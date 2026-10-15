from app.db.seed import DIS_FLOOD
from app.models import AuditLog, RescueResource
from app.services.rescue.priority import PriorityInput, RescuePriorityService, band
from app.services.rescue.recommend import recommend_resources
from app.services.rescue.routing import edge_cost, shortest_path


def test_priority_score_bands():
    svc = RescuePriorityService()
    low = svc.evaluate(
        PriorityInput(500, "low", 10, 0.05, "open", "low", 1.0, 0.1)
    )
    high = svc.evaluate(
        PriorityInput(20000, "critical", 2000, 0.8, "blocked", "critical", 8.0, 0.9)
    )
    assert low["score"] < high["score"]
    assert 0 <= low["score"] <= 100
    assert high["level"] in {"HIGH", "CRITICAL"}
    assert band(20) == "LOW"
    assert band(90) == "CRITICAL"


def test_resource_recommendation_rules():
    rec = recommend_resources(
        flood_severity="critical",
        population_affected=18000,
        medical_urgency=0.7,
        road_accessibility="blocked",
        shelter_occupancy=0.8,
        people_stranded=400,
    )
    types = {i["type"] for i in rec["required"]}
    assert "RESCUE_BOAT" in types
    assert "AMBULANCE" in types
    assert "MEDICAL_TEAM" in types
    assert "Prototype" in rec["estimate_label"]
    assert rec["warnings"]


def test_route_scoring_avoids_blocked():
    blocked_cost = edge_cost(1.4, 0.7, 0.8, "blocked", True)
    open_cost = edge_cost(1.6, 0.4, 0.1, "open", True)
    assert blocked_cost is None
    assert open_cost is not None
    path = shortest_path("incident", "shelter", safer=True)
    assert path["path"]
    assert "junction_west" not in path["path"] or "bypass" in path["path"]
    assert path["score"] > 0


def test_rescue_api_allocate_plan_override(client):
    listed = client.get("/api/v1/resources")
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert any(i["resource_type"] == "HELICOPTER" for i in items)
    avail = next((i for i in items if i["status"] == "AVAILABLE"), items[0])
    alloc = client.post(
        "/api/v1/resources/allocate",
        json={"resource_id": avail["id"], "incident_id": DIS_FLOOD},
    )
    assert alloc.status_code == 200
    assert alloc.json()["status"] == "DEPLOYED"
    assert alloc.json()["assigned_incident"] == DIS_FLOOD

    prios = client.get("/api/v1/rescue/priorities")
    assert prios.status_code == 200
    assert prios.json()["total"] >= 1
    assert prios.json()["items"][0]["score"] >= 0

    plan = client.post("/api/v1/rescue/plan", json={})
    assert plan.status_code == 200
    body = plan.json()
    assert body["decision"] == "PENDING"
    assert "recommended_allocation" in body["plan"]
    assert "reasoning" in body["plan"]
    pid = body["id"]
    fetched = client.get(f"/api/v1/rescue/plans/{pid}")
    assert fetched.status_code == 200

    rejected = client.post(
        f"/api/v1/rescue/plans/{pid}/decision",
        json={"action": "reject", "notes": "Need more boats"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["decision"] == "REJECTED"

    plan2 = client.post("/api/v1/rescue/plan", json={"disaster_id": DIS_FLOOD})
    accepted = client.post(
        f"/api/v1/rescue/plans/{plan2.json()['id']}/decision",
        json={"action": "accept", "notes": ""},
    )
    assert accepted.status_code == 200
    assert accepted.json()["decision"] == "ACCEPTED"

    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        logs = db.query(AuditLog).filter(AuditLog.entity_type == "rescue_plan").all()
        assert any("reject" in (l.action or "") for l in logs)
        boats = db.query(RescueResource).filter(RescueResource.status == "DEPLOYED").count()
        assert boats >= 1
    finally:
        db.close()
