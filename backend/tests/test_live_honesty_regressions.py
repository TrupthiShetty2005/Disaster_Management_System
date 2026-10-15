"""REAL DATA mode must neither hide genuine live alerts nor invent historical series."""

from types import SimpleNamespace

from app.core.config import settings
from app.core.operational import alert_provenance_status, is_demo_or_simulated_alert
from app.db.session import SessionLocal
from app.services.analytics.service import AnalyticsService
from app.services.weather_intel import WeatherIntelService


def test_live_heuristic_alert_with_index_82_is_not_suppressed():
    class Row:
        source = "visionguard_heuristic"
        title = "Prototype flood risk threshold exceeded"
        message = (
            "Derived risk estimate (not an official government warning). "
            "RULE-BASED index from available weather inputs only: index 82. "
            "No SMS/email dispatched. Not an IMD warning."
        )
        location_id = None
        location_name = "Karnataka, India"
        latitude = 12.9716
        longitude = 77.5946
        signals = {"official_warning": False, "provenance_status": "DERIVED_LIVE"}

    assert is_demo_or_simulated_alert(Row()) is False
    assert alert_provenance_status(Row()) == "DERIVED_LIVE"


def test_real_mode_risk_trend_has_no_fabricated_history(client, monkeypatch):
    monkeypatch.setattr(settings, "use_mock_providers", False)
    monkeypatch.setattr(WeatherIntelService, "flood", lambda self, location_id=None: SimpleNamespace(flood_probability=70.0))
    db = SessionLocal()
    try:
        series = AnalyticsService(db).overview()["series"]
    finally:
        db.close()
    assert series["risk_trend"] == [0.0, 0.0, 0.0, 0.0, 70.0]
