from datetime import datetime, timedelta, timezone

import pytest
from shapely.geometry import box

from app.core.errors import SourceUnavailable
from app.services import fire
from app.sources import firms


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(fire.karnataka, "district_for", lambda lat, lon: "dakshina-kannada")
    monkeypatch.setattr(fire.settings, "firms_map_key", None)


def _det(lat, lon, when, frp=8.0, sensor="VIIRS_NOAA20"):
    return {"latitude": lat, "longitude": lon, "acquired_at": when.isoformat(), "sensor": sensor, "confidence": "nominal", "frp_mw": frp}


def test_coastal_band_keeps_shoreline_points_but_not_inland_borders(monkeypatch):
    # Stand-in state outline whose west edge is the coastline at 74.85 E.
    monkeypatch.setattr(fire.karnataka, "_state_shape", lambda: box(74.85, 11.6, 77.5, 18.0))
    fire._coastal_band.cache_clear()
    try:
        assert fire.in_state(13.0, 74.90)
        assert fire.in_state(13.0, 74.84)  # ~1 km offshore of a simplified coastline: kept
        assert not fire.in_state(13.0, 74.80)  # ~5 km out at sea: dropped
        assert not fire.in_state(13.0, 77.51)  # just across the inland eastern border: dropped
        assert not fire.in_state(12.70, 74.84)  # south of Talapady (Kerala coast): dropped
    finally:
        fire._coastal_band.cache_clear()


def test_persistent_flare_is_attributed_to_monitored_site(monkeypatch):
    now = datetime.now(timezone.utc)
    flare = [_det(12.9856 + 0.001 * (d % 2), 74.8429, now - timedelta(days=d, hours=1)) for d in range(5)]
    monkeypatch.setattr(fire, "detections", lambda window: {"detections": flare})

    (c,) = fire.clusters("7d")
    assert c["persistent_heat_source"] is True
    assert c["severity"] == "INFO"
    assert c["nearest_site"]["id"] == "mrpl"
    assert "MRPL" in c["classification"]
    assert [m["acquired_at"] for m in c["members"]] == sorted((m["acquired_at"] for m in c["members"]), reverse=True)
    assert len(c["members"]) == 5


def test_monitored_sites_counts_and_honest_absence(monkeypatch):
    now = datetime.now(timezone.utc)
    jsw = _det(15.182, 76.670, now - timedelta(hours=3), frp=40)
    old_jsw = _det(15.183, 76.668, now - timedelta(days=5))
    far = _det(13.89, 74.69, now - timedelta(days=2))  # ~100 km north of MRPL
    by_window = {"24h": [jsw], "48h": [jsw], "7d": [jsw, old_jsw, far]}
    monkeypatch.setattr(firms, "detections", lambda w: {"detections": by_window[w], "feeds": {"VIIRS_NOAA20": len(by_window[w])}})

    def no_clouds(points):
        raise SourceUnavailable("open-meteo", "offline")

    monkeypatch.setattr(fire, "_cloud_at_satellite_passes", no_clouds)

    res = fire.monitored_sites()
    sites = {s["id"]: s for s in res["items"]}

    assert sites["jsw-toranagallu"]["counts"] == {"24h": 1, "48h": 1, "7d": 2}
    assert sites["jsw-toranagallu"]["status"] == "DETECTED_24H"
    assert sites["jsw-toranagallu"]["history"][0]["nearest_facility"].startswith("JSW")

    mrpl = sites["mrpl"]
    assert mrpl["status"] == "NO_DETECTION"
    assert mrpl["counts"] == {"24h": 0, "48h": 0, "7d": 0}
    assert mrpl["history"] == []
    assert 95 < mrpl["nearest_detection"]["distance_km"] < 110
    assert "No satellite thermal detection" in mrpl["summary"]

    assert res["archive"]["map_key_configured"] is False
    assert res["archive"]["windows"] == ["24h", "48h", "7d"]
    assert "No FIRMS MAP_KEY" in res["archive"]["note"]


def test_ten_day_window_requires_map_key():
    with pytest.raises(SourceUnavailable):
        firms.detections("10d")
