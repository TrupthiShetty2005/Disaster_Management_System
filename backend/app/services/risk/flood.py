"""Replaceable flood score. Outputs are labeled prototype estimates, not calibrated probabilities.

Live formula (only terms with real inputs, then renormalized):
  rain_s = clamp(rainfall_mm / 60 * 100)
  intensity_s = clamp(intensity_mm_h / 3 * 100)
  river_s = clamp((river_m - 1) / 3.5 * 100)   # omitted when no gauge
  hist_s / terrain_s / soil_s — omitted in live mode (no dataset)
  score = weighted mean of available terms
This is a heuristic 0–100 index, not a scientifically established flood probability.
"""

from dataclasses import dataclass
from typing import Protocol

from app.services.risk.rainfall import _clamp


def level_from_score(score: float) -> str:
    if score >= 76:
        return "critical"
    if score >= 51:
        return "high"
    if score >= 26:
        return "moderate"
    return "low"


def factor_level(score: float) -> str:
    if score >= 70:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


@dataclass(frozen=True)
class FloodRiskInput:
    rainfall_mm: float | None = None
    rainfall_intensity: float | None = None
    river_level_m: float | None = None
    historical_flood_frequency: float | None = None  # 0–1
    terrain_elevation_m: float | None = None
    soil_saturation: float | None = None


@dataclass(frozen=True)
class FloodRiskResult:
    flood_probability: float
    risk_score: float
    risk_level: str
    factors: list[dict]
    recommended_action: str
    estimate_label: str = "Prototype AI Risk Estimate"


class FloodRiskModel(Protocol):
    def evaluate(self, data: FloodRiskInput) -> FloodRiskResult: ...


class BaselineFloodRiskModel:
    """Transparent weighted heuristic. Swap for a trained model later."""

    def evaluate(self, data: FloodRiskInput) -> FloodRiskResult:
        terms: list[tuple[str, float, float]] = []
        if data.rainfall_mm is not None:
            terms.append(("Rainfall", 0.25, _clamp(data.rainfall_mm / 60 * 100)))
        if data.rainfall_intensity is not None:
            terms.append(("Rainfall intensity", 0.20, _clamp(data.rainfall_intensity / 3 * 100)))
        if data.river_level_m is not None:
            terms.append(("River level", 0.20, _clamp((data.river_level_m - 1.0) / 3.5 * 100)))
        if data.historical_flood_frequency is not None:
            terms.append(("Historical flood frequency", 0.15, _clamp(data.historical_flood_frequency * 100)))
        if data.terrain_elevation_m is not None:
            terms.append(("Terrain / elevation", 0.10, _clamp((12 - data.terrain_elevation_m) / 12 * 100)))
        if data.soil_saturation is not None:
            terms.append(("Soil saturation", 0.10, _clamp(data.soil_saturation * 100)))
        if not terms:
            raise ValueError("No flood-score inputs available.")
        weight_sum = sum(w for _, w, _ in terms)
        probability = round(sum(w * s for _, w, s in terms) / weight_sum, 1)
        level = level_from_score(probability)
        action = {
            "critical": "Evacuate remaining low-lying households; boat last-mile only.",
            "high": "Pre-stage boats and open overflow shelters.",
            "moderate": "Hold in place; keep high-ground access open.",
            "low": "Monitor rainfall watch. No movement required.",
        }[level]
        used = {name for name, _, _ in terms}
        catalog = [
            "Rainfall",
            "Rainfall intensity",
            "River level",
            "Historical flood frequency",
            "Terrain / elevation",
            "Soil saturation",
        ]
        factors = []
        by_name = {n: (w, s) for n, w, s in terms}
        for name in catalog:
            if name in by_name:
                _, score = by_name[name]
                factors.append({"name": name, "level": factor_level(score), "value": round(score, 1)})
            else:
                factors.append({"name": f"{name} (unavailable)", "level": "n/a", "value": 0})
        return FloodRiskResult(
            flood_probability=probability,
            risk_score=probability,
            risk_level=level,
            factors=factors,
            recommended_action=action,
            estimate_label=(
                "RULE-BASED index from available weather inputs only — not a scientifically "
                f"established probability. Terms used: {', '.join(sorted(used))}."
            ),
        )


def overlay_demo_flood(result: FloodRiskResult) -> FloodRiskResult:
    """Canonical demo scenario figures — labeled SIMULATED, not live observations."""
    from app.core.config import settings
    from app.core.demo import DEMO_FLOOD_FACTORS, DEMO_FLOOD_RISK_PCT

    if not settings.use_mock_providers:
        return result
    return FloodRiskResult(
        flood_probability=DEMO_FLOOD_RISK_PCT,
        risk_score=DEMO_FLOOD_RISK_PCT,
        risk_level=level_from_score(DEMO_FLOOD_RISK_PCT),
        factors=list(DEMO_FLOOD_FACTORS),
        recommended_action=result.recommended_action,
        estimate_label="SIMULATED DATA · Prototype AI Risk Estimate",
    )
