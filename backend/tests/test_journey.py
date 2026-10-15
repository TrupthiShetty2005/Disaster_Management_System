from app.core.demo import (
    DEMO_AFFECTED_POPULATION,
    DEMO_DAMAGED_BUILDINGS,
    DEMO_FLOOD_RISK_PCT,
    DEMO_FLOODED_KM2,
    DEMO_INCIDENT_ID,
)


def test_demo_user_journey(client):
    assert client.get("/api/v1/health").json()["status"] == "ok"
    disasters = client.get("/api/v1/disasters").json()
    assert any(d["id"] == DEMO_INCIDENT_ID for d in disasters["items"])
    assert client.get(f"/api/v1/disasters/{DEMO_INCIDENT_ID}").status_code == 200
    assert client.get("/api/v1/weather/current").status_code == 200
    flood = client.get("/api/v1/risk/flood").json()
    assert flood["flood_probability"] == DEMO_FLOOD_RISK_PCT
    assert "SIMULATED" in flood["estimate_label"]
    assert client.get("/api/v1/satellite/images").status_code == 200
    assert client.post("/api/v1/flood/analyze", json={"scene_kind": "flood"}).status_code == 200
    assert client.post("/api/v1/damage/analyze", json={"before_kind": "flood_before", "after_kind": "flood"}).status_code == 200
    assert client.get("/api/v1/rescue/priorities").status_code == 200
    plan = client.post("/api/v1/rescue/plan", json={"disaster_id": DEMO_INCIDENT_ID})
    assert plan.status_code == 200
    plan_id = plan.json()["id"]
    decision = client.post(
        f"/api/v1/rescue/plans/{plan_id}/decision",
        json={"action": "accept", "notes": "demo"},
    )
    assert decision.status_code == 200
    alerts = client.post("/api/v1/alerts/generate", json={})
    assert alerts.status_code == 200
    overview = client.get("/api/v1/analytics/overview").json()
    assert overview["kpis"]["flooded_area"] == DEMO_FLOODED_KM2
    assert overview["kpis"]["damaged_buildings"] == DEMO_DAMAGED_BUILDINGS
    incident = client.get(f"/api/v1/incidents/{DEMO_INCIDENT_ID}").json()
    assert incident["incident"]["people_at_risk"] == DEMO_AFFECTED_POPULATION
    export = client.get("/api/v1/exports/analytics")
    assert export.status_code == 200
