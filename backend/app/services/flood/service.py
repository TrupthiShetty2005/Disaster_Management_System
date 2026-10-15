from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.demo import DEMO_AFFECTED_POPULATION, DEMO_FLOODED_KM2
from app.core.providers import ProviderUnavailableError
from app.models import FloodAnalysis
from app.services.flood.geo import (
    affected_assets,
    classify_flood_risk,
    extract_polygons,
    flooded_area_km2,
    heatmap_geojson,
)
from app.services.flood.models import get_flood_model
from app.services.satellite.copernicus_provider import resolve_search_window
from app.services.satellite.processing import (
    WATER_CHANGE_LABEL,
    compare_water_change,
    generate_demo_raster,
    mask_ratio,
)

# Reject optical scenes above this cloud cover for flood indication.
MAX_CLOUD_FOR_FLOOD = 55.0
CHANGE_KEY = "visionguard_change"


def _poly_extent(geom: dict | None) -> tuple[float, float, float, float] | None:
    if not geom:
        return None
    if geom.get("type") == "Polygon":
        ring = geom["coordinates"][0]
        return (
            min(p[0] for p in ring),
            min(p[1] for p in ring),
            max(p[0] for p in ring),
            max(p[1] for p in ring),
        )
    return None


def _overlap_ratio(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = max((a[2] - a[0]) * (a[3] - a[1]), 1e-12)
    area_b = max((b[2] - b[0]) * (b[3] - b[1]), 1e-12)
    return inter / min(area_a, area_b)


def _scenes_compatible(before, after) -> bool:
    if after.acquisition_time <= before.acquisition_time:
        return False
    if (after.source or "") != (before.source or ""):
        return False
    ba = _poly_extent(before.bounding_box)
    aa = _poly_extent(after.bounding_box)
    if ba and aa and _overlap_ratio(ba, aa) < 0.2:
        return False
    return True


def _is_live_water_change_row(row) -> bool:
    notes = (row.notes or "").lower()
    if "synthetic" in notes or "demo mode" in notes:
        return False
    if (row.model_name or "").startswith("demo") or row.model_name == "stub-flood-seg-v0":
        return False
    if (
        abs(float(row.flooded_area or 0) - DEMO_FLOODED_KM2) < 0.05
        and int(row.affected_population or 0) == DEMO_AFFECTED_POPULATION
    ):
        return False
    boundary = row.boundary_geojson if isinstance(row.boundary_geojson, dict) else {}
    change = boundary.get(CHANGE_KEY) if isinstance(boundary, dict) else None
    if isinstance(change, dict) and change.get("before_stac_id") and change.get("after_stac_id"):
        return True
    return (row.scene_kind or "") == "sentinel2-change" or "requires validation" in notes


class FloodDetectionService:
    """Real Mode: before/after Sentinel water change. Demo Mode: synthetic single-scene fallback."""

    def __init__(self, db: Session, model=None):
        self.db = db
        self.model = model

    def _aoi_bbox(self) -> dict:
        from app.services.satellite.copernicus_provider import CopernicusStacProvider, _bbox_polygon

        return _bbox_polygon(CopernicusStacProvider()._aoi_bbox())

    def _suitable_sentinel2(self):
        from app.services.satellite.copernicus_provider import CopernicusStacProvider

        provider = CopernicusStacProvider()
        start, end = resolve_search_window(None, None)
        try:
            scenes = [
                s
                for s in provider.list_scenes(start=start, end=end)
                if s.source == "sentinel-2"
            ]
        except ProviderUnavailableError:
            raise
        if not scenes:
            raise ProviderUnavailableError(
                "flood",
                "No Sentinel-2 scenes available for the Karnataka AOI. Flood analysis will not invent synthetic imagery.",
            )
        suitable = [s for s in scenes if s.cloud_cover <= MAX_CLOUD_FOR_FLOOD]
        if len(suitable) < 2:
            detail = ", ".join(
                f"{(s.metadata or {}).get('stac_id', s.id)} cloud={s.cloud_cover:.1f}%"
                for s in sorted(scenes, key=lambda x: x.cloud_cover)[:3]
            )
            raise ProviderUnavailableError(
                "flood",
                (
                    f"Need at least two low-cloud Sentinel-2 scenes (cloud ≤ {MAX_CLOUD_FOR_FLOOD}%) "
                    f"for before/after change detection. Available: {detail or 'none'}."
                ),
            )
        suitable = sorted(suitable, key=lambda s: (-s.acquisition_time.timestamp(), s.cloud_cover))
        return provider, suitable

    def _decode_scene(self, provider, scene):
        from app.services.satellite.service import _decode_image_bytes

        stac_id = (scene.metadata or {}).get("stac_id", scene.id)
        try:
            raw = provider.fetch_thumbnail_bytes(scene.id)
        except ProviderUnavailableError as exc:
            raise ProviderUnavailableError(
                "flood",
                f"Sentinel-2 image download failed for {stac_id}: {exc.message}",
            ) from exc
        try:
            rgb = _decode_image_bytes(raw)
        except ProviderUnavailableError as exc:
            raise ProviderUnavailableError("flood", f"Could not decode Sentinel preview {stac_id}: {exc.message}") from exc
        if rgb is None or getattr(rgb, "size", 0) == 0:
            raise ProviderUnavailableError("flood", f"Decoded Sentinel image was empty ({stac_id}).")
        return rgb

    def _load_pair(self, provider, suitable):
        """Newest suitable = after; try older candidates until a before image downloads."""
        errors: list[str] = []
        after_scene = suitable[0]
        try:
            after_rgb = self._decode_scene(provider, after_scene)
        except ProviderUnavailableError as exc:
            raise ProviderUnavailableError("flood", f"AFTER scene download failed: {exc.message}") from exc
        for before_scene in suitable[1:]:
            try:
                before_rgb = self._decode_scene(provider, before_scene)
                if not _scenes_compatible(before_scene, after_scene):
                    continue
                if before_rgb.shape[0] < 8 or after_rgb.shape[0] < 8:
                    continue
                return before_scene, before_rgb, after_scene, after_rgb
            except ProviderUnavailableError as exc:
                errors.append(f"{(before_scene.metadata or {}).get('stac_id', before_scene.id)}: {exc.message}")
                continue
        extra = "; ".join(errors[:3]) or "No overlapping low-cloud pair."
        raise ProviderUnavailableError(
            "flood",
            "Could not download a compatible BEFORE Sentinel-2 preview for change detection. " + extra,
        )

    def _analyze_real_change(self, bbox: dict | None) -> FloodAnalysis:
        from app.services.satellite.service import sync_catalog

        provider, suitable = self._suitable_sentinel2()
        before_scene, before_rgb, after_scene, after_rgb = self._load_pair(provider, suitable)
        scene_bbox = bbox or self._aoi_bbox()
        try:
            change = compare_water_change(
                before_rgb,
                after_rgb,
                scene_bbox,
                use_sentinel_heuristic=True,
            )
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailableError("flood", f"Flood change processing failed: {exc}") from exc

        # Ensure preview URLs resolve via satellite catalog.
        try:
            sync_catalog(self.db)
        except Exception:  # noqa: BLE001
            pass

        m = change["metrics"]
        newly_area = float(m["newly_flooded_area_km2"])
        newly_pct = float(m["newly_flooded_percentage"])
        before_id = (before_scene.metadata or {}).get("stac_id", before_scene.id)
        after_id = (after_scene.metadata or {}).get("stac_id", after_scene.id)
        gap_days = abs((after_scene.acquisition_time.date() - before_scene.acquisition_time.date()).days)
        notes = " | ".join(
            [
                f"Label: {WATER_CHANGE_LABEL}",
                "Method: OpenCV/NumPy RGB heuristic on genuine Sentinel-2 STAC previews — not a trained flood-segmentation model",
                f"BEFORE STAC: {before_id} date={before_scene.acquisition_time.date().isoformat()} cloud={before_scene.cloud_cover:.1f}% res={before_scene.resolution}",
                f"AFTER STAC: {after_id} date={after_scene.acquisition_time.date().isoformat()} cloud={after_scene.cloud_cover:.1f}% res={after_scene.resolution}",
                f"Acquisition gap: {gap_days} day(s) (seasonal/permanent water can dominate change)",
                f"Before water: {m['before_water_area_km2']} km² ({m['before_water_fraction'] * 100:.1f}% AOI)",
                f"After water: {m['after_water_area_km2']} km² ({m['after_water_fraction'] * 100:.1f}% AOI)",
                f"Newly water-covered vs before mask: {newly_area} km² ({newly_pct}% AOI); relative water change {m['percentage_change']}%",
                "Not every water pixel is floodwater. Permanent water, wetlands, clouds, and date gaps are not field-validated.",
                "Impact stats (population, buildings, roads, economic loss) are UNAVAILABLE — no census/asset overlay wired.",
                "Analysis status: heuristic_preview — not a validated flood boundary.",
            ]
        )
        newly_mask = change["expansion_mask"]
        boundary = extract_polygons(newly_mask, scene_bbox)
        # Attach structured change payload for API/UI (extra key; FeatureCollection features remain valid).
        boundary = {
            **boundary,
            CHANGE_KEY: {
                "metrics": m,
                "before_image_id": before_scene.id,
                "after_image_id": after_scene.id,
                "before_stac_id": before_id,
                "after_stac_id": after_id,
                "before_date": before_scene.acquisition_time.date().isoformat(),
                "after_date": after_scene.acquisition_time.date().isoformat(),
                "before_cloud": before_scene.cloud_cover,
                "after_cloud": after_scene.cloud_cover,
                "spatial_resolution": after_scene.resolution,
                "processing_method": m.get("method"),
                "analysis_status": "heuristic_preview_unvalidated",
                "validated_flood_boundary": False,
                "before_preview_url": f"/api/v1/satellite/images/{before_scene.id}/preview",
                "after_preview_url": f"/api/v1/satellite/images/{after_scene.id}/preview",
                "before_water_geojson": change["before_water_geojson"],
                "after_water_geojson": change["after_water_geojson"],
                "newly_flooded_geojson": change["newly_flooded_geojson"],
            },
        }
        row = FloodAnalysis(
            model_name="sentinel-rgb-water-change-v1",
            scene_kind="sentinel2-change",
            flooded_area=newly_area,
            flood_percentage=newly_pct,
            severity=classify_flood_risk(newly_pct),
            confidence=0.48,
            affected_population=0,
            affected_roads=0,
            affected_buildings=0,
            boundary_geojson=boundary,
            heatmap_geojson=heatmap_geojson(newly_mask, scene_bbox),
            notes=notes,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def _analyze_demo(self, scene_kind: str, population: int, bbox: dict | None) -> FloodAnalysis:
        before = generate_demo_raster("flood_before", size=64)
        after = generate_demo_raster("flood" if scene_kind == "flood" else scene_kind, size=64)
        model = self.model or get_flood_model("demo")
        change = compare_water_change(before, after, bbox, use_sentinel_heuristic=False)
        m = change["metrics"]
        newly_area = float(m["newly_flooded_area_km2"])
        newly_pct = float(m["newly_flooded_percentage"])
        # Demo Mode also exposes single-scene absolute water for storytelling KPIs path.
        after_mask, method_note = model.segment(after)
        # Prefer change metrics as primary flooded_area so UI teaches change concept consistently.
        pop, roads, buildings = affected_assets(newly_pct, population)
        notes = (
            f"Demo Mode synthetic before/after change. Newly water-covered {newly_area} km² ({newly_pct}%). "
            f"{method_note} Absolute after-water {mask_ratio(after_mask) * 100:.1f}% of synthetic raster."
        )
        boundary = extract_polygons(change["expansion_mask"], bbox)
        boundary = {
            **boundary,
            CHANGE_KEY: {
                "metrics": m,
                "before_image_id": None,
                "after_image_id": None,
                "before_water_geojson": change["before_water_geojson"],
                "after_water_geojson": change["after_water_geojson"],
                "newly_flooded_geojson": change["newly_flooded_geojson"],
            },
        }
        row = FloodAnalysis(
            model_name=model.name,
            scene_kind=scene_kind,
            flooded_area=newly_area if newly_area > 0 else flooded_area_km2(after_mask, bbox),
            flood_percentage=newly_pct if newly_pct > 0 else round(mask_ratio(after_mask) * 100, 1),
            severity=classify_flood_risk(newly_pct if newly_pct > 0 else mask_ratio(after_mask) * 100),
            confidence=0.58,
            affected_population=pop,
            affected_roads=roads,
            affected_buildings=buildings,
            boundary_geojson=boundary,
            heatmap_geojson=heatmap_geojson(change["expansion_mask"], bbox),
            notes=notes,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def analyze(self, scene_kind: str = "flood", population: int = 42000, bbox: dict | None = None) -> FloodAnalysis:
        if settings.use_mock_providers:
            return self._analyze_demo(scene_kind, population, bbox)
        return self._analyze_real_change(bbox)

    def list_events(self) -> list[FloodAnalysis]:
        rows = self.db.query(FloodAnalysis).order_by(FloodAnalysis.created_at.desc()).all()
        if settings.use_mock_providers:
            if rows:
                return rows
            return [self.analyze("flood")]
        return [r for r in rows if _is_live_water_change_row(r)]

    def get(self, event_id: str) -> FloodAnalysis | None:
        row = self.db.query(FloodAnalysis).filter(FloodAnalysis.id == event_id).first()
        if row is None:
            return None
        if not settings.use_mock_providers and not _is_live_water_change_row(row):
            return None
        return row
