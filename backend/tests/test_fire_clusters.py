from datetime import datetime, timedelta, timezone

import pytest

from app.services import fire


@pytest.fixture(autouse=True)
def offline_districts(monkeypatch):
    monkeypatch.setattr(fire.karnataka, "district_for", lambda lat, lon: "ballari")


def _det(lat, lon, when, frp=10.0, conf="nominal"):
    return {"latitude": lat, "longitude": lon, "acquired_at": when.isoformat(), "sensor": "VIIRS_NOAA20", "confidence": conf, "frp_mw": frp, "district_id": "ballari", "district": "Ballari"}


def test_persistent_site_is_classified_industrial(monkeypatch):
    now = datetime.now(timezone.utc)
    steel_plant = [_det(15.178 + 0.002 * (d % 2), 76.667, now - timedelta(days=d, hours=2)) for d in range(6)]
    grass_fire = [_det(15.55, 76.76, now - timedelta(hours=h), frp=12) for h in (2, 3, 4, 5, 6)]
    monkeypatch.setattr(fire, "detections", lambda window: {"detections": steel_plant + grass_fire})

    clusters = {c["persistent_heat_source"]: c for c in fire.clusters("7d")}
    industrial, vegetation = clusters[True], clusters[False]

    assert industrial["days_seen"] >= fire.PERSISTENT_MIN_DAYS
    assert industrial["severity"] == "INFO"
    assert vegetation["detections"] == 5
    assert vegetation["active_24h"] is True
    assert vegetation["severity"] == "WARNING"


def test_far_apart_detections_form_separate_events(monkeypatch):
    now = datetime.now(timezone.utc)
    pts = [_det(13.0, 77.0, now), _det(13.0, 77.1, now)]  # ~10.8 km apart
    monkeypatch.setattr(fire, "detections", lambda window: {"detections": pts})
    assert len(fire.clusters("24h")) == 2
