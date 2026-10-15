from dataclasses import dataclass

from app.services.risk.flood import level_from_score
from app.services.risk.rainfall import _clamp


@dataclass(frozen=True)
class CycloneRiskResult:
    cyclone_risk: float
    severity: str
    affected_region: str
    recommended_action: str
    storm_probability: float
    estimate_label: str = "Prototype AI Risk Estimate"


def evaluate_cyclone(
    wind_speed_ms: float,
    pressure_hpa: float,
    storm_probability: float | None,
    forecast_wind_trend: float | None,
    region: str = "Karnataka / Bengaluru (India)",
) -> CycloneRiskResult:
    """Heuristic 0–100 index from OpenWeather wind/pressure (optional trend). Not an IMD cyclone warning."""
    terms: list[tuple[float, float]] = [
        (0.45, _clamp(wind_speed_ms / 25 * 100)),
        (0.35, _clamp((1015 - pressure_hpa) / 40 * 100)),
    ]
    if storm_probability is not None:
        terms.append((0.25, _clamp(storm_probability * 100)))
    if forecast_wind_trend is not None:
        terms.append((0.15, _clamp(50 + forecast_wind_trend * 20)))
    weight = sum(w for w, _ in terms)
    score = round(sum(w * s for w, s in terms) / weight, 1)
    severity = level_from_score(score)
    action = {
        "critical": "Shelter in cyclone-rated buildings; halt coastal movement.",
        "high": "Secure loose structures; stage medical teams inland.",
        "moderate": "Issue precautionary watch; review boat operations.",
        "low": "Routine monitoring. Score is a heuristic, not an official cyclone warning.",
    }[severity]
    return CycloneRiskResult(
        cyclone_risk=score,
        severity=severity,
        affected_region=region,
        recommended_action=action,
        storm_probability=storm_probability if storm_probability is not None else 0.0,
    )
