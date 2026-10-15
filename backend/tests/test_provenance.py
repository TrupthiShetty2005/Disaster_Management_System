from app.core.config import settings
from app.services.provenance import build_data_source_status
from app.services.weather.factory import get_weather_provider
from app.services.weather.mock_provider import MockWeatherProvider
from app.services.weather.live_provider import LiveWeatherProvider


def test_demo_mode_uses_mock_weather_provider(monkeypatch):
    monkeypatch.setattr(settings, "use_mock_providers", True)
    assert isinstance(get_weather_provider(), MockWeatherProvider)
    status = build_data_source_status(probe=False)
    assert status["use_mock_providers"] is True
    assert status["modules"]["weather"]["status"] == "MOCK"
    assert status["modules"]["gis"]["status"] == "MOCK"


def test_live_mode_does_not_use_mock_weather_provider(monkeypatch):
    monkeypatch.setattr(settings, "use_mock_providers", False)
    monkeypatch.setattr(settings, "openweather_api_key", "test-key")
    assert isinstance(get_weather_provider(), LiveWeatherProvider)
    status = build_data_source_status(probe=False)
    assert status["use_mock_providers"] is False
    assert status["modules"]["weather"]["status"] in {"LIVE", "NOT_CONFIGURED", "UNAVAILABLE"}
    assert status["modules"]["flood_analysis"]["status"] == "DERIVED_LIVE"
    assert status["modules"]["resources"]["status"] == "UNAVAILABLE"
    assert status["modules"]["incidents"]["status"] == "UNAVAILABLE"
    assert status["modules"]["notifications"]["status"] == "MOCK"
    assert status["modules"]["river_level"]["status"] == "UNAVAILABLE"


def test_data_sources_status_endpoint(client, monkeypatch):
    monkeypatch.setattr(settings, "use_mock_providers", True)
    res = client.get("/api/v1/data-sources/status", params={"probe": "false"})
    assert res.status_code == 200
    body = res.json()
    assert "modules" in body
    assert body["modules"]["notifications"]["status"] == "MOCK"
