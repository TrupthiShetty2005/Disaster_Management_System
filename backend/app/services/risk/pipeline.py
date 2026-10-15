"""Weather → risk → threshold → alert candidate. Thresholds come from alerts/rules.json."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Alert
from app.db.session import new_uuid
from app.services.alerts.rules import dispatch_threshold


def should_raise_flood_alert(flood_probability: float, threshold: float | None = None) -> bool:
    return flood_probability >= (threshold if threshold is not None else dispatch_threshold("flood"))


def should_raise_cyclone_alert(cyclone_risk: float, threshold: float | None = None) -> bool:
    return cyclone_risk >= (threshold if threshold is not None else dispatch_threshold("cyclone"))


def persist_alert_candidate(
    db: Session,
    *,
    title: str,
    severity: str,
    message: str,
    location_id: str | None,
    category: str = "risk_candidate",
) -> Alert:
    from app.core.config import settings
    from app.core.operational import hide_seeded_operations, is_demo_or_simulated_alert

    existing = (
        db.query(Alert)
        .filter(Alert.title == title, Alert.category == category)
        .order_by(Alert.issued_at.desc())
        .all()
    )
    for row in existing:
        if hide_seeded_operations() and is_demo_or_simulated_alert(row):
            continue
        return row
    sev = severity.upper()
    if sev == "SEVERE":
        sev = "CRITICAL"
    lat, lon, aoi_name = settings.demo_latitude, settings.demo_longitude, settings.aoi_name
    try:
        from app.services.geo.aoi import get_aoi

        aoi = get_aoi()
        lat = float(aoi.get("latitude") or lat)
        lon = float(aoi.get("longitude") or lon)
        aoi_name = str(aoi.get("aoi_name") or aoi_name)
    except Exception:
        pass
    official = False
    provenance = "MOCK" if settings.use_mock_providers else "DERIVED_LIVE"
    alert = Alert(
        id=new_uuid(),
        title=title,
        severity=sev,
        category=category,
        alert_type=category,
        message=message,
        location_id=location_id,
        location_name=aoi_name,
        latitude=lat,
        longitude=lon,
        issued_at=datetime.now(timezone.utc).replace(tzinfo=None),
        status="ACTIVE",
        source="visionguard_heuristic" if not settings.use_mock_providers else "weather_intel",
        recommended_action="Validate with authorized personnel. No SMS/email dispatched. Not an official warning.",
        signals={
            "official_warning": official,
            "provenance_status": provenance,
            "kind": "heuristic_risk_candidate",
            "source_model": "WeatherIntelService",
        },
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert
