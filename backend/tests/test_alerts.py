from app.services.alerts.engine import AlertEngine, AlertSignals
from app.services.alerts.notifications import (
    DashboardNotificationProvider,
    EmailNotificationProvider,
    SMSNotificationProvider,
    dispatch,
)
from app.services.alerts.rules import score_to_severity
from app.services.alerts.stream import publish, recent


class _FakeAlert:
    id = "x"
    title = "t"
    message = "m"
    severity = "WATCH"


def test_thresholds_from_rules():
    assert score_to_severity(10, "flood") == "INFO"
    assert score_to_severity(35, "flood") == "WATCH"
    assert score_to_severity(60, "flood") == "WARNING"
    assert score_to_severity(80, "flood") == "CRITICAL"
    assert score_to_severity(50, "cyclone") == "WARNING"
    assert score_to_severity(50, "cyclone") != score_to_severity(50, "wildfire")


def test_composite_score_null_gauges():
    from app.services.alerts.engine import composite_score

    scores = composite_score(
        AlertSignals(flood_probability=0.6, rainfall=None, river_level=None, cyclone_probability=None)  # type: ignore[arg-type]
    )
    assert scores["rainfall"] == 0
    assert scores["river"] == 0
    assert scores["cyclone"] == 0
    assert scores["flood"] == 0.6
    ev = AlertEngine().evaluate(
        AlertSignals(flood_probability=0.6, rainfall=None, river_level=None, cyclone_probability=None)  # type: ignore[arg-type]
    )
    assert "scores" in ev


def test_engine_evaluation():
    ev = AlertEngine().evaluate(
        AlertSignals(flood_probability=82, rainfall=50, river_level=2.4, cyclone_probability=20)
    )
    assert ev["overall_severity"] in {"WATCH", "WARNING", "CRITICAL"}
    assert "decision-support prototype" in ev["disclaimer"]


def test_notification_adapters_are_mock():
    receipts = dispatch(_FakeAlert(), [DashboardNotificationProvider(), EmailNotificationProvider(), SMSNotificationProvider()])
    assert receipts[0]["delivered"] is True
    assert receipts[1]["mode"] == "mock"
    assert receipts[2]["mode"] == "mock"


def test_stream_publish():
    publish({"type": "test.event", "id": "1"})
    assert any(e.get("type") == "test.event" for e in recent())


def test_alert_api_generate_ack_filter(client):
    gen = client.post("/api/v1/alerts/generate", json={})
    assert gen.status_code == 200
    assert gen.json()["total"] >= 1
    item = gen.json()["items"][0]
    assert item["disclaimer"]
    aid = item["id"]
    one = client.get(f"/api/v1/alerts/{aid}")
    assert one.status_code == 200
    ack = client.post(f"/api/v1/alerts/{aid}/acknowledge", json={"actor": "tester"})
    assert ack.status_code == 200
    assert ack.json()["status"] == "ACKNOWLEDGED"
    assert ack.json()["acknowledged_by"] == "tester"
    resolved = client.post(f"/api/v1/alerts/{aid}/resolve", json={"actor": "tester"})
    assert resolved.json()["status"] == "RESOLVED"
    listed = client.get("/api/v1/alerts", params={"status": "RESOLVED"})
    assert listed.status_code == 200
    assert any(a["id"] == aid for a in listed.json()["items"])
    filtered = client.get("/api/v1/alerts", params={"severity": "CRITICAL"})
    assert filtered.status_code == 200
    events = client.get("/api/v1/alerts/events")
    assert events.status_code == 200
