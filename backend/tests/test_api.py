import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.core.errors import SourceUnavailable
from app.main import app


@pytest.fixture()
def client(db):
    return TestClient(app)


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json()["region"] == "Karnataka, India"


def test_unavailable_source_returns_503_with_source_name(client, monkeypatch):
    def down():
        raise SourceUnavailable("open-meteo-flood", "HTTP 429")

    monkeypatch.setattr(routes.water, "stations", lambda include_series=True: down())
    r = client.get("/api/v1/water/stations")
    assert r.status_code == 503
    assert r.json() == {"error": "source_unavailable", "source": "open-meteo-flood", "detail": "HTTP 429"}


def test_unknown_station_is_404(client, monkeypatch):
    def missing(_id):
        raise KeyError(_id)

    monkeypatch.setattr(routes.water, "station", missing)
    assert client.get("/api/v1/water/stations/nope").status_code == 404


def test_rescue_rejects_points_outside_karnataka(client):
    assert client.get("/api/v1/rescue/plan?lat=28.6&lon=77.2").status_code == 422


def test_vision_rejects_non_images(client):
    r = client.post("/api/v1/vision/detect", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_alerts_empty_and_actions_404(client):
    assert client.get("/api/v1/alerts").json() == {"items": [], "total": 0}
    assert client.post("/api/v1/alerts/missing/acknowledge", json={"actor": "x"}).status_code == 404


def test_satellite_preview_validates_bbox(client):
    r = client.get("/api/v1/satellite/preview", params={"key": "sentinel-1-rtc:2026-10-14", "kind": "sar", "bbox": "74,12,76,14"})
    assert r.status_code == 400
