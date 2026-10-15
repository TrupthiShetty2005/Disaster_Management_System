from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Alert, AuditLog
from app.services.alerts.engine import AlertEngine
from app.services.alerts.stream import publish


class EarlyWarningService:
    def __init__(self, db: Session):
        self.db = db
        self.engine = AlertEngine()

    def list(
        self,
        *,
        severity: str | None = None,
        location_id: str | None = None,
        status: str | None = None,
        disaster_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[Alert]:
        q = self.db.query(Alert)
        if severity:
            q = q.filter(Alert.severity.ilike(severity))
        if location_id:
            q = q.filter(Alert.location_id == location_id)
        if status:
            q = q.filter(Alert.status.ilike(status))
        if disaster_type:
            q = q.filter((Alert.alert_type.ilike(disaster_type)) | (Alert.category.ilike(disaster_type)))
        if date_from:
            q = q.filter(Alert.issued_at >= date_from)
        if date_to:
            q = q.filter(Alert.issued_at <= date_to)
        items = q.order_by(Alert.issued_at.desc()).all()
        from app.core.operational import hide_seeded_operations, is_seeded_alert

        if hide_seeded_operations():
            items = [a for a in items if not is_seeded_alert(a)]
        return items

    def get(self, alert_id: str) -> Alert:
        row = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Alert not found")
        from app.core.operational import hide_seeded_operations, is_demo_or_simulated_alert

        if hide_seeded_operations() and is_demo_or_simulated_alert(row):
            raise HTTPException(status_code=404, detail="Alert not found")
        return row

    def generate(self, location_id: str | None = None) -> list[Alert]:
        return self.engine.generate(self.db, location_id)

    def acknowledge(self, alert_id: str, actor: str = "ops.demo") -> Alert:
        row = self.get(alert_id)
        row.acknowledged_at = datetime.now(timezone.utc).replace(tzinfo=None)
        row.acknowledged_by = actor
        if row.status == "ACTIVE":
            row.status = "ACKNOWLEDGED"
        self._audit("alert_acknowledge", row.id, actor)
        self.db.commit()
        self.db.refresh(row)
        publish({"type": "alert.acknowledged", "id": row.id, "status": row.status})
        return row

    def resolve(self, alert_id: str, actor: str = "ops.demo") -> Alert:
        row = self.get(alert_id)
        row.status = "RESOLVED"
        if not row.acknowledged_at:
            row.acknowledged_at = datetime.now(timezone.utc).replace(tzinfo=None)
            row.acknowledged_by = actor
        self._audit("alert_resolve", row.id, actor)
        self.db.commit()
        self.db.refresh(row)
        publish({"type": "alert.resolved", "id": row.id, "status": row.status})
        return row

    def _audit(self, action: str, entity_id: str, actor: str) -> None:
        self.db.add(
            AuditLog(
                action=action,
                entity_type="alert",
                entity_id=entity_id,
                details=actor,
            )
        )
