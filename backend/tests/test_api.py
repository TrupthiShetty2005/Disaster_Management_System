from app.db.seed import DIS_FLOOD


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "VisionGuard AI"
    assert "use_mock_providers" in body
    assert body["data_mode"] in {"DEMO DATA", "REAL DATA"}
    blob = str(body).lower()
    for needle in ("api_key", "client_secret", "password", "appid", "bearer"):
        assert needle not in blob


def test_health_real_data_mode_label(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "use_mock_providers", False)
    body = client.get("/api/v1/health").json()
    assert body["use_mock_providers"] is False
    assert body["data_mode"] == "REAL DATA"


def test_list_disasters(client):
    r = client.get("/api/v1/disasters")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 3
    assert any(d["disaster_type"] == "flood" for d in body["items"])


def test_get_disaster(client):
    r = client.get(f"/api/v1/disasters/{DIS_FLOOD}")
    assert r.status_code == 200
    assert r.json()["id"] == DIS_FLOOD


def test_disaster_not_found(client):
    r = client.get("/api/v1/disasters/00000000-0000-4000-8000-000000000000")
    assert r.status_code == 404
    assert r.json()["code"] == "not_found"


def test_risk_zones_weather_alerts_resources_centers(client):
    assert client.get("/api/v1/risk-zones").status_code == 200
    assert client.get("/api/v1/weather/current").status_code == 200
    assert client.get("/api/v1/weather/forecast").status_code == 200
    assert client.get("/api/v1/alerts").json()["total"] >= 1
    assert client.get("/api/v1/resources").json()["total"] >= 1
    assert client.get("/api/v1/evacuation-centers").json()["total"] >= 1


def test_weather_intel_and_risk_zone_detail(client):
    current = client.get("/api/v1/weather/current")
    assert current.status_code == 200
    body = current.json()
    assert "visibility_km" in body
    assert "river_level_m" in body

    assert client.get("/api/v1/weather/history").status_code == 200
    rain = client.get("/api/v1/weather/rainfall")
    assert rain.status_code == 200
    assert 0 <= rain.json()["short_term_risk"] <= 100

    flood = client.get("/api/v1/risk/flood")
    assert flood.status_code == 200
    assert "Prototype AI Risk Estimate" in flood.json()["estimate_label"]

    alerts = client.get("/api/v1/weather/alerts")
    assert alerts.status_code == 200
    assert "no SMS/email sent" in alerts.json()["dispatch"]

    zones = client.get("/api/v1/risk-zones").json()
    zone_id = zones["items"][0]["id"]
    detail = client.get(f"/api/v1/risk-zones/{zone_id}")
    assert detail.status_code == 200
    assert detail.json()["contributing_factors"]

