from datetime import datetime, timezone

import httpx
import pytest

from app.core.providers import ProviderUnavailableError
from app.services.risk.flood import BaselineFloodRiskModel, FloodRiskInput
from app.services.weather.imd_client import ImdClient
from app.services.weather.nasa_power import NasaPowerClient, power_value
from app.services.weather.openweather_provider import OpenWeatherProvider


def test_openweather_missing_credentials(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.openweather_api_key", None)
    provider = OpenWeatherProvider(api_key=None)
    provider.api_key = None
    with pytest.raises(ProviderUnavailableError, match="OPENWEATHER_API_KEY"):
        provider.current_live(None)


def test_nasa_power_fill_is_not_zero_rain():
    assert power_value(-999) is None
    assert power_value(None) is None
    assert power_value(12.4) == 12.4


def test_nasa_power_skips_fill_values(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.nasa_power_enabled", True)

    class _Resp:
        status_code = 200

        def json(self):
            return {
                "properties": {
                    "parameter": {
                        "PRECTOTCORR": {"20261001": -999, "20261002": 8.5},
                        "T2M": {"20261001": 26.1, "20261002": 25.0},
                        "RH2M": {"20261001": 70, "20261002": -999},
                        "WS2M": {"20261001": 3.2, "20261002": 2.1},
                    }
                }
            }

    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Resp())
    points = NasaPowerClient().fetch_daily(12.97, 77.59, days=2, end=datetime(2026, 10, 2, tzinfo=timezone.utc))
    by_day = {p.observed_at.date().isoformat(): p for p in points}
    assert by_day["2026-10-01"].rainfall_mm is None
    assert "rainfall_mm" in by_day["2026-10-01"].missing_fields
    assert by_day["2026-10-02"].rainfall_mm == 8.5
    assert by_day["2026-10-02"].humidity is None
    assert all(p.river_level_m is None for p in points)
    assert all(p.record_kind == "historical_daily" for p in points)
    assert "mm/day" in points[0].units["rainfall_mm"]
    assert points[0].observed_at.tzinfo is not None


def test_nasa_power_network_error(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.nasa_power_enabled", True)

    def boom(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "get", boom)
    with pytest.raises(ProviderUnavailableError, match="Network"):
        NasaPowerClient().fetch_daily(12.97, 77.59, days=3)


def test_imd_unavailable_without_key():
    client = ImdClient(api_key="")
    status = client.status()
    assert status["configured"] is False
    assert status["available"] is False
    with pytest.raises(ProviderUnavailableError, match="IMD_API_KEY"):
        client.district_warnings()


def test_flood_score_omits_unavailable_river_and_placeholders():
    result = BaselineFloodRiskModel().evaluate(FloodRiskInput(rainfall_mm=40.0, rainfall_intensity=1.2))
    names = [f["name"] for f in result.factors]
    assert any("River level (unavailable)" in n for n in names)
    assert any("Historical flood frequency (unavailable)" in n for n in names)
    assert "scientifically" in result.estimate_label.lower() or "RULE-BASED" in result.estimate_label


def test_live_provider_imd_unconfigured_is_not_empty_all_clear(monkeypatch):
    from app.core.config import settings
    from app.services.weather.live_provider import LiveWeatherProvider

    monkeypatch.setattr(settings, "use_mock_providers", False)
    monkeypatch.setattr(settings, "imd_api_key", None)
    provider = LiveWeatherProvider()
    provider.imd.api_key = None
    with pytest.raises(ProviderUnavailableError, match="NOT_CONFIGURED"):
        provider.alerts(None)


def test_live_weather_alerts_imd_status_not_configured(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "use_mock_providers", False)
    monkeypatch.setattr(settings, "imd_api_key", None)
    monkeypatch.setattr(settings, "openweather_api_key", None)
    res = client.get("/api/v1/weather/alerts")
    assert res.status_code == 200
    body = res.json()
    assert body["imd_source_status"] == "NOT_CONFIGURED"
    imd_items = [i for i in body.get("items") or [] if str(i.get("category") or "").lower() == "imd"]
    assert imd_items == []
    assert "all-clear" not in (body.get("imd_status") or "").lower() or "not" in (body.get("imd_status") or "").lower()
    assert "NOT_CONFIGURED" in (body.get("imd_status") or "") or "IMD_API_KEY" in (body.get("imd_status") or "")


def test_imd_live_empty_payload_is_not_all_clear(monkeypatch):
    from app.core.config import settings
    from app.services.weather.live_provider import LiveWeatherProvider
    from app.services.weather_intel import WeatherIntelService

    monkeypatch.setattr(settings, "use_mock_providers", False)
    monkeypatch.setattr(settings, "imd_api_key", "test-token")
    monkeypatch.setattr(settings, "openweather_api_key", None)

    class _EmptyImd:
        configured = True

        def district_warnings(self):
            return []

        def status(self):
            return {"configured": True, "available": True, "note": "ok"}

    provider = LiveWeatherProvider()
    provider.imd = _EmptyImd()
    intel = WeatherIntelService(db=None)
    intel.provider = provider
    payload = intel.weather_alerts(None)
    assert payload["imd_source_status"] == "LIVE_EMPTY"
    assert payload["provider_alerts"] == []
    assert "not confirmation" in payload["imd_status"].lower() or "not treated" in payload["imd_status"].lower()


def test_live_weather_endpoints_do_not_return_seeded_kuttanad(client):
    cur = client.get("/api/v1/weather/current")
    assert cur.status_code == 200
    body = cur.json()
    assert body["source"] == "mock"
    assert body["observed_at"]
    hist = client.get("/api/v1/weather/history")
    assert hist.status_code == 200
    assert hist.json()["items"]
    assert hist.json()["items"][0]["source"] == "mock"
    fc = client.get("/api/v1/weather/forecast")
    assert fc.status_code == 200
    assert fc.json()["items"][0]["record_kind"] == "forecast"
    assert "period_start" in fc.json()["items"][0]
