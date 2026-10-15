from __future__ import annotations

from dataclasses import dataclass


RISK_WEIGHT = {"low": 15, "medium": 35, "moderate": 35, "high": 65, "critical": 90, "severe": 85}
FLOOD_WEIGHT = {"low": 10, "moderate": 35, "medium": 35, "high": 70, "critical": 90}
ROAD_WEIGHT = {"open": 5, "partial": 40, "partially_blocked": 40, "blocked": 85, "destroyed": 95}


@dataclass
class PriorityInput:
    population_affected: int
    risk_level: str
    people_stranded: int
    infrastructure_damage: float
    road_accessibility: str
    flood_severity: str
    distance_to_resources_km: float
    medical_urgency: float


def band(score: float) -> str:
    if score < 35:
        return "LOW"
    if score < 55:
        return "MEDIUM"
    if score < 80:
        return "HIGH"
    return "CRITICAL"


class RescuePriorityService:
    """Transparent 0–100 score. Prototype decision support, not an optimizer."""

    def evaluate(self, inp: PriorityInput) -> dict:
        pop = min(30.0, inp.population_affected / 800.0)
        stranded = min(15.0, inp.people_stranded / 200.0)
        risk = RISK_WEIGHT.get(inp.risk_level.lower(), 40) * 0.18
        infra = min(1.0, max(0.0, inp.infrastructure_damage)) * 10
        road = ROAD_WEIGHT.get(inp.road_accessibility.lower(), 40) * 0.12
        flood = FLOOD_WEIGHT.get(inp.flood_severity.lower(), 40) * 0.15
        dist = min(8.0, inp.distance_to_resources_km * 0.8)
        medical = min(1.0, max(0.0, inp.medical_urgency)) * 12
        score = round(min(100.0, pop + stranded + risk + infra + road + flood + dist + medical), 1)
        factors = {
            "population_affected": round(pop, 2),
            "people_stranded": round(stranded, 2),
            "risk_level": round(risk, 2),
            "infrastructure_damage": round(infra, 2),
            "road_accessibility": round(road, 2),
            "flood_severity": round(flood, 2),
            "distance_to_resources": round(dist, 2),
            "medical_urgency": round(medical, 2),
        }
        return {
            "score": score,
            "level": band(score),
            "factors": factors,
            "estimate_label": "Prototype rescue priority (not guaranteed optimal)",
        }
