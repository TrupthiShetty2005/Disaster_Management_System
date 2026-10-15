from app.core.config import settings
from app.core.demo import DEMO_INCIDENT_ID, DEMO_REGION


def test_live_incident_report_rejects_missing_and_seeded_ids(client, monkeypatch):
    monkeypatch.setattr(settings, "use_mock_providers", False)
    missing = client.post("/api/v1/reports/generate", json={"kind": "incident"})
    assert missing.status_code == 503
    detail = missing.json().get("detail", "")
    assert "DEMO_INCIDENT_ID" in detail or "disaster_id" in detail or "live incident" in detail.lower()
    assert DEMO_REGION not in (missing.text or "")

    seeded = client.post(
        "/api/v1/reports/generate",
        json={"kind": "incident", "disaster_id": DEMO_INCIDENT_ID},
    )
    assert seeded.status_code == 503
    assert DEMO_INCIDENT_ID not in str(seeded.json().get("incident_id"))


def test_live_aoi_scoped_damage_report_does_not_use_kuttanad(client, monkeypatch):
    monkeypatch.setattr(settings, "use_mock_providers", False)
    res = client.post("/api/v1/reports/generate", json={"kind": "damage"})
    assert res.status_code == 200
    body = res.json()
    assert body.get("incident_id") in (None, "")
    assert DEMO_REGION not in str(body.get("region", ""))
    assert "Karnataka" in str(body.get("region", "")) or "Bengaluru" in str(body.get("region", ""))
    assert body.get("data_mode") == "REAL DATA"
    assert "Kuttanad" not in (body.get("disclaimer") or "")
