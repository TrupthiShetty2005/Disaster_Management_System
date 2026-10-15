from datetime import datetime, timezone
from types import SimpleNamespace

from app.core.config import settings
from app.core.demo import DEMO_AFFECTED_POPULATION, DEMO_FLOODED_KM2
from app.core.providers import ProviderUnavailableError
from app.services.flood.service import _is_live_water_change_row, _scenes_compatible
from app.services.satellite.processing import generate_demo_raster


def test_seeded_demo_flood_stats_are_not_live_rows():
    seeded = SimpleNamespace(
        notes="Demo Mode synthetic before/after change.",
        model_name="demo-flood-seg-v0",
        flooded_area=DEMO_FLOODED_KM2,
        affected_population=DEMO_AFFECTED_POPULATION,
        scene_kind="flood",
        boundary_geojson={},
    )
    assert _is_live_water_change_row(seeded) is False


def test_live_change_row_requires_stac_pair():
    live = SimpleNamespace(
        notes="Satellite-derived water-change indication — requires validation",
        model_name="sentinel-rgb-water-change-v1",
        flooded_area=1.2,
        affected_population=0,
        scene_kind="sentinel2-change",
        boundary_geojson={
            "visionguard_change": {"before_stac_id": "S2_BEFORE", "after_stac_id": "S2_AFTER"}
        },
    )
    assert _is_live_water_change_row(live) is True


def test_scene_pair_rejects_inverted_dates_and_disjoint_footprints():
    before = SimpleNamespace(
        acquisition_time=datetime(2026, 6, 10, tzinfo=timezone.utc),
        source="sentinel-2",
        bounding_box={
            "type": "Polygon",
            "coordinates": [[[77.5, 12.9], [77.6, 12.9], [77.6, 13.0], [77.5, 13.0], [77.5, 12.9]]],
        },
    )
    after_earlier = SimpleNamespace(
        acquisition_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        source="sentinel-2",
        bounding_box=before.bounding_box,
    )
    assert _scenes_compatible(before, after_earlier) is False
    distant = SimpleNamespace(
        acquisition_time=datetime(2026, 6, 20, tzinfo=timezone.utc),
        source="sentinel-2",
        bounding_box={
            "type": "Polygon",
            "coordinates": [[[74.0, 15.0], [74.1, 15.0], [74.1, 15.1], [74.0, 15.1], [74.0, 15.0]]],
        },
    )
    assert _scenes_compatible(before, distant) is False
    after_ok = SimpleNamespace(
        acquisition_time=datetime(2026, 6, 20, tzinfo=timezone.utc),
        source="sentinel-2",
        bounding_box=before.bounding_box,
    )
    assert _scenes_compatible(before, after_ok) is True


def test_live_flood_analyze_does_not_fall_back_to_demo_raster(client, monkeypatch):
    monkeypatch.setattr(settings, "use_mock_providers", False)

    def boom(*_args, **_kwargs):
        raise AssertionError("generate_demo_raster must not run in live flood analysis")

    monkeypatch.setattr("app.services.flood.service.generate_demo_raster", boom)

    def fail_scenes(self):
        raise ProviderUnavailableError("flood", "No Sentinel-2 scenes for AOI.")

    monkeypatch.setattr(
        "app.services.flood.service.FloodDetectionService._suitable_sentinel2",
        fail_scenes,
    )
    res = client.post("/api/v1/flood/analyze", json={"scene_kind": "flood"})
    assert res.status_code == 503
    assert "34.5" not in (res.text or "")
    assert "42000" not in (res.text or "")


def test_live_flood_list_omits_seeded_demo_event(client, monkeypatch):
    monkeypatch.setattr(settings, "use_mock_providers", False)
    listed = client.get("/api/v1/flood/events")
    assert listed.status_code == 200
    for item in listed.json().get("items") or []:
        assert item.get("affected_population") != DEMO_AFFECTED_POPULATION or item.get("flooded_area") != DEMO_FLOODED_KM2
        assert "synthetic" not in (item.get("notes") or "").lower()
        assert item.get("validated_flood_boundary") is False


def test_demo_raster_helper_still_exists_for_demo_mode_only():
    rgb = generate_demo_raster("flood", 16)
    assert rgb.shape == (16, 16, 3)


def test_live_flood_get_hides_seeded_demo_row(client, monkeypatch):
    from app.db.session import SessionLocal
    from app.models import FloodAnalysis

    db = SessionLocal()
    try:
        row = FloodAnalysis(
            model_name="demo-flood-seg-v0",
            scene_kind="flood",
            flooded_area=DEMO_FLOODED_KM2,
            affected_population=DEMO_AFFECTED_POPULATION,
            notes="Demo Mode synthetic before/after change.",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        event_id = row.id
    finally:
        db.close()

    monkeypatch.setattr(settings, "use_mock_providers", False)
    res = client.get(f"/api/v1/flood/events/{event_id}")
    assert res.status_code == 404
