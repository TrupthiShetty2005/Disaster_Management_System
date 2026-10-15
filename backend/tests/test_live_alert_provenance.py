"""REAL DATA mode must not surface persisted demo/simulated alerts as live warnings."""

from datetime import datetime, timezone

from app.core.config import settings
from app.core.operational import alert_provenance_status, is_demo_or_simulated_alert, is_official_warning
from app.db.session import SessionLocal
from app.models import Alert
from app.services.risk.pipeline import persist_alert_candidate


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _insert(**kwargs) -> Alert:
    db = SessionLocal()
    try:
        row = Alert(
            issued_at=_now(),
            status="ACTIVE",
            **kwargs,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    finally:
        db.close()


def test_legacy_82_percent_signature_without_relying_on_simulated_word_alone():
    class Row:
        source = "weather_intel"
        title = "Prototype flood risk threshold exceeded"
        message = "Prototype AI Risk Estimate: flood probability 82%. Pre-stage boats."
        location_id = None
        location_name = "Kuttanad"
        latitude = 9.517
        longitude = 76.522
        signals = None

    assert is_demo_or_simulated_alert(Row())
    assert alert_provenance_status(Row()) == "MOCK"
    assert is_official_warning(Row()) is False


def test_simulated_alert_metadata_flags_demo():
    class Row:
        source = "seed"
        title = "Watch"
        message = "Flood watch"
        location_id = "11111111-1111-4111-8111-111111111111"
        location_name = ""
        latitude = 12.97
        longitude = 77.59
        signals = {"provenance_status": "SEEDED", "official_warning": False}

    assert is_demo_or_simulated_alert(Row())


def test_genuine_live_heuristic_not_treated_as_demo():
    class Row:
        source = "visionguard_heuristic"
        title = "Prototype flood risk threshold exceeded"
        message = "Derived risk estimate (not an official government warning). RULE-BASED index: index 1."
        location_id = None
        location_name = "Karnataka, India"
        latitude = 12.9716
        longitude = 77.5946
        signals = {
            "official_warning": False,
            "provenance_status": "DERIVED_LIVE",
            "kind": "heuristic_risk_candidate",
            "source_model": "WeatherIntelService",
        }

    assert is_demo_or_simulated_alert(Row()) is False
    assert alert_provenance_status(Row()) == "DERIVED_LIVE"
    assert is_official_warning(Row()) is False


def test_live_list_hides_legacy_82_keeps_genuine_and_does_not_delete(client, monkeypatch):
    legacy = _insert(
        title="Prototype flood risk threshold exceeded",
        severity="CRITICAL",
        category="risk_candidate",
        alert_type="risk_candidate",
        message="SIMULATED DATA · Prototype AI Risk Estimate: flood probability 82%. Pre-stage boats.",
        source="weather_intel",
        latitude=9.517,
        longitude=76.522,
        location_name="Kuttanad",
    )
    simulated = _insert(
        title="Heavy rainfall watch (demo leftover)",
        severity="WARNING",
        category="weather",
        message="SIMULATED DATA leftover row",
        source="demo",
        latitude=9.517,
        longitude=76.522,
    )
    genuine = _insert(
        title="Live heuristic flood candidate",
        severity="WARNING",
        category="risk_candidate",
        message="Derived risk estimate from OpenWeather inputs. Index 1.",
        source="visionguard_heuristic",
        latitude=12.9716,
        longitude=77.5946,
        location_name="Karnataka, India",
        signals={
            "official_warning": False,
            "provenance_status": "DERIVED_LIVE",
            "kind": "heuristic_risk_candidate",
        },
    )
    official = _insert(
        title="IMD cyclone warning",
        severity="CRITICAL",
        category="cyclone",
        message="Official IMD bulletin excerpt.",
        source="imd",
        latitude=13.0,
        longitude=77.5,
        signals={"official_warning": True, "provenance_status": "LIVE", "kind": "official_warning"},
    )

    demo_list = client.get("/api/v1/alerts").json()
    demo_ids = {a["id"] for a in demo_list["items"]}
    assert legacy.id in demo_ids
    assert simulated.id in demo_ids

    monkeypatch.setattr(settings, "use_mock_providers", False)
    live_list = client.get("/api/v1/alerts").json()
    live_ids = {a["id"] for a in live_list["items"]}
    assert legacy.id not in live_ids
    assert simulated.id not in live_ids
    assert genuine.id in live_ids
    assert official.id in live_ids
    genuine_out = next(a for a in live_list["items"] if a["id"] == genuine.id)
    assert genuine_out["official_warning"] is False
    assert genuine_out["provenance_status"] == "DERIVED_LIVE"
    assert "Derived risk estimate" in genuine_out["message"]
    assert "82" not in genuine_out["message"]
    official_out = next(a for a in live_list["items"] if a["id"] == official.id)
    assert official_out["official_warning"] is True
    assert official_out["provenance_status"] == "LIVE"

    assert client.get(f"/api/v1/alerts/{legacy.id}").status_code == 404
    assert client.get(f"/api/v1/alerts/{genuine.id}").status_code == 200

    db = SessionLocal()
    try:
        assert db.query(Alert).filter(Alert.id == legacy.id).first() is not None
        assert db.query(Alert).filter(Alert.id == simulated.id).first() is not None
    finally:
        db.close()


def test_persist_does_not_reuse_legacy_simulated_row_in_live(monkeypatch):
    monkeypatch.setattr(settings, "use_mock_providers", False)
    leftover = _insert(
        title="Prototype flood risk threshold exceeded",
        severity="CRITICAL",
        category="risk_candidate",
        message="SIMULATED DATA · Prototype AI Risk Estimate: flood probability 82%. Pre-stage boats.",
        source="weather_intel",
        latitude=9.517,
        longitude=76.522,
    )
    db = SessionLocal()
    try:
        created = persist_alert_candidate(
            db,
            title="Prototype flood risk threshold exceeded",
            severity="critical",
            message="Derived risk estimate (not an official government warning). RULE-BASED index: index 1.",
            location_id=None,
        )
        assert created.id != leftover.id
        assert "82" not in (created.message or "")
        assert (created.signals or {}).get("provenance_status") == "DERIVED_LIVE"
        assert (created.signals or {}).get("official_warning") is False
        assert db.query(Alert).filter(Alert.id == leftover.id).first() is not None
    finally:
        db.close()


def test_unknown_provenance_is_not_official(client, monkeypatch):
    unknown = _insert(
        title="Unlabelled bulletin",
        severity="WARNING",
        category="weather",
        message="Source not tagged.",
        source="unknown_feed",
        latitude=12.97,
        longitude=77.59,
        signals=None,
    )
    monkeypatch.setattr(settings, "use_mock_providers", False)
    listed = client.get("/api/v1/alerts").json()["items"]
    row = next(a for a in listed if a["id"] == unknown.id)
    assert row["official_warning"] is False
    assert row["provenance_status"] == "UNKNOWN"
    assert "Unverified provenance" in row["message"]
