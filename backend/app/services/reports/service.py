"""JSON/CSV reports. PDF hook exists but is not implemented."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.demo import DEMO_INCIDENT_ID, DEMO_NARRATIVE, DEMO_REGION
from app.core.operational import SEEDED_DISASTER_IDS, hide_seeded_operations
from app.core.providers import ProviderUnavailableError
from app.models import Alert, DamageReport, Disaster, RescuePlan, RiskZone
from app.services.analytics.service import AnalyticsService, rows_to_csv


class ReportRenderer:
    def to_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload

    def to_csv(self, rows: list[dict[str, Any]]) -> str:
        return rows_to_csv(rows)

    def to_pdf(self, payload: dict[str, Any]) -> bytes | None:  # noqa: ARG002
        return None


def _live_region() -> str:
    from app.services.geo.aoi import get_aoi

    aoi = get_aoi()
    return str(aoi.get("aoi_name") or settings.aoi_name)


class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.renderer = ReportRenderer()

    def generate(self, kind: str, disaster_id: str | None = None) -> dict[str, Any]:
        if hide_seeded_operations():
            return self._generate_live(kind, disaster_id)
        return self._generate_demo(kind, disaster_id)

    def _generate_demo(self, kind: str, disaster_id: str | None) -> dict[str, Any]:
        did = disaster_id or DEMO_INCIDENT_ID
        disaster = self.db.query(Disaster).filter(Disaster.id == did).first()
        analytics = AnalyticsService(self.db).overview()
        stamp = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        if kind == "damage":
            dmg = self.db.query(DamageReport).order_by(DamageReport.created_at.desc()).first()
            body = dmg.report if dmg else {"note": "Run damage assessment to populate statistics."}
            payload: dict[str, Any] = {
                "kind": "Damage Assessment Report",
                "incident_id": did,
                "region": DEMO_REGION,
                "body": body,
            }
        elif kind == "rescue":
            plan = (
                self.db.query(RescuePlan)
                .filter(RescuePlan.disaster_id == did)
                .order_by(RescuePlan.created_at.desc())
                .first()
            )
            payload = {
                "kind": "Rescue Plan",
                "incident_id": did,
                "body": plan.payload if plan else {"note": "Generate a rescue plan first."},
            }
        elif kind == "risk":
            zones = self.db.query(RiskZone).all()
            payload = {
                "kind": "Risk Assessment",
                "incident_id": did,
                "zones": [{"name": z.name, "level": z.risk_level, "score": z.risk_score} for z in zones],
            }
        else:
            payload = {
                "kind": "Incident Summary",
                "incident_id": did,
                "title": disaster.title if disaster else "Kuttanad monsoon inundation (demo)",
                "narrative": DEMO_NARRATIVE,
                "analytics": analytics["kpis"],
                "alert_count": self.db.query(Alert).count(),
            }
        payload["generated_at"] = stamp
        payload["pdf_available"] = False
        payload["disclaimer"] = "VisionGuard AI is a decision-support prototype. Not an official government product."
        payload["data_mode"] = "DEMO DATA"
        return self.renderer.to_json(payload)

    def _generate_live(self, kind: str, disaster_id: str | None) -> dict[str, Any]:
        region = _live_region()
        if disaster_id and (disaster_id == DEMO_INCIDENT_ID or disaster_id in SEEDED_DISASTER_IDS):
            raise ProviderUnavailableError(
                "reports",
                "Live reports cannot use the seeded Kuttanad DEMO_INCIDENT_ID. "
                f"Selected AOI is {region}. Pass a real live incident id or omit it for an AOI-scoped report.",
            )
        disaster = None
        if disaster_id:
            disaster = self.db.query(Disaster).filter(Disaster.id == disaster_id).first()
            if disaster is None or disaster.id in SEEDED_DISASTER_IDS:
                raise ProviderUnavailableError(
                    "reports",
                    f"No live incident '{disaster_id}'. Seeded Kuttanad case files are hidden in REAL DATA mode.",
                )
        analytics = AnalyticsService(self.db).overview()
        stamp = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        live_id = disaster.id if disaster else None

        if kind == "incident" and disaster is None:
            raise ProviderUnavailableError(
                "reports",
                "Live incident report requires a real disaster_id. There is no seeded Karnataka case file. "
                f"Selected AOI: {region}.",
            )
        if kind == "damage":
            rows = [
                r
                for r in self.db.query(DamageReport).order_by(DamageReport.created_at.desc()).all()
                if (r.model_name or "").startswith("sentinel")
            ]
            dmg = rows[0] if rows else None
            payload: dict[str, Any] = {
                "kind": "Damage Assessment Report",
                "incident_id": live_id,
                "region": region,
                "body": dmg.report
                if dmg
                else {
                    "note": "UNAVAILABLE — no live Sentinel damage assessment for this AOI. Demo building counts are not used.",
                },
            }
        elif kind == "rescue":
            payload = {
                "kind": "Rescue Plan",
                "incident_id": live_id,
                "region": region,
                "body": {
                    "note": "UNAVAILABLE — no live rescue inventory or plan. Seeded boats/centers are not used.",
                },
            }
        elif kind == "risk":
            payload = {
                "kind": "Risk Assessment",
                "incident_id": live_id,
                "region": region,
                "zones": [],
                "note": "Seeded Kuttanad risk zones are not included. Live risk is weather-heuristic only.",
            }
        else:
            payload = {
                "kind": "Incident Summary",
                "incident_id": live_id,
                "region": region,
                "title": disaster.title if disaster else None,
                "narrative": [],
                "analytics": analytics["kpis"],
                "alert_count": analytics["kpis"].get("alert_count", 0),
            }
        payload["generated_at"] = stamp
        payload["pdf_available"] = False
        payload["disclaimer"] = (
            "VisionGuard AI is a decision-support prototype. Not an official government product. "
            f"AOI: {region}."
        )
        payload["data_mode"] = "REAL DATA"
        return self.renderer.to_json(payload)
