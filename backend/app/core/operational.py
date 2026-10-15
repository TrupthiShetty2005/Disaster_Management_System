"""Helpers for REAL DATA mode: never surface seeded/demo ops as live results."""

from app.core.config import settings
from app.db.seed import DIS_CYCLONE, DIS_FLOOD, DIS_LANDSLIDE, LOC_GUWAHATI, LOC_KUTTANAD, LOC_PURI

SEEDED_DISASTER_IDS = frozenset({DIS_FLOOD, DIS_LANDSLIDE, DIS_CYCLONE})
SEEDED_LOCATION_IDS = frozenset({LOC_KUTTANAD, LOC_GUWAHATI, LOC_PURI})


def is_demo_mode() -> bool:
    return bool(settings.use_mock_providers)


def hide_seeded_operations() -> bool:
    """True in REAL DATA mode — seeded inventory/incidents must not appear as operations."""
    return not is_demo_mode()


def is_seeded_disaster_id(disaster_id: str | None) -> bool:
    return bool(disaster_id) and disaster_id in SEEDED_DISASTER_IDS


# Legacy overlay_demo_flood / seed signatures (do not treat as live warnings).
_DEMO_ALERT_SOURCES = frozenset({"mock", "seed", "demo", "seeded"})
_KERALA_DEMO_LAT = 9.517
_KERALA_DEMO_LON = 76.522


def _alert_blob(alert) -> str:
    parts = [
        getattr(alert, "source", None),
        getattr(alert, "title", None),
        getattr(alert, "message", None),
        getattr(alert, "reason", None),
        getattr(alert, "location_name", None),
        getattr(alert, "alert_type", None),
        getattr(alert, "category", None),
    ]
    return " ".join(str(p or "") for p in parts).lower()


def _alert_signals(alert) -> dict:
    raw = getattr(alert, "signals", None)
    return raw if isinstance(raw, dict) else {}


def alert_provenance_status(alert) -> str:
    """Classify an alert. LIVE here means official provider product, not VisionGuard heuristics."""
    signals = _alert_signals(alert)
    tagged = str(signals.get("provenance_status") or "").upper()
    if tagged in {"SEEDED", "MOCK", "DERIVED_LIVE", "LIVE", "UNKNOWN"}:
        if tagged in {"DERIVED_LIVE", "LIVE"} and is_demo_or_simulated_alert(alert, ignore_signals=True):
            return "MOCK"
        return tagged
    if is_demo_or_simulated_alert(alert, ignore_signals=True):
        return "MOCK"
    source = str(getattr(alert, "source", "") or "").lower()
    if source in {"imd"} or str(signals.get("kind") or "") == "official_warning":
        return "LIVE"
    if source in {"weather_intel", "visionguard_heuristic", "engine", "alert_engine"}:
        return "DERIVED_LIVE"
    return "UNKNOWN"


def is_official_warning(alert) -> bool:
    signals = _alert_signals(alert)
    if signals.get("official_warning") is True:
        return True
    if signals.get("official_warning") is False:
        return False
    return str(getattr(alert, "source", "") or "").lower() == "imd"


def is_demo_or_simulated_alert(alert, *, ignore_signals: bool = False) -> bool:
    """True for Demo Mode / seed / overlay_demo_flood leftovers. Does not delete rows."""
    if not ignore_signals:
        status = str(_alert_signals(alert).get("provenance_status") or "").upper()
        if status in {"MOCK", "SEEDED"}:
            return True
        if status == "DERIVED_LIVE" and not _legacy_demo_signature(alert):
            return False
    source = str(getattr(alert, "source", "") or "").lower()
    if source in _DEMO_ALERT_SOURCES:
        return True
    loc = str(getattr(alert, "location_id", "") or "")
    if loc in SEEDED_LOCATION_IDS:
        return True
    return _legacy_demo_signature(alert)


def _legacy_demo_signature(alert) -> bool:
    blob = _alert_blob(alert)
    if "demo" in blob:
        return True
    if "simulated data" in blob or ("simulated" in blob and "prototype ai risk estimate" in blob):
        return True
    if "prototype ai risk estimate" in blob:
        return True
    if "kuttanad" in blob:
        return True
    if "flood probability 82" in blob:
        return True
    try:
        lat = float(getattr(alert, "latitude", 0) or 0)
        lon = float(getattr(alert, "longitude", 0) or 0)
    except (TypeError, ValueError):
        lat, lon = 0.0, 0.0
    if abs(lat - _KERALA_DEMO_LAT) < 0.02 and abs(lon - _KERALA_DEMO_LON) < 0.02:
        signals = _alert_signals(alert)
        if str(signals.get("provenance_status") or "").upper() != "DERIVED_LIVE":
            return True
    return False


def is_seeded_alert(alert) -> bool:
    """Hide from REAL DATA list/get. Demo Mode still returns these rows."""
    return is_demo_or_simulated_alert(alert)


def is_authoritative_live_warning(alert) -> bool:
    if hide_seeded_operations() and is_demo_or_simulated_alert(alert):
        return False
    return is_official_warning(alert)
