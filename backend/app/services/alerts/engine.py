from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.seed import LOC_KUTTANAD
from app.models import Alert, Location
from app.services.alerts.notifications import dispatch
from app.services.alerts.rules import disclaimer, recommended_action, score_to_severity
from app.services.alerts.stream import publish


def _num(value: Any, default: float = 0.0) -> float:
    """Coerce missing gauges (None / NaN) so generate never TypeErrors."""
    if value is None:
        return default
    try:
        n = float(value)
    except (TypeError, ValueError):
        return default
    if n != n:  # NaN
        return default
    return n


@dataclass
class AlertSignals:
    flood_probability: float = 0
    rainfall: float = 0
    river_level: float = 0
    cyclone_probability: float = 0
    wildfire_risk: float = 0
    landslide_risk: float = 0
    damage_severity: float = 0
    location_id: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)


def composite_score(sig: AlertSignals) -> dict[str, float]:
    """Normalize heterogeneous inputs to 0–100 per hazard, then a weighted overall."""
    rain_mm = _num(sig.rainfall)
    river_m = _num(sig.river_level)
    rainfall = min(100.0, rain_mm * 1.6)
    river = min(100.0, max(0.0, (river_m - 1.0) * 40)) if river_m > 0 else 0.0
    parts = {
        "flood": _num(sig.flood_probability),
        "rainfall": rainfall,
        "river": river,
        "cyclone": _num(sig.cyclone_probability),
        "wildfire": _num(sig.wildfire_risk),
        "landslide": _num(sig.landslide_risk),
        "damage": _num(sig.damage_severity),
    }
    overall = round(
        0.28 * parts["flood"]
        + 0.18 * parts["rainfall"]
        + 0.12 * parts["river"]
        + 0.14 * parts["cyclone"]
        + 0.08 * parts["wildfire"]
        + 0.10 * parts["landslide"]
        + 0.10 * parts["damage"],
        1,
    )
    parts["overall"] = overall
    return parts


class AlertEngine:
    """Configurable early-warning engine. Does not send official emergency warnings."""

    def evaluate(self, sig: AlertSignals) -> dict[str, Any]:
        scores = composite_score(sig)
        by_type = {k: score_to_severity(v, k if k != "overall" else "flood") for k, v in scores.items() if k != "overall"}
        overall_sev = score_to_severity(scores["overall"], "flood")
        return {
            "scores": scores,
            "severity_by_type": by_type,
            "overall_severity": overall_sev,
            "recommended_action": recommended_action(overall_sev),
            "disclaimer": disclaimer(),
        }

    def gather_signals(self, db: Session, location_id: str | None = None) -> AlertSignals:
        from app.services.weather_intel import WeatherIntelService
        loc = location_id or (LOC_KUTTANAD if settings.use_mock_providers else None)
        intel = WeatherIntelService(db)
        snap = intel.current(loc)
        rain = intel.rainfall(loc)
        flood = intel.flood(loc)
        cyclone = intel.cyclone(loc)
        rain_mm = _num(getattr(snap, "rainfall_mm", None))
        river_m = getattr(snap, "river_level_m", None)
        return AlertSignals(
            flood_probability=_num(getattr(flood, "flood_probability", None)),
            rainfall=rain_mm,
            river_level=_num(river_m),
            cyclone_probability=_num(getattr(cyclone, "cyclone_risk", None)),
            wildfire_risk=12.0 if settings.use_mock_providers else 0.0,
            landslide_risk=(38.0 if rain_mm > 30 else 18.0) if settings.use_mock_providers else 0.0,
            damage_severity=42.0 if settings.use_mock_providers else 0.0,
            location_id=loc,
            extras={
                "rainfall_intensity": getattr(rain, "intensity_mm_h", None),
                "source": getattr(snap, "source", None),
                "river_gauge_available": river_m is not None,
            },
        )

    def generate(self, db: Session, location_id: str | None = None) -> list[Alert]:
        sig = self.gather_signals(db, location_id)
        evaluation = self.evaluate(sig)
        loc = db.query(Location).filter(Location.id == sig.location_id).first()
        name = loc.name if loc else settings.aoi_name
        lat = loc.latitude if loc else settings.demo_latitude
        lon = loc.longitude if loc else settings.demo_longitude
        created: list[Alert] = []
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for hazard, score in evaluation["scores"].items():
            if hazard == "overall":
                continue
            severity = evaluation["severity_by_type"][hazard]
            if severity == "INFO":
                continue
            title = f"{hazard.title()} {severity.lower()} (prototype)"
            existing_rows = (
                db.query(Alert)
                .filter(Alert.title == title, Alert.status != "RESOLVED")
                .all()
            )
            from app.core.operational import hide_seeded_operations, is_demo_or_simulated_alert

            existing = None
            for row in existing_rows:
                if hide_seeded_operations() and is_demo_or_simulated_alert(row):
                    continue
                existing = row
                break
            if existing:
                created.append(existing)
                continue
            provenance = "MOCK" if settings.use_mock_providers else "DERIVED_LIVE"
            alert = Alert(
                title=title,
                severity=severity,
                category=hazard,
                alert_type=hazard,
                message=(
                    f"Derived risk estimate (not an official government warning). "
                    f"Prototype signal fusion: {hazard} score {score}. "
                    "Not an official IMD/NDMA warning. Validate before public dissemination."
                ),
                location_id=sig.location_id,
                location_name=name,
                latitude=lat,
                longitude=lon,
                risk_score=score,
                issued_at=now,
                expires_at=now + timedelta(hours=12),
                status="ACTIVE",
                recommended_action=recommended_action(severity),
                source="alert_engine",
                reason=f"{hazard}={score}; overall={evaluation['scores']['overall']}",
                signals={
                    "scores": evaluation["scores"],
                    "inputs": sig.extras,
                    "official_warning": False,
                    "provenance_status": provenance,
                    "kind": "heuristic_risk_estimate",
                    "source_model": "AlertEngine",
                },
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)
            receipts = dispatch(alert)
            publish({"type": "alert.created", "id": alert.id, "severity": alert.severity, "title": alert.title})
            alert.signals = {**(alert.signals or {}), "notifications": receipts}
            db.commit()
            created.append(alert)
        return created
