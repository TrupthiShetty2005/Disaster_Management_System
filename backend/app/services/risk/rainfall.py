"""Rainfall diagnostics. Scores are 0–100 and are not a calibrated meteorological product."""

from dataclasses import dataclass


def _clamp(value: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, value))


@dataclass(frozen=True)
class RainfallAnalysis:
    cumulative_mm: float
    intensity_mm_h: float
    anomaly: float
    short_term_risk: float
    label: str = "Prototype rainfall analysis"


def analyze_rainfall(
    daily_mm: list[float | None],
    hours_in_latest: float = 24.0,
    climatology_mm: float | None = None,
) -> RainfallAnalysis:
    values = [float(v) for v in daily_mm if v is not None]
    if not values:
        return RainfallAnalysis(0, 0, 0, 0)
    cumulative = sum(values)
    latest = values[-1]
    intensity = latest / max(hours_in_latest, 1.0)
    if climatology_mm is None:
        climatology_mm = (sum(values[:-1]) / max(len(values) - 1, 1)) if len(values) >= 2 else latest
    anomaly = (latest - climatology_mm) / max(climatology_mm, 1.0)
    short_term = _clamp(latest * 1.2 + intensity * 40 + max(0, anomaly) * 25)
    return RainfallAnalysis(
        cumulative_mm=round(cumulative, 1),
        intensity_mm_h=round(intensity, 3),
        anomaly=round(anomaly, 3),
        short_term_risk=round(short_term, 1),
    )
