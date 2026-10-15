from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.operational import hide_seeded_operations
from app.core.providers import ProviderUnavailableError
from app.db.seed import DIS_FLOOD, LOC_KUTTANAD
from app.models import AuditLog, Disaster, EvacuationCenter, RescuePlan, RescuePriority, RescueResource
from app.services.rescue.priority import PriorityInput, RescuePriorityService
from app.services.rescue.recommend import recommend_resources
from app.services.rescue.routing import NODES, plan_routes

TYPE_MAP = {
    "rescue_boat": "RESCUE_BOAT",
    "ambulance": "AMBULANCE",
    "medical_team": "MEDICAL_TEAM",
    "food_unit": "FOOD_UNIT",
    "rescue_team": "RESCUE_TEAM",
    "helicopter": "HELICOPTER",
    "water_tanker": "WATER_TANKER",
}

STATUS_MAP = {
    "available": "AVAILABLE",
    "staging": "AVAILABLE",
    "deployed": "DEPLOYED",
    "busy": "BUSY",
    "maintenance": "MAINTENANCE",
}


def normalize_type(raw: str) -> str:
    key = raw.lower().replace(" ", "_")
    return TYPE_MAP.get(key, raw.upper())


def normalize_status(raw: str) -> str:
    return STATUS_MAP.get(raw.lower(), raw.upper() if raw else "AVAILABLE")


def coords_of(row: RescueResource) -> tuple[float, float]:
    geo = row.geojson or {}
    if geo.get("type") == "Point":
        lon, lat = geo["coordinates"]
        return float(lat), float(lon)
    return (
        float(getattr(row, "latitude", None) or settings.demo_latitude),
        float(getattr(row, "longitude", None) or settings.demo_longitude),
    )


class RescuePlanningService:
    def __init__(self, db: Session):
        self.db = db
        self.priority = RescuePriorityService()

    def ensure_catalog(self) -> None:
        if hide_seeded_operations():
            return
        extra = [
            ("Food unit 3 (demo)", "FOOD_UNIT", "AVAILABLE", 4, 76.532, 9.506),
            ("Rescue team Bravo (demo)", "RESCUE_TEAM", "AVAILABLE", 10, 76.528, 9.512),
            ("Helicopter H1 (demo)", "HELICOPTER", "MAINTENANCE", 6, 76.545, 9.500),
            ("Water tanker 7 (demo)", "WATER_TANKER", "AVAILABLE", 2, 76.518, 9.509),
        ]
        names = {r.name for r in self.db.query(RescueResource).all()}
        for name, typ, status, cap, lon, lat in extra:
            if name in names:
                continue
            self.db.add(
                RescueResource(
                    name=name,
                    resource_type=typ,
                    status=status,
                    personnel=cap,
                    capacity=cap,
                    latitude=lat,
                    longitude=lon,
                    location_id=LOC_KUTTANAD,
                    geojson={"type": "Point", "coordinates": [lon, lat]},
                )
            )
        self.db.commit()
        for row in self.db.query(RescueResource).all():
            geo = row.geojson or {}
            if geo.get("type") == "Point":
                row.longitude = float(geo["coordinates"][0])
                row.latitude = float(geo["coordinates"][1])
            if not getattr(row, "capacity", 0):
                row.capacity = row.personnel
            row.resource_type = normalize_type(row.resource_type)
            row.status = normalize_status(row.status)
        self.db.commit()

    def list_resources(self) -> list[RescueResource]:
        if hide_seeded_operations():
            return []
        self.ensure_catalog()
        return self.db.query(RescueResource).all()

    def refresh_priorities(self) -> list[RescuePriority]:
        if hide_seeded_operations():
            return []
        rows = self.db.query(RescuePriority).all()
        if not rows:
            return rows
        for row in rows:
            disaster = self.db.query(Disaster).filter(Disaster.id == row.disaster_id).first()
            risk = (disaster.severity if disaster else "high") or "high"
            inp = PriorityInput(
                population_affected=row.people_affected,
                risk_level=risk,
                people_stranded=max(80, int(row.people_affected * 0.18)),
                infrastructure_damage=0.45 if risk in {"high", "severe", "critical"} else 0.2,
                road_accessibility="blocked",
                flood_severity="high" if disaster and disaster.disaster_type == "flood" else "moderate",
                distance_to_resources_km=2.4,
                medical_urgency=0.55,
            )
            result = self.priority.evaluate(inp)
            row.score = result["score"]
            row.level = result["level"]
            row.factors = result["factors"]
        self.db.commit()
        return self.db.query(RescuePriority).order_by(RescuePriority.score.desc()).all()

    def allocate(self, resource_id: str, incident_id: str) -> RescueResource:
        row = self.db.query(RescueResource).filter(RescueResource.id == resource_id).first()
        if not row:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Resource not found")
        row.assigned_incident = incident_id
        row.status = "DEPLOYED"
        row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.db.add(
            AuditLog(
                action="resource_allocate",
                entity_type="rescue_resource",
                entity_id=row.id,
                details=f"Assigned to incident {incident_id}",
            )
        )
        self.db.commit()
        self.db.refresh(row)
        return row

    def generate_plan(self, disaster_id: str | None = None) -> RescuePlan:
        if hide_seeded_operations():
            raise ProviderUnavailableError(
                "rescue",
                "No live rescue inventory API. Seeded boats/centers are disabled in REAL DATA mode.",
            )
        self.ensure_catalog()
        disaster_id = disaster_id or DIS_FLOOD
        disaster = self.db.query(Disaster).filter(Disaster.id == disaster_id).first()
        if not disaster:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Disaster not found")
        prios = self.refresh_priorities()
        prio = next((p for p in prios if p.disaster_id == disaster_id), prios[0] if prios else None)
        centers = self.db.query(EvacuationCenter).filter(EvacuationCenter.location_id == disaster.location_id).all()
        occ = 0.0
        if centers:
            cap = sum(c.capacity for c in centers) or 1
            occ = sum(c.occupied for c in centers) / cap
        flood = "high" if disaster.disaster_type == "flood" else "moderate"
        rec = recommend_resources(
            flood_severity=flood,
            population_affected=disaster.people_at_risk,
            medical_urgency=0.6,
            road_accessibility="blocked",
            shelter_occupancy=occ,
            people_stranded=int((prio.people_affected if prio else disaster.people_at_risk) * 0.18),
        )
        inventory = self.list_resources()
        available = [r for r in inventory if normalize_status(r.status) == "AVAILABLE"]
        allocation = []
        remaining = {item["type"]: item["count"] for item in rec["required"]}
        for row in available:
            typ = normalize_type(row.resource_type)
            if remaining.get(typ, 0) > 0:
                allocation.append(
                    {
                        "resource_id": row.id,
                        "name": row.name,
                        "type": typ,
                        "action": "recommend_deploy",
                    }
                )
                remaining[typ] -= 1
        routes = plan_routes()
        payload = {
            "incident": {
                "id": disaster.id,
                "title": disaster.title,
                "type": disaster.disaster_type,
                "severity": disaster.severity,
            },
            "priority": {
                "id": prio.id if prio else None,
                "title": prio.title if prio else disaster.title,
                "score": prio.score if prio else None,
                "level": prio.level if prio else None,
            },
            "affected_population": disaster.people_at_risk,
            "required_resources": rec["required"],
            "available_resources": [
                {"id": r.id, "name": r.name, "type": normalize_type(r.resource_type), "status": normalize_status(r.status)}
                for r in inventory
            ],
            "recommended_allocation": allocation,
            "unmet_need": {k: v for k, v in remaining.items() if v > 0},
            "evacuation_route": routes["evacuation"],
            "routes": routes,
            "estimated_response_time": routes["estimated_response_time_min"],
            "warnings": rec["warnings"],
            "reasoning": rec["reasoning"],
            "estimate_label": rec["estimate_label"],
            "map": {
                "incident": {"type": "Point", "coordinates": list(NODES["incident"])},
                "hospital": {"type": "Point", "coordinates": list(NODES["hospital"])},
                "shelter": {"type": "Point", "coordinates": list(NODES["shelter"])},
            },
        }
        plan = RescuePlan(
            disaster_id=disaster.id,
            priority_id=prio.id if prio else None,
            decision="PENDING",
            payload=payload,
        )
        self.db.add(plan)
        self.db.flush()
        self.db.add(
            AuditLog(
                action="rescue_plan_generated",
                entity_type="rescue_plan",
                entity_id=plan.id,
                details="Prototype plan created",
            )
        )
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def get_plan(self, plan_id: str) -> RescuePlan | None:
        return self.db.query(RescuePlan).filter(RescuePlan.id == plan_id).first()

    def decide(self, plan_id: str, action: str, notes: str = "") -> RescuePlan:
        from fastapi import HTTPException

        plan = self.get_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Rescue plan not found")
        act = action.lower()
        if act not in {"accept", "modify", "reject"}:
            raise HTTPException(status_code=400, detail="Action must be accept, modify, or reject")
        plan.decision = {"accept": "ACCEPTED", "modify": "MODIFIED", "reject": "REJECTED"}[act]
        plan.override_notes = notes
        self.db.add(plan)
        self.db.flush()
        if act == "accept":
            for item in (plan.payload or {}).get("recommended_allocation", []):
                rid = item.get("resource_id")
                if rid:
                    self.allocate(rid, plan.disaster_id)
        self.db.add(
            AuditLog(
                action=f"rescue_plan_{act}",
                entity_type="rescue_plan",
                entity_id=plan.id,
                details=notes or act,
            )
        )
        self.db.commit()
        self.db.refresh(plan)
        return plan
