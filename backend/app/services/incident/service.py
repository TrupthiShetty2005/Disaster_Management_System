from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.demo import DEMO_INCIDENT_ID, DEMO_LOCATION_ID, DEMO_NARRATIVE, DEMO_REGION
from app.core.operational import hide_seeded_operations
from app.models import (
    Alert,
    AuditLog,
    Building,
    Disaster,
    FloodEvent,
    Infrastructure,
    RescuePlan,
    RescuePriority,
    RescueResource,
    RiskZone,
    Road,
    WeatherObservation,
)
from app.schemas.common import DisasterOut


class IncidentCommandService:
    """Assembles weather → risk → alert, satellite → GIS, and CV → rescue onto one incident."""

    def __init__(self, db: Session):
        self.db = db

    def picture(self, disaster_id: str | None = None) -> dict[str, Any]:
        if hide_seeded_operations():
            from fastapi import HTTPException

            raise HTTPException(
                status_code=404,
                detail=(
                    "No live operational incident. Seeded demo case files are disabled in REAL DATA mode. "
                    f"Use Weather / Satellite / Flood for {settings.aoi_name}."
                ),
            )
        did = disaster_id or DEMO_INCIDENT_ID
        disaster = self.db.query(Disaster).filter(Disaster.id == did).first()
        if not disaster:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Incident not found")
        loc_id = disaster.location_id
        weather = (
            self.db.query(WeatherObservation)
            .filter(WeatherObservation.location_id == loc_id)
            .order_by(WeatherObservation.observed_at.desc())
            .first()
        )
        zones = self.db.query(RiskZone).filter(RiskZone.location_id == loc_id).all()
        flood = self.db.query(FloodEvent).filter(FloodEvent.disaster_id == did).first()
        alerts = self.db.query(Alert).filter(Alert.location_id == loc_id).order_by(Alert.issued_at.desc()).all()
        resources = self.db.query(RescueResource).filter(RescueResource.location_id == loc_id).all()
        prios = self.db.query(RescuePriority).filter(RescuePriority.disaster_id == did).all()
        plan = (
            self.db.query(RescuePlan)
            .filter(RescuePlan.disaster_id == did)
            .order_by(RescuePlan.created_at.desc())
            .first()
        )
        roads = self.db.query(Road).filter(Road.location_id == loc_id).all()
        buildings = self.db.query(Building).filter(Building.location_id == loc_id).all()
        infra = self.db.query(Infrastructure).filter(Infrastructure.location_id == loc_id).all()
        audits = (
            self.db.query(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .limit(25)
            .all()
        )
        start = disaster.started_at or datetime(2026, 7, 12)
        timeline = [
            {"t": (start + timedelta(hours=h)).isoformat(), "event": ev}
            for h, ev in enumerate(DEMO_NARRATIVE)
        ]
        return {
            "incident": DisasterOut.model_validate(disaster).model_dump(mode="json"),
            "region": DEMO_REGION,
            "location_id": loc_id,
            "narrative": DEMO_NARRATIVE,
            "weather": {
                "conditions": weather.conditions if weather else "Heavy rain",
                "rainfall_mm": weather.rainfall_mm if weather else 48.2,
                "temperature_c": weather.temperature_c if weather else 27.4,
            },
            "risk_zones": [{"id": z.id, "name": z.name, "risk_level": z.risk_level, "risk_score": z.risk_score} for z in zones],
            "flood": {"extent_km2": flood.extent_km2 if flood else 34.5, "water_depth_m": flood.water_depth_m if flood else 1.8},
            "infrastructure": [{"name": i.name, "category": i.category, "status": i.status} for i in infra],
            "roads": [{"name": r.name, "accessibility": r.accessibility} for r in roads],
            "buildings": [{"name": b.name, "damage_class": b.damage_class} for b in buildings],
            "resources": [{"id": r.id, "name": r.name, "type": r.resource_type, "status": r.status} for r in resources],
            "alerts": [{"id": a.id, "title": a.title, "severity": a.severity, "status": getattr(a, "status", "ACTIVE")} for a in alerts],
            "priorities": [{"title": p.title, "level": getattr(p, "level", None), "score": getattr(p, "score", None), "people_affected": p.people_affected} for p in prios],
            "rescue_plan": {"id": plan.id, "decision": plan.decision} if plan else None,
            "audit": [{"action": a.action, "entity_type": a.entity_type, "details": a.details, "created_at": a.created_at.isoformat() if a.created_at else None} for a in audits],
            "timeline": timeline,
            "links": {
                "flood_map": "/flood-detection",
                "damage_report": "/damage-assessment",
                "risk": "/risk-intelligence",
                "rescue": "/rescue-planning",
                "satellite_compare": "/satellite/compare",
                "alerts": "/alerts",
                "analytics": "/analytics",
                "vision": "/computer-vision",
            },
        }
