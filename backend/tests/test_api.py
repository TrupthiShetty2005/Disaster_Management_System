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


def test_analysis_assets_backfilled_from_stored_geojson_and_kept(client, db, monkeypatch):
    from shapely.geometry import box, mapping

    from app.db import Analysis

    a = Analysis(kind="burn", area_name="Test area", bbox=[76.0, 15.0, 76.02, 15.02], geojson={"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"class": "burned"}, "geometry": mapping(box(76.0, 15.0, 76.01, 15.01))}]}, impact={})
    db.add(a)
    db.commit()
    calls = []
    infra = [{"type": "way", "id": 7, "tags": {"building": "yes"}, "center": {"lat": 15.005, "lon": 76.005}}]
    monkeypatch.setattr(routes.impact.osm, "infrastructure", lambda bbox: calls.append(bbox) or infra)
    ring = [{"lon": 76.0049, "lat": 15.0049}, {"lon": 76.0051, "lat": 15.0049}, {"lon": 76.0051, "lat": 15.0051}, {"lon": 76.0049, "lat": 15.0049}]
    monkeypatch.setattr(routes.impact.osm, "building_geometries", lambda ids: {7: ring})

    r = client.get(f"/api/v1/analyses/{a.id}/assets")
    assert r.status_code == 200
    body = r.json()
    assert body["analysis_id"] == a.id and body["summary"]["buildings_affected"] == 1
    assert body["buildings"]["features"][0]["properties"]["damage_class"] == "burned"
    assert client.get(f"/api/v1/analyses/{a.id}/assets").json() == body
    assert len(calls) == 1  # second request served from the stored assets.json
    assert client.get("/api/v1/analyses/missing/assets").status_code == 404


def test_satellite_preview_validates_bbox(client):
    r = client.get("/api/v1/satellite/preview", params={"key": "sentinel-1-rtc:2026-10-14", "kind": "sar", "bbox": "74,12,76,14"})
    assert r.status_code == 400
