from app.core.demo import DEMO_INCIDENT_ID, DEMO_LOCATION_ID


def test_analytics_and_exports(client):
    ov = client.get("/api/v1/analytics/overview")
    assert ov.status_code == 200
    body = ov.json()
    assert body["incident_id"] == DEMO_INCIDENT_ID
    assert "total_disasters" in body["kpis"]
    assert client.get("/api/v1/analytics/disasters").status_code == 200
    assert client.get("/api/v1/analytics/damage").status_code == 200
    assert client.get("/api/v1/analytics/resources").status_code == 200
    assert client.get("/api/v1/analytics/risks").status_code == 200
    assert client.get("/api/v1/analytics/alerts").status_code == 200
    ranged = client.get("/api/v1/analytics/overview", params={"disaster_type": "flood", "location_id": DEMO_LOCATION_ID})
    assert ranged.status_code == 200


def test_incident_command_and_reports(client):
    pic = client.get(f"/api/v1/incidents/{DEMO_INCIDENT_ID}")
    assert pic.status_code == 200
    body = pic.json()
    assert body["incident"]["id"] == DEMO_INCIDENT_ID
    assert body["narrative"]
    assert "flood_map" in body["links"]
    report = client.post("/api/v1/reports/generate", json={"kind": "incident", "disaster_id": DEMO_INCIDENT_ID})
    assert report.status_code == 200
    assert report.json()["pdf_available"] is False
    csv = client.get("/api/v1/exports/analytics")
    assert csv.status_code == 200
    assert "text/csv" in csv.headers.get("content-type", "")
    assert client.get("/api/v1/audit-logs").status_code == 200
