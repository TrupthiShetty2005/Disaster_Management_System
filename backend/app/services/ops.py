from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.operational import hide_seeded_operations
from app.repositories.ops import (
    AlertRepository,
    DisasterRepository,
    EvacuationRepository,
    ResourceRepository,
    RiskZoneRepository,
)
from app.schemas.common import FactorOut
from app.services.risk.flood import BaselineFloodRiskModel, FloodRiskInput, overlay_demo_flood
from app.services.weather_intel import ZONE_PROFILES, WeatherIntelService


class DisasterService:
    def __init__(self, db: Session):
        self.repo = DisasterRepository(db)

    def list(self, phase: str | None = None):
        if hide_seeded_operations():
            return [], 0
        items = self.repo.list(phase)
        return items, len(items)

    def get(self, disaster_id: str):
        if hide_seeded_operations():
            raise HTTPException(
                status_code=404,
                detail="No live disaster incident feed. Seeded demo records are hidden in REAL DATA mode.",
            )
        item = self.repo.get(disaster_id)
        if not item:
            raise HTTPException(status_code=404, detail="Disaster not found")
        return item


class RiskService:
    def __init__(self, db: Session):
        self.repo = RiskZoneRepository(db)
        self.intel = WeatherIntelService(db)

    def list(self):
        if hide_seeded_operations():
            return [], 0
        items = self.repo.list()
        return items, len(items)

    def get(self, zone_id: str):
        if hide_seeded_operations():
            raise HTTPException(
                status_code=404,
                detail="No live risk-zone catalog. Seeded demo zones are hidden in REAL DATA mode.",
            )
        item = self.repo.get(zone_id)
        if not item:
            raise HTTPException(status_code=404, detail="Risk zone not found")
        return item

    def explain(self, zone) -> dict:
        profile = ZONE_PROFILES.get(
            zone.name, {"population": 0, "historical": 0.4, "elevation": 6.0, "soil": 0.5}
        )
        snap = self.intel.current(zone.location_id)
        rain = self.intel.rainfall(zone.location_id)
        result = BaselineFloodRiskModel().evaluate(
            FloodRiskInput(
                rainfall_mm=snap.rainfall_mm,
                rainfall_intensity=rain.intensity_mm_h,
                river_level_m=snap.river_level_m,
                historical_flood_frequency=profile["historical"],
                terrain_elevation_m=profile["elevation"],
                soil_saturation=profile["soil"],
            )
        )
        if settings.use_mock_providers and "Polder" in zone.name:
            result = overlay_demo_flood(result)
        elif not settings.use_mock_providers:
            result = result.__class__(
                flood_probability=result.flood_probability,
                risk_score=result.risk_score,
                risk_level=result.risk_level,
                factors=result.factors,
                recommended_action=result.recommended_action,
                estimate_label="RULE-BASED zone risk from live weather inputs (not an official warning)",
            )
        return {
            "affected_population": profile["population"],
            "flood_probability": result.flood_probability,
            "contributing_factors": [FactorOut(**f) for f in result.factors],
            "recommended_action": result.recommended_action,
            "estimate_label": result.estimate_label,
            "risk_level": result.risk_level,
            "risk_score": result.risk_score,
        }


class WeatherService:
    def __init__(self, db: Session):
        self.intel = WeatherIntelService(db)

    def current(self, location_id: str | None):
        return self.intel.current(location_id)

    def forecast(self, location_id: str | None):
        items = self.intel.forecast(location_id)
        live = bool(items) and items[0].source == "openweather" and not settings.use_mock_providers
        return items, len(items), live


class AlertService:
    def __init__(self, db: Session):
        self.repo = AlertRepository(db)

    def list(self):
        items = self.repo.list()
        if hide_seeded_operations():
            from app.core.operational import is_seeded_alert

            items = [a for a in items if not is_seeded_alert(a)]
        return items, len(items)


class ResourceService:
    def __init__(self, db: Session):
        self.repo = ResourceRepository(db)

    def list(self):
        if hide_seeded_operations():
            return [], 0
        items = self.repo.list()
        return items, len(items)


class EvacuationService:
    def __init__(self, db: Session):
        self.repo = EvacuationRepository(db)

    def list(self):
        if hide_seeded_operations():
            return [], 0
        items = self.repo.list()
        return items, len(items)
