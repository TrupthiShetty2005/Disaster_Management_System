from datetime import timedelta

from sqlalchemy import select

from app.core.errors import SourceUnavailable
from app.db import Alert, utcnow
from app.services import alerts


def _cond(key, severity="WATCH", hazard="flood"):
    now = utcnow()
    return {
        "key": key,
        "hazard": hazard,
        "severity": severity,
        "title": f"{key} {severity}",
        "message": "test condition",
        "district": "Vijayapura",
        "latitude": 16.33,
        "longitude": 75.89,
        "source": "GloFAS",
        "source_url": None,
        "observed_value": 7000.0,
        "threshold": 6200.0,
        "unit": "m³/s",
        "valid_from": now,
        "valid_until": now + timedelta(days=2),
        "payload": {},
    }


def _families(monkeypatch, water=None, fire=None):
    def make(v):
        def fn():
            if isinstance(v, Exception):
                raise v
            return v or []

        return fn

    monkeypatch.setattr(alerts, "FAMILIES", {"water": make(water), "fire": make(fire)})
    monkeypatch.setattr(alerts, "_record_observations", lambda db: None)


def test_lifecycle_create_escalate_resolve(db, monkeypatch):
    _families(monkeypatch, water=[_cond("water:almatti")])
    assert alerts.refresh(db)["created"] == 1

    _families(monkeypatch, water=[_cond("water:almatti", "WARNING")])
    s = alerts.refresh(db)
    assert s["created"] == 0 and s["updated"] == 1
    row = db.scalars(select(Alert)).one()
    assert row.severity == "WARNING" and row.status == "ACTIVE"

    _families(monkeypatch, water=[])
    assert alerts.refresh(db)["resolved"] == 1
    assert db.scalars(select(Alert)).one().status == "RESOLVED"


def test_failed_source_does_not_resolve_its_alerts(db, monkeypatch):
    _families(monkeypatch, fire=[_cond("fire:15.55:76.75", hazard="fire")])
    alerts.refresh(db)
    _families(monkeypatch, fire=SourceUnavailable("firms", "timeout"))
    s = alerts.refresh(db)
    assert s["resolved"] == 0 and "fire" in s["errors"]
    assert db.scalars(select(Alert)).one().status == "ACTIVE"


def test_operator_resolution_holds_until_escalation(db, monkeypatch):
    _families(monkeypatch, water=[_cond("water:krs")])
    alerts.refresh(db)
    row = db.scalars(select(Alert)).one()
    alerts.set_status(db, row.id, "RESOLVED", "operator")

    s = alerts.refresh(db)
    assert s["suppressed"] == 1 and s["created"] == 0

    _families(monkeypatch, water=[_cond("water:krs", "SEVERE")])
    assert alerts.refresh(db)["created"] == 1


def test_expired_alerts_close(db, monkeypatch):
    c = _cond("water:kabini")
    c["valid_until"] = utcnow() - timedelta(minutes=1)
    _families(monkeypatch, water=[c])
    s = alerts.refresh(db)
    assert s["expired"] == 1
