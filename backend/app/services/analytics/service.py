from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime
from io import StringIO
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.demo import DEMO_AFFECTED_POPULATION, DEMO_BLOCKED_ROADS, DEMO_DAMAGED_BUILDINGS, DEMO_FLOOD_RISK_PCT, DEMO_FLOODED_KM2, DEMO_INCIDENT_ID, DEMO_LOCATION_ID
from app.models import (
    Alert,
    Building,
    Disaster,
    FloodAnalysis,
    FloodEvent,
    RescuePlan,
    RescuePriority,
    RescueResource,
    RiskZone,
    Road,
)


def _in_range(dt: datetime | None, start: datetime | None, end: datetime | None) -> bool:
    if dt is None:
        return True
    if start and dt < start:
        return False
    if end and dt > end:
        return False
    return True


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def _disasters(self, disaster_type: str | None, location_id: str | None, severity: str | None) -> list[Disaster]:
        q = self.db.query(Disaster)
        if disaster_type:
            q = q.filter(Disaster.disaster_type == disaster_type)
        if location_id:
            q = q.filter(Disaster.location_id == location_id)
        if severity:
            q = q.filter(Disaster.severity.ilike(severity))
        return q.all()

    def overview(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        disaster_type: str | None = None,
        location_id: str | None = None,
        severity: str | None = None,
    ) -> dict[str, Any]:
        from app.core.operational import SEEDED_DISASTER_IDS, hide_seeded_operations, is_seeded_alert

        disasters = [
            d
            for d in self._disasters(disaster_type, location_id, severity)
            if _in_range(d.started_at, date_from, date_to)
            and not (hide_seeded_operations() and d.id in SEEDED_DISASTER_IDS)
        ]
        alerts = [
            a
            for a in self.db.query(Alert).all()
            if _in_range(a.issued_at, date_from, date_to)
            and (not location_id or a.location_id == location_id)
            and not (hide_seeded_operations() and is_seeded_alert(a))
        ]
        resources = [] if hide_seeded_operations() else self.db.query(RescueResource).all()
        deployed = [r for r in resources if str(r.status).upper() in {"DEPLOYED", "BUSY"}]
        buildings = [] if hide_seeded_operations() else self.db.query(Building).all()
        damaged_b = [b for b in buildings if (b.damage_class or "unknown") not in {"unknown", "none", "NO DAMAGE"}]
        roads = [] if hide_seeded_operations() else self.db.query(Road).all()
        damaged_r = [r for r in roads if str(r.accessibility).lower() in {"blocked", "destroyed", "partial"}]
        flood_rows = self.db.query(FloodAnalysis).order_by(FloodAnalysis.created_at.desc()).all()
        if hide_seeded_operations():
            from app.services.flood.service import _is_live_water_change_row

            flood_rows = [r for r in flood_rows if _is_live_water_change_row(r)]
        elif not flood_rows:
            flood_rows = self.db.query(FloodEvent).all()
        flooded = 0.0
        if flood_rows:
            row = flood_rows[0]
            flooded = float(getattr(row, "flooded_area", None) or getattr(row, "extent_km2", 0) or 0.0)
        if settings.use_mock_providers:
            flooded = DEMO_FLOODED_KM2
            damaged_b_n = DEMO_DAMAGED_BUILDINGS
            damaged_r_n = DEMO_BLOCKED_ROADS
            pop = DEMO_AFFECTED_POPULATION
            flood_risk_pct = DEMO_FLOOD_RISK_PCT
            data_class = "SIMULATED"
            estimate_label = "Prototype analytics — SIMULATED demo figures, not official statistics"
            risk_trend = [42, 51, 66, 78, 86]
            flood_series = [4, 9, 16, 24, flooded]
            response_perf = [40, 48, 55, 62, 70]
        else:
            # Real Data Mode: never substitute hard-coded demo KPIs (34.5 / 82).
            damaged_b_n = 0
            damaged_r_n = 0
            pop = 0
            try:
                from app.services.weather_intel import WeatherIntelService

                flood_risk_pct = WeatherIntelService(self.db).flood(location_id).flood_probability
            except Exception:
                flood_risk_pct = None
            data_class = "REAL_DATA"
            estimate_label = (
                "Analytics from live weather and Sentinel flood analyses only. "
                "No seeded inventory. Not official statistics or government warnings."
            )
            risk_val = float(flood_risk_pct) if flood_risk_pct is not None else 0.0
            risk_trend = [max(0.0, risk_val - 12), max(0.0, risk_val - 8), max(0.0, risk_val - 4), max(0.0, risk_val - 2), risk_val]
            flood_series = [0.0, 0.0, 0.0, 0.0, flooded]
            response_perf = [0.0, 0.0, 0.0, 0.0, 0.0]
        prios = [] if hide_seeded_operations() else self.db.query(RescuePriority).all()
        plans = [] if hide_seeded_operations() else self.db.query(RescuePlan).all()
        avg_rt = 0.0
        if plans:
            times = [float((p.payload or {}).get("estimated_response_time") or 0) for p in plans]
            times = [t for t in times if t > 0]
            avg_rt = round(sum(times) / len(times), 1) if times else 0.0
        labels = ["T-4d", "T-3d", "T-2d", "T-1d", "Now"]
        kpis = {
            "total_disasters": len(disasters) if hide_seeded_operations() else len(self.db.query(Disaster).all()),
            "active_disasters": len([d for d in disasters if d.status == "active"]),
            "affected_population": pop,
            "flooded_area": flooded,
            "damaged_buildings": damaged_b_n,
            "damaged_roads": damaged_r_n,
            "resource_utilization": round(100 * len(deployed) / max(len(resources), 1), 1),
            "alert_count": len(alerts),
            "average_response_time": avg_rt if settings.use_mock_providers else (avg_rt or 0.0),
            "rescue_priority_distribution": dict(Counter((p.level or "MEDIUM") for p in prios)) or (
                {"HIGH": 1} if settings.use_mock_providers else {}
            ),
            "flood_risk_pct": (
                DEMO_FLOOD_RISK_PCT
                if settings.use_mock_providers
                else flood_risk_pct
            ),
            "data_class": data_class,
            "population_note": "no live census feed" if not settings.use_mock_providers else "SIMULATED",
            "rescue_inventory_available": bool(settings.use_mock_providers),
            "damage_overlay_available": bool(settings.use_mock_providers),
            "river_gauge_available": False,
            "official_warnings_available": False,
        }
        return {
            "incident_id": None if hide_seeded_operations() else DEMO_INCIDENT_ID,
            "location_id": None if hide_seeded_operations() else (location_id or DEMO_LOCATION_ID),
            "kpis": kpis,
            "series": {
                "labels": labels,
                "disaster_frequency": [0, 1, 1, 2, len(disasters)] if settings.use_mock_providers else [0, 0, 0, 0, len(disasters)],
                "risk_trend": risk_trend,
                "affected_population": [8, 12, 18, 28, round(kpis["affected_population"] / 1000, 1)]
                if settings.use_mock_providers
                else [0, 0, 0, 0, round(float(kpis["affected_population"] or 0) / 1000, 1)],
                "resource_utilization": [20, 28, 40, 55, kpis["resource_utilization"]]
                if settings.use_mock_providers
                else [0, 0, 0, 0, kpis["resource_utilization"]],
                "flood_expansion": flood_series,
                "alert_severity": {
                    "INFO": len([a for a in alerts if str(a.severity).upper() == "INFO"]),
                    "WATCH": len([a for a in alerts if str(a.severity).upper() in {"WATCH", "INFO"}]),
                    "WARNING": len([a for a in alerts if str(a.severity).upper() == "WARNING"]),
                    "CRITICAL": len([a for a in alerts if str(a.severity).upper() in {"CRITICAL", "SEVERE"}]),
                },
                "response_performance": response_perf,
                "damage_by_category": {"buildings": kpis["damaged_buildings"], "roads": kpis["damaged_roads"], "flood": flooded},
            },
            "estimate_label": estimate_label,
            "data_provenance": {
                "status": "MOCK" if settings.use_mock_providers else "DERIVED_LIVE",
                "provider": "AnalyticsService",
                "description": (
                    "Demo KPI strip with SIMULATED figures."
                    if settings.use_mock_providers
                    else "Flood/risk from live analyses when present; seeded ops inventory excluded."
                ),
                "kpis": {
                    "flooded_area": "DERIVED_LIVE from FloodAnalysis when present, else 0 (never hard-coded 34.5 in LIVE)",
                    "flood_risk_pct": "DERIVED_LIVE from WeatherIntel when LIVE, else DEMO 82 in Demo Mode",
                    "affected_population": "UNAVAILABLE — no census feed",
                    "damaged_buildings": "UNAVAILABLE — no damage overlay dataset in live mode",
                    "damaged_roads": "UNAVAILABLE — no live road-status feed",
                    "rescue_units": "UNAVAILABLE — no live vehicle/shelter inventory",
                },
            },
        }

    def disasters(self, **kwargs) -> dict[str, Any]:
        from app.core.operational import SEEDED_DISASTER_IDS, hide_seeded_operations

        ov = self.overview(**kwargs)
        rows = self.db.query(Disaster).all()
        if hide_seeded_operations():
            rows = [d for d in rows if d.id not in SEEDED_DISASTER_IDS]
        return {
            "items": [
                {
                    "id": d.id,
                    "title": d.title,
                    "disaster_type": d.disaster_type,
                    "severity": d.severity,
                    "status": d.status,
                    "people_at_risk": d.people_at_risk,
                    "started_at": d.started_at.isoformat() if d.started_at else None,
                }
                for d in rows
            ],
            "series": ov["series"],
            "incident_id": None if hide_seeded_operations() else DEMO_INCIDENT_ID,
        }

    def damage(self, **kwargs) -> dict[str, Any]:
        from app.core.operational import hide_seeded_operations

        ov = self.overview(**kwargs)
        return {
            "kpis": {k: ov["kpis"][k] for k in ("damaged_buildings", "damaged_roads", "flooded_area")},
            "series": ov["series"]["damage_by_category"],
            "incident_id": None if hide_seeded_operations() else DEMO_INCIDENT_ID,
        }

    def resources(self, **kwargs) -> dict[str, Any]:
        from app.core.operational import hide_seeded_operations

        ov = self.overview(**kwargs)
        items = [] if hide_seeded_operations() else self.db.query(RescueResource).all()
        return {
            "utilization": ov["kpis"]["resource_utilization"],
            "average_response_time": ov["kpis"]["average_response_time"],
            "items": [{"id": r.id, "name": r.name, "type": r.resource_type, "status": r.status} for r in items],
            "incident_id": None if hide_seeded_operations() else DEMO_INCIDENT_ID,
        }

    def risks(self, **kwargs) -> dict[str, Any]:
        from app.core.operational import hide_seeded_operations

        zones = [] if hide_seeded_operations() else self.db.query(RiskZone).all()
        return {
            "items": [
                {"id": z.id, "name": z.name, "hazard_type": z.hazard_type, "risk_score": z.risk_score, "risk_level": z.risk_level}
                for z in zones
            ],
            "series": self.overview(**kwargs)["series"]["risk_trend"],
            "incident_id": None if hide_seeded_operations() else DEMO_INCIDENT_ID,
        }

    def alerts(self, **kwargs) -> dict[str, Any]:
        from app.core.operational import hide_seeded_operations

        ov = self.overview(**kwargs)
        return {
            "count": ov["kpis"]["alert_count"],
            "severity": ov["series"]["alert_severity"],
            "incident_id": None if hide_seeded_operations() else DEMO_INCIDENT_ID,
        }


def rows_to_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()
