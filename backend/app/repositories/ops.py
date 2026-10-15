from sqlalchemy.orm import Session

from app.models import (
    Alert,
    Disaster,
    EvacuationCenter,
    RescueResource,
    RiskZone,
    WeatherForecast,
    WeatherObservation,
)


class DisasterRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, phase: str | None = None) -> list[Disaster]:
        q = self.db.query(Disaster)
        if phase:
            q = q.filter(Disaster.phase == phase)
        return q.order_by(Disaster.started_at.desc()).all()

    def get(self, disaster_id: str) -> Disaster | None:
        return self.db.query(Disaster).filter(Disaster.id == disaster_id).first()


class RiskZoneRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, zone_id: str) -> RiskZone | None:
        return self.db.query(RiskZone).filter(RiskZone.id == zone_id).first()

    def list(self) -> list[RiskZone]:
        return self.db.query(RiskZone).order_by(RiskZone.risk_score.desc()).all()


class WeatherRepository:
    def __init__(self, db: Session):
        self.db = db

    def latest_observation(self, location_id: str | None) -> WeatherObservation | None:
        q = self.db.query(WeatherObservation)
        if location_id:
            q = q.filter(WeatherObservation.location_id == location_id)
        return q.order_by(WeatherObservation.observed_at.desc()).first()

    def forecasts(self, location_id: str | None) -> list[WeatherForecast]:
        q = self.db.query(WeatherForecast)
        if location_id:
            q = q.filter(WeatherForecast.location_id == location_id)
        return q.order_by(WeatherForecast.period_start.asc()).all()


class AlertRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list[Alert]:
        return self.db.query(Alert).order_by(Alert.issued_at.desc()).all()


class ResourceRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list[RescueResource]:
        return self.db.query(RescueResource).all()


class EvacuationRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list[EvacuationCenter]:
        return self.db.query(EvacuationCenter).all()
