from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.providers import ProviderUnavailableError
from app.models import DamageReport
from app.services.damage.classify import building_statistics, road_statistics
from app.services.damage.report import ReportRenderer, build_report
from app.services.satellite.processing import compare_scenes, generate_demo_raster


class DamageAssessmentService:
    """Before + after images → structural / road / building / vegetation / water change."""

    def __init__(self, db: Session):
        self.db = db
        self.renderer = ReportRenderer()

    def _load_pair(self, before_kind: str, after_kind: str):
        if settings.use_mock_providers:
            return generate_demo_raster(before_kind, 64), generate_demo_raster(after_kind, 64), None, None
        from app.services.satellite.copernicus_provider import CopernicusStacProvider
        from app.services.satellite.service import _decode_image_bytes

        provider = CopernicusStacProvider()
        try:
            scenes = [s for s in provider.list_scenes() if s.source == "sentinel-2"]
        except ProviderUnavailableError:
            raise
        if len(scenes) < 2:
            raise ProviderUnavailableError(
                "damage",
                "Need at least two Sentinel-2 scenes for before/after damage comparison. Demo synthetic pair is not used in Real Data Mode.",
            )
        # Newest = after, next = before (Latest Available catalogue order).
        ordered = sorted(scenes, key=lambda s: s.acquisition_time.timestamp(), reverse=True)
        after_scene, before_scene = ordered[0], ordered[1]
        try:
            after_rgb = _decode_image_bytes(provider.fetch_thumbnail_bytes(after_scene.id))
            before_rgb = _decode_image_bytes(provider.fetch_thumbnail_bytes(before_scene.id))
        except ProviderUnavailableError as exc:
            raise ProviderUnavailableError(
                "damage",
                f"Sentinel before/after download failed: {exc.message}",
            ) from exc
        return before_rgb, after_rgb, before_scene, after_scene

    def analyze(
        self,
        before_kind: str = "flood_before",
        after_kind: str = "flood",
        bbox: dict | None = None,
        population: int = 42000,
    ) -> DamageReport:
        before, after, before_scene, after_scene = self._load_pair(before_kind, after_kind)
        if before_scene is not None:
            from app.services.satellite.copernicus_provider import CopernicusStacProvider, _bbox_polygon

            bbox = bbox or _bbox_polygon(CopernicusStacProvider()._aoi_bbox())
        compared = compare_scenes(before, after, bbox)
        m = compared["metrics"]
        flood_exp = float(m["flood_expansion_fraction"])
        veg = float(m["vegetation_loss_fraction"])
        urban = float(m["urban_change_fraction"])
        if settings.use_mock_providers:
            buildings = building_statistics(flood_exp, urban, veg)
            roads = road_statistics(flood_exp, urban)
            pop = population
        else:
            from app.services.damage.classify import BUILDING_CLASSES, ROAD_CLASSES

            buildings = {
                "counts": {c: 0 for c in BUILDING_CLASSES},
                "damaged_percentage": 0,
                "primary": "UNAVAILABLE",
                "available": False,
            }
            roads = {
                "counts": {c: 0 for c in ROAD_CLASSES},
                "destroyed_roads": 0,
                "blocked_or_destroyed": 0,
                "primary": "UNAVAILABLE",
                "available": False,
            }
            pop = 0
        report = build_report(
            flooded_area_km2=float(m["flooded_area_km2"]),
            flood_expansion=flood_exp,
            veg_loss=veg,
            urban_change=urban,
            buildings=buildings,
            roads=roads,
            population=pop,
        )
        if before_scene is not None and after_scene is not None:
            b_id = (before_scene.metadata or {}).get("stac_id", before_scene.id)
            a_id = (after_scene.metadata or {}).get("stac_id", after_scene.id)
            report["executive_summary"] = (
                f"Satellite-derived change indication on Copernicus Sentinel-2 previews "
                f"({b_id} → {a_id}). Heuristic change detection — not a trained damage model."
            )
            model_name = "sentinel-change-heuristic-v1"
            before_kind = "sentinel2-before"
            after_kind = "sentinel2-after"
        else:
            model_name = "demo-change-v0"
        row = DamageReport(
            model_name=model_name,
            before_kind=before_kind,
            after_kind=after_kind,
            report=self.renderer.to_json(report),
            overlay_geojson=compared["geojson"],
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_assessments(self) -> list[DamageReport]:
        rows = self.db.query(DamageReport).order_by(DamageReport.created_at.desc()).all()
        if settings.use_mock_providers:
            if rows:
                return rows
            return [self.analyze()]
        live_rows = [r for r in rows if (r.model_name or "").startswith("sentinel")]
        return live_rows

    def get(self, assessment_id: str) -> DamageReport | None:
        row = self.db.query(DamageReport).filter(DamageReport.id == assessment_id).first()
        if row is None:
            return None
        if not settings.use_mock_providers and not (row.model_name or "").startswith("sentinel"):
            return None
        return row
