"""Integration tests against real external APIs (no secrets required for NASA/STAC)."""

import pytest

from app.core.config import settings
from app.services.satellite.copernicus_provider import CopernicusStacProvider
from app.services.weather.imd_client import ImdClient
from app.services.weather.nasa_power import NasaPowerClient


@pytest.mark.integration
def test_nasa_power_history_kuttanad():
    points = NasaPowerClient().fetch_daily(settings.demo_latitude, settings.demo_longitude, days=7)
    assert len(points) >= 3
    assert all(p.source == "nasa-power" for p in points)
    assert any(p.temperature_c > -50 for p in points)


@pytest.mark.integration
def test_copernicus_stac_search_and_thumbnail():
    provider = CopernicusStacProvider()
    scenes = provider.refresh()
    assert len(scenes) >= 1
    assert any(s.source == "sentinel-2" for s in scenes)
    optical = next(s for s in scenes if s.source == "sentinel-2")
    assert optical.metadata.get("stac_id")
    label = str(optical.metadata.get("data_label") or "")
    assert "not real-time" in label.lower()
    assert optical.metadata.get("live_stream") is False
    thumb = provider.fetch_thumbnail_bytes(optical.id)
    assert len(thumb) > 1000


def test_imd_unavailable_without_key():
    client = ImdClient(api_key="")
    status = client.status()
    assert status["configured"] is False
    assert status["available"] is False
    assert "fake" not in status["note"].lower() or "no fake" in status["note"].lower()
