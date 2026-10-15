from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.providers import ProviderUnavailableError
from app.db.session import new_uuid
from app.models import ImageAnalysisResult, SatelliteImage
from app.services.satellite.copernicus_provider import resolve_search_window
from app.services.satellite.mock_provider import get_satellite_provider
from app.services.satellite.processing import (
    compare_scenes,
    detect_burned,
    detect_urban,
    detect_vegetation,
    detect_water,
    detect_water_sentinel_rgb,
    encode_png,
    flooded_metrics,
    generate_demo_raster,
    mask_to_geojson,
)

DETECTORS = {
    "flood": detect_water,
    "water": detect_water,
    "vegetation": detect_vegetation,
    "burn": detect_burned,
    "urban": detect_urban,
    "landslide": detect_urban,
}


def _decode_image_bytes(data: bytes):
    import numpy as np

    try:
        import cv2
    except ImportError as exc:  # pragma: no cover
        raise ProviderUnavailableError("opencv", "OpenCV not available to decode imagery.") from exc
    arr = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ProviderUnavailableError("satellite", "Could not decode thumbnail image bytes.")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def _query_window(start: date | None, end: date | None) -> tuple[date, date]:
    try:
        return resolve_search_window(start, end)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _aoi_snapshot() -> dict:
    from app.services.geo.aoi import get_aoi

    return get_aoi()


def sync_catalog(
    db: Session,
    *,
    start: date | None = None,
    end: date | None = None,
    max_cloud: float | None = None,
) -> None:
    provider = get_satellite_provider()
    start_d, end_d = _query_window(start, end)
    try:
        scenes = provider.list_scenes(start=start_d, end=end_d, max_cloud=max_cloud)
    except ProviderUnavailableError:
        raise
    except TypeError:
        scenes = provider.list_scenes()
    if not settings.use_mock_providers:
        for row in db.query(SatelliteImage).all():
            meta = row.extra_metadata or {}
            source = str(row.source or row.provider or "")
            if not meta.get("stac_id") and ("mock" in source or source in {"demo", "mock-sentinel2", "mock-landsat"}):
                db.delete(row)
        db.commit()
    for scene in scenes:
        row = db.query(SatelliteImage).filter(SatelliteImage.id == scene.id).first()
        thumb = (scene.metadata or {}).get("thumbnail_href") or ""
        payload = dict(
            location_id=scene.location_id or "",
            captured_at=scene.acquisition_time.replace(tzinfo=None),
            provider=scene.source,
            source=scene.source,
            storage_path=thumb if thumb else (f"memory://{scene.scene_kind}" if settings.use_mock_providers else ""),
            bbox_geojson=scene.bounding_box,
            latitude=scene.latitude,
            longitude=scene.longitude,
            resolution=scene.resolution,
            cloud_cover=scene.cloud_cover,
            image_url=scene.image_url,
            thumbnail_url=scene.thumbnail_url,
            status=scene.status,
            extra_metadata={**scene.metadata, "title": scene.title, "scene_kind": scene.scene_kind},
        )
        if row:
            for key, value in payload.items():
                setattr(row, key, value)
        else:
            db.add(SatelliteImage(id=scene.id, **payload))
    db.commit()


class SatelliteService:
    def __init__(self, db: Session):
        self.db = db
        self.provider = get_satellite_provider()
        if settings.use_mock_providers:
            sync_catalog(db)

    def list_catalog(
        self,
        start: date | None = None,
        end: date | None = None,
        max_cloud: float | None = None,
    ) -> tuple[list[SatelliteImage], dict]:
        start_d, end_d = _query_window(start, end)
        aoi = _aoi_snapshot()
        sync_catalog(self.db, start=start_d, end=end_d, max_cloud=max_cloud)
        rows = self.db.query(SatelliteImage).order_by(SatelliteImage.captured_at.desc()).all()
        filtered: list[SatelliteImage] = []
        for row in rows:
            captured = row.captured_at.date() if row.captured_at else None
            if captured and (captured < start_d or captured > end_d):
                continue
            if max_cloud is not None and float(row.cloud_cover or 0) > float(max_cloud):
                continue
            if not settings.use_mock_providers:
                meta = row.extra_metadata or {}
                if not meta.get("stac_id"):
                    continue
                from app.services.satellite.copernicus_provider import (
                    bboxes_intersect,
                    geometry_bbox,
                    stac_scene_bbox,
                )

                aoi_bbox = aoi.get("bbox")
                scene_bb = meta.get("scene_bbox")
                if not scene_bb:
                    scene_bb = geometry_bbox(row.bbox_geojson) if isinstance(row.bbox_geojson, dict) else None
                if not scene_bb:
                    scene_bb = stac_scene_bbox({"bbox": None, "geometry": row.bbox_geojson})
                if not aoi_bbox or not scene_bb or not bboxes_intersect(list(scene_bb), list(aoi_bbox)):
                    continue
            filtered.append(row)
        query = {
            "start": start_d.isoformat(),
            "end": end_d.isoformat(),
            "max_cloud": max_cloud if max_cloud is not None else settings.copernicus_max_cloud,
            "aoi_name": aoi.get("aoi_name"),
            "bbox": aoi.get("bbox"),
            "live_stream": False,
            "imagery_layers": ["catalogue", "preview", "downloadable_raster", "processed_analysis"],
            "note": "Acquisition dates are scene timestamps from Copernicus STAC, not a real-time feed.",
        }
        return filtered, query

    def list_images(self) -> list[SatelliteImage]:
        items, _ = self.list_catalog()
        return items

    def get_image(self, image_id: str) -> SatelliteImage:
        row = self.db.query(SatelliteImage).filter(SatelliteImage.id == image_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Satellite image not found")
        return row

    def _live_rgb(self, image_id: str):
        if settings.use_mock_providers:
            return None
        fetch = getattr(self.provider, "fetch_thumbnail_bytes", None)
        if not callable(fetch):
            raise ProviderUnavailableError(
                "satellite",
                "Live satellite provider cannot fetch imagery bytes.",
            )
        return _decode_image_bytes(fetch(image_id))

    def raster_for(self, image_id: str):
        if not settings.use_mock_providers:
            return self._live_rgb(image_id)
        kind = self.provider.scene_kind(image_id)
        return generate_demo_raster(kind)

    def preview_png(self, image_id: str) -> bytes:
        self.get_image(image_id)
        if not settings.use_mock_providers:
            fetch = getattr(self.provider, "fetch_thumbnail_bytes", None)
            if not callable(fetch):
                raise ProviderUnavailableError("satellite", "Live preview unavailable.")
            data = fetch(image_id)
            # Thumbnails are often JPEG; return as-is when already encoded.
            if data[:3] == b"\xff\xd8\xff":
                return data
            rgb = _decode_image_bytes(data)
            return encode_png(rgb)
        return encode_png(self.raster_for(image_id))

    def analyze(self, image_id: str, analysis_type: str = "flood") -> ImageAnalysisResult:
        image = self.get_image(image_id)
        rgb = self.raster_for(image_id)
        live = not settings.use_mock_providers and bool((image.extra_metadata or {}).get("stac_id"))
        if not settings.use_mock_providers and not live:
            raise ProviderUnavailableError(
                "satellite",
                "Live analysis requires a genuine STAC scene. Demo rasters are not substituted.",
            )
        if live and analysis_type in {"flood", "water"}:
            detector = detect_water_sentinel_rgb
            model_name = "sentinel-rgb-water-heuristic-v1"
            summary = (
                "Satellite-derived water indication on a Sentinel-2 preview "
                f"({analysis_type}). OpenCV/NumPy heuristic — not a trained flood model; requires validation."
            )
        else:
            detector = DETECTORS.get(analysis_type, detect_water)
            model_name = "opencv-heuristic-on-preview" if live else "baseline-demo-cv-v0"
            summary = (
                f"{'OpenCV feature heuristic on latest-available Sentinel preview' if live else 'Prototype segmentation on synthetic raster'}"
                f" ({analysis_type}). Not a trained Sentinel segmentation model."
            )
        mask = detector(rgb)
        geojson = mask_to_geojson(mask, image.bbox_geojson, analysis_type)
        if analysis_type in {"flood", "water"}:
            metrics = flooded_metrics(mask, image.bbox_geojson, population=None if live else 42000)
        else:
            metrics = {"percent_affected": round(float(mask.mean()) * 100, 1)}
        meta = image.extra_metadata or {}
        row = ImageAnalysisResult(
            id=new_uuid(),
            satellite_image_id=image_id,
            model_name=model_name,
            analysis_type=analysis_type,
            summary=summary,
            confidence=0.55 if live else 0.62,
            result_geojson=geojson,
            metrics={
                **metrics,
                "data_label": "Processed analysis on STAC preview" if live else "DEMO synthetic raster",
                "layer": "processed_analysis",
                "full_raster_downloaded": False,
                "scene_provenance": {
                    "stac_id": meta.get("stac_id"),
                    "acquisition_time": image.captured_at.isoformat() if image.captured_at else None,
                    "cloud_cover": image.cloud_cover,
                    "aoi_name": meta.get("aoi_name"),
                    "aoi_bbox": meta.get("aoi_bbox"),
                    "preview_used": True,
                    "live_stream": False,
                },
            },
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_analysis(self, analysis_id: str) -> ImageAnalysisResult:
        row = self.db.query(ImageAnalysisResult).filter(ImageAnalysisResult.id == analysis_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Analysis not found")
        return row

    def compare(self, before_id: str, after_id: str) -> ImageAnalysisResult:
        before = self.get_image(before_id)
        after = self.get_image(after_id)
        live = not settings.use_mock_providers
        before_meta = before.extra_metadata or {}
        after_meta = after.extra_metadata or {}
        if live and (not before_meta.get("stac_id") or not after_meta.get("stac_id")):
            raise ProviderUnavailableError(
                "satellite",
                "Live comparison requires two genuine STAC scenes. Demo rasters are not substituted.",
            )
        bbox = after.bbox_geojson
        if live:
            from app.services.satellite.copernicus_provider import CopernicusStacProvider, _bbox_polygon

            bbox = _bbox_polygon(CopernicusStacProvider()._aoi_bbox())
        result = compare_scenes(
            self.raster_for(before_id),
            self.raster_for(after_id),
            bbox,
            use_sentinel_heuristic=live,
        )
        m = result["metrics"]
        row = ImageAnalysisResult(
            id=new_uuid(),
            satellite_image_id=after_id,
            model_name="sentinel-rgb-water-change-v1" if live else "baseline-change-v0",
            analysis_type="comparison",
            summary=(
                (
                    "Satellite-derived water-change indication — requires validation. "
                    f"Sentinel-2 previews before→after. Newly water-covered {m.get('newly_flooded_area_km2')} km² "
                    f"({m.get('newly_flooded_percentage')}% AOI). RGB heuristic — not a trained flood model."
                )
                if live
                else (
                    f"Prototype change detection {before_id} → {after_id}. "
                    f"Flood expansion {m.get('flood_expansion_fraction')}."
                )
            ),
            confidence=0.48 if live else 0.58,
            result_geojson=result["geojson"],
            metrics={
                **m,
                "before_image": before_id,
                "after_image": after_id,
                "before_title": (before.extra_metadata or {}).get("title") or before.title,
                "after_title": (after.extra_metadata or {}).get("title") or after.title,
                "before_water_geojson": result.get("before_water_geojson"),
                "after_water_geojson": result.get("after_water_geojson"),
                "newly_flooded_geojson": result.get("newly_flooded_geojson"),
                "estimate_label": (
                    "Satellite-derived water-change indication — requires validation"
                    if live
                    else "Prototype change detection"
                ),
                "data_label": "Processed analysis on STAC previews" if live else "DEMO synthetic raster",
                "layer": "processed_analysis",
                "full_raster_downloaded": False,
                "scene_provenance": {
                    "before_stac_id": (before.extra_metadata or {}).get("stac_id"),
                    "after_stac_id": (after.extra_metadata or {}).get("stac_id"),
                    "before_acquisition_time": before.captured_at.isoformat() if before.captured_at else None,
                    "after_acquisition_time": after.captured_at.isoformat() if after.captured_at else None,
                    "before_cloud_cover": before.cloud_cover,
                    "after_cloud_cover": after.cloud_cover,
                    "live_stream": False,
                },
            },
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row
