"""REAL DATA mode: no mock fallback, no seeded ops as live results, Karnataka AOI defaults."""

from app.core.config import settings
from app.core.operational import hide_seeded_operations
from app.db.seed import DIS_FLOOD
from app.services.ops import DisasterService, ResourceService
from app.services.risk.flood import BaselineFloodRiskModel, FloodRiskInput, overlay_demo_flood
from app.services.satellite.mock_provider import MockSatelliteProvider, get_satellite_provider
from app.services.weather.factory import get_weather_provider
from app.services.weather.live_provider import LiveWeatherProvider
from app.services.weather.mock_provider import MockWeatherProvider
from app.db.session import SessionLocal


def test_default_settings_are_karnataka_india():
    assert settings.aoi_state == "Karnataka" or "Karnataka" in settings.aoi_name
    assert "India" in settings.aoi_name
    assert "Bengaluru" in settings.openweather_query or "Bangalore" in settings.openweather_query
    assert settings.demo_latitude > 11.5
    assert settings.demo_longitude > 74.0


def test_live_weather_factory_never_returns_mock(monkeypatch):
    monkeypatch.setattr(settings, "use_mock_providers", False)
    assert isinstance(get_weather_provider(), LiveWeatherProvider)
    assert not isinstance(get_weather_provider(), MockWeatherProvider)


def test_live_satellite_factory_never_returns_mock(monkeypatch):
    monkeypatch.setattr(settings, "use_mock_providers", False)
    provider = get_satellite_provider()
    assert not isinstance(provider, MockSatelliteProvider)


def test_overlay_demo_flood_is_noop_in_live(monkeypatch):
    monkeypatch.setattr(settings, "use_mock_providers", False)
    raw = BaselineFloodRiskModel().evaluate(
        FloodRiskInput(
            rainfall_mm=10,
            rainfall_intensity=0.4,
            river_level_m=1.2,
            historical_flood_frequency=0.3,
            terrain_elevation_m=8.0,
            soil_saturation=0.4,
        )
    )
    overlaid = overlay_demo_flood(raw)
    assert overlaid.flood_probability == raw.flood_probability
    assert "SIMULATED" not in (overlaid.estimate_label or "")


def test_live_hides_seeded_disasters_and_resources(client, monkeypatch):
    monkeypatch.setattr(settings, "use_mock_providers", False)
    assert hide_seeded_operations() is True
    disasters = client.get("/api/v1/disasters")
    assert disasters.status_code == 200
    body = disasters.json()
    assert body["total"] == 0
    assert body["items"] == []
    assert client.get(f"/api/v1/disasters/{DIS_FLOOD}").status_code == 404
    assert client.get(f"/api/v1/incidents/{DIS_FLOOD}").status_code == 404
    resources = client.get("/api/v1/resources")
    assert resources.status_code == 200
    assert resources.json()["total"] == 0
    zones = client.get("/api/v1/risk-zones")
    assert zones.status_code == 200
    assert zones.json()["total"] == 0
    overview = client.get("/api/v1/analytics/overview").json()
    assert overview["incident_id"] is None
    assert overview["kpis"]["flooded_area"] != 34.5 or overview["kpis"]["flooded_area"] == 0
    assert overview["kpis"].get("flood_risk_pct") != 82
    assert overview["kpis"].get("rescue_inventory_available") is False
    assert overview["kpis"].get("damage_overlay_available") is False
    assert "SIMULATED" not in (overview.get("estimate_label") or "")


def test_live_gis_does_not_use_demo_mode_error_as_mock(client, monkeypatch):
    monkeypatch.setattr(settings, "use_mock_providers", False)
    monkeypatch.setattr(settings, "gis_overpass_enabled", False)
    res = client.get("/api/v1/gis/features")
    assert res.status_code == 503
    detail = res.json().get("detail", "")
    assert "LIVE" in detail or "disabled" in detail.lower() or "GIS" in detail


def test_demo_mode_still_seeds_for_tests(client, monkeypatch):
    monkeypatch.setattr(settings, "use_mock_providers", True)
    db = SessionLocal()
    try:
        items, total = DisasterService(db).list()
        assert total >= 1
        res_items, _ = ResourceService(db).list()
        assert len(res_items) >= 1
    finally:
        db.close()
