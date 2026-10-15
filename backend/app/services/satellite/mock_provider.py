from datetime import datetime, timedelta, timezone

from app.db.seed import LOC_KUTTANAD, LOC_GUWAHATI, LOC_PURI
from app.services.satellite.models import SatelliteScene

NOW = datetime(2026, 7, 14, 6, 0, tzinfo=timezone.utc)

SAT_NORMAL = "sat-normal-001"
SAT_FLOOD_BEFORE = "sat-flood-before-001"
SAT_FLOOD_AFTER = "sat-flood-after-001"
SAT_BURN = "sat-burn-001"
SAT_URBAN = "sat-urban-001"
SAT_VEG = "sat-veg-001"
SAT_SLIDE = "sat-slide-001"


def _box(lon: float, lat: float, d: float = 0.035) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [[
            [lon - d, lat - d],
            [lon + d, lat - d],
            [lon + d, lat + d],
            [lon - d, lat + d],
            [lon - d, lat - d],
        ]],
    }


class MockSatelliteProvider:
    name = "mock-sentinel2"
    live = False

    def __init__(self) -> None:
        self._scenes = [
            SatelliteScene(
                id=SAT_NORMAL,
                title="Kuttanad baseline (demo)",
                source="mock-sentinel2",
                acquisition_time=NOW - timedelta(days=18),
                latitude=9.517,
                longitude=76.522,
                bounding_box=_box(76.522, 9.517),
                cloud_cover=6.2,
                image_url=f"/api/v1/satellite/images/{SAT_NORMAL}/preview",
                thumbnail_url=f"/api/v1/satellite/images/{SAT_NORMAL}/preview",
                location_id=LOC_KUTTANAD,
                scene_kind="normal",
                metadata={"note": "Synthetic raster. Not Copernicus imagery."},
            ),
            SatelliteScene(
                id=SAT_FLOOD_BEFORE,
                title="Kuttanad pre-event (demo)",
                source="mock-landsat",
                acquisition_time=NOW - timedelta(days=10),
                latitude=9.517,
                longitude=76.522,
                bounding_box=_box(76.522, 9.517),
                cloud_cover=11.0,
                image_url=f"/api/v1/satellite/images/{SAT_FLOOD_BEFORE}/preview",
                thumbnail_url=f"/api/v1/satellite/images/{SAT_FLOOD_BEFORE}/preview",
                location_id=LOC_KUTTANAD,
                scene_kind="flood_before",
                metadata={"pair": SAT_FLOOD_AFTER},
            ),
            SatelliteScene(
                id=SAT_FLOOD_AFTER,
                title="Kuttanad flood event (demo)",
                source="mock-sentinel2",
                acquisition_time=NOW - timedelta(hours=6),
                latitude=9.517,
                longitude=76.522,
                bounding_box=_box(76.522, 9.517),
                cloud_cover=9.4,
                image_url=f"/api/v1/satellite/images/{SAT_FLOOD_AFTER}/preview",
                thumbnail_url=f"/api/v1/satellite/images/{SAT_FLOOD_AFTER}/preview",
                location_id=LOC_KUTTANAD,
                scene_kind="flood",
                metadata={"pair": SAT_FLOOD_BEFORE},
            ),
            SatelliteScene(
                id=SAT_BURN,
                title="Burn scar demo (Western Ghats)",
                source="mock-sentinel2",
                acquisition_time=NOW - timedelta(days=4),
                latitude=9.58,
                longitude=76.90,
                bounding_box=_box(76.90, 9.58),
                cloud_cover=4.1,
                image_url=f"/api/v1/satellite/images/{SAT_BURN}/preview",
                thumbnail_url=f"/api/v1/satellite/images/{SAT_BURN}/preview",
                location_id=LOC_KUTTANAD,
                scene_kind="burn",
            ),
            SatelliteScene(
                id=SAT_URBAN,
                title="Urban fabric demo (Alappuzha)",
                source="mock-landsat",
                acquisition_time=NOW - timedelta(days=2),
                latitude=9.498,
                longitude=76.338,
                bounding_box=_box(76.338, 9.498, 0.02),
                cloud_cover=14.0,
                image_url=f"/api/v1/satellite/images/{SAT_URBAN}/preview",
                thumbnail_url=f"/api/v1/satellite/images/{SAT_URBAN}/preview",
                location_id=LOC_KUTTANAD,
                scene_kind="urban",
            ),
            SatelliteScene(
                id=SAT_VEG,
                title="Vegetation canopy demo",
                source="mock-sentinel2",
                acquisition_time=NOW - timedelta(days=7),
                latitude=9.62,
                longitude=76.55,
                bounding_box=_box(76.55, 9.62),
                cloud_cover=3.3,
                image_url=f"/api/v1/satellite/images/{SAT_VEG}/preview",
                thumbnail_url=f"/api/v1/satellite/images/{SAT_VEG}/preview",
                location_id=LOC_KUTTANAD,
                scene_kind="vegetation",
            ),
            SatelliteScene(
                id=SAT_SLIDE,
                title="Hillslope scar demo (Guwahati)",
                source="mock-sentinel2",
                acquisition_time=NOW - timedelta(days=1),
                latitude=26.185,
                longitude=91.752,
                bounding_box=_box(91.752, 26.185),
                cloud_cover=18.5,
                image_url=f"/api/v1/satellite/images/{SAT_SLIDE}/preview",
                thumbnail_url=f"/api/v1/satellite/images/{SAT_SLIDE}/preview",
                location_id=LOC_GUWAHATI,
                scene_kind="landslide",
                metadata={"puri_ref": LOC_PURI},
            ),
        ]

    def list_scenes(self, start=None, end=None, max_cloud=None) -> list[SatelliteScene]:
        scenes = list(self._scenes)
        if start is not None:
            scenes = [s for s in scenes if s.acquisition_time.date() >= start]
        if end is not None:
            scenes = [s for s in scenes if s.acquisition_time.date() <= end]
        if max_cloud is not None:
            scenes = [s for s in scenes if s.cloud_cover <= float(max_cloud)]
        return scenes

    def get_scene(self, scene_id: str) -> SatelliteScene | None:
        return next((s for s in self._scenes if s.id == scene_id), None)

    def scene_kind(self, scene_id: str) -> str:
        scene = self.get_scene(scene_id)
        return scene.scene_kind if scene else "normal"


class SentinelLandsatProvider:
    """Optional live adapter. Without GEE/Sentinel credentials this delegates to mock."""

    name = "sentinel-landsat"
    live = False

    def __init__(self, credentials_configured: bool = False):
        self._mock = MockSatelliteProvider()
        self.live = credentials_configured

    def list_scenes(self, start=None, end=None, max_cloud=None):
        return self._mock.list_scenes(start=start, end=end, max_cloud=max_cloud)

    def get_scene(self, scene_id: str):
        return self._mock.get_scene(scene_id)

    def scene_kind(self, scene_id: str) -> str:
        return self._mock.scene_kind(scene_id)


def get_satellite_provider():
    from app.core.config import settings

    if settings.use_mock_providers:
        return MockSatelliteProvider()
    from app.services.satellite.copernicus_provider import CopernicusStacProvider

    return CopernicusStacProvider()
