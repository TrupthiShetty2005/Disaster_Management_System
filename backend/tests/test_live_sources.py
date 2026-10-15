"""Calls the real external services. Run with: pytest -m integration"""

import pytest

from app.geo.karnataka import KARNATAKA_BBOX
from app.services import fire, water
from app.sources import firms, gdacs, openmeteo, planetary

pytestmark = pytest.mark.integration


def test_firms_south_asia_feed_has_karnataka_window():
    d = firms.detections("24h")
    assert d["feeds"], d.get("feed_errors")
    w, s, e, n = KARNATAKA_BBOX
    assert all(w <= p["longitude"] <= e and s <= p["latitude"] <= n for p in d["detections"])


def test_glofas_discharge_and_forecast_for_almatti():
    rep = water.station("almatti")
    assert rep["current"]["discharge"] is not None
    assert any(p["forecast"] for p in rep["series"])


def test_open_meteo_daily_weather():
    rows = openmeteo.daily_weather(((12.97, 77.59),), past_days=3, forecast_days=3)
    assert rows[0]["daily"]["precipitation_sum"]


def test_planetary_computer_has_recent_sentinel1_over_tungabhadra():
    items = planetary.recent("sentinel-1-rtc", (76.2, 15.1, 76.5, 15.4), days=60)
    assert items, "no Sentinel-1 RTC scene in 60 days"


def test_gdacs_reachable():
    assert isinstance(gdacs.india_events(), list)


def test_fire_danger_forecast_covers_all_districts():
    assert len(fire.danger_forecast()) == 31
