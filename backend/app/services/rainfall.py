"""District rainfall: observed (last 30 days) and forecast (next 7 days), IMD intensity categories."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.geo.karnataka import DISTRICTS
from app.sources import openmeteo

# IMD 24-hour rainfall categories (mm/day)
IMD_CATEGORIES = (
    (204.5, "EXTREMELY_HEAVY"),
    (115.6, "VERY_HEAVY"),
    (64.5, "HEAVY"),
    (15.6, "MODERATE"),
    (2.5, "LIGHT"),
    (0.1, "VERY_LIGHT"),
)
SEVERITY = {"EXTREMELY_HEAVY": "SEVERE", "VERY_HEAVY": "WARNING", "HEAVY": "WATCH"}


def imd_category(mm: float | None) -> str:
    if mm is None:
        return "NO_DATA"
    for lower, name in IMD_CATEGORIES:
        if mm >= lower:
            return name
    return "NO_RAIN"


def district_weather() -> list[dict[str, Any]]:
    """Raw Open-Meteo daily series for all districts (one multi-location request, cached)."""
    pts = tuple((d.latitude, d.longitude) for d in DISTRICTS)
    return openmeteo.daily_weather(pts, past_days=30, forecast_days=7)


def districts() -> list[dict[str, Any]]:
    today = date.today().isoformat()
    out = []
    for d, row in zip(DISTRICTS, district_weather()):
        daily = row.get("daily") or {}
        days = daily.get("time", [])
        precip = daily.get("precipitation_sum", [])
        prob = daily.get("precipitation_probability_max", [])
        series = [
            {"date": t, "rain_mm": precip[i], "probability_pct": prob[i] if i < len(prob) else None, "forecast": t > today}
            for i, t in enumerate(days)
        ]
        observed = [p for p in series if not p["forecast"] and p["date"] < today and p["rain_mm"] is not None]
        upcoming = [p for p in series if p["date"] >= today]
        next3 = upcoming[:3]
        peak = max(next3, key=lambda p: p["rain_mm"] or 0, default=None)
        cat = imd_category(peak["rain_mm"] if peak else None)
        out.append(
            {
                "id": d.id,
                "name": d.name,
                "hq": d.hq,
                "latitude": d.latitude,
                "longitude": d.longitude,
                "coastal": d.coastal,
                "observed_7d_mm": round(sum(p["rain_mm"] for p in observed[-7:]), 1),
                "observed_30d_mm": round(sum(p["rain_mm"] for p in observed), 1),
                "forecast_3d_mm": round(sum(p["rain_mm"] or 0 for p in next3), 1),
                "forecast_7d_mm": round(sum(p["rain_mm"] or 0 for p in upcoming), 1),
                "peak_day": peak,
                "category": cat,
                "alert_level": SEVERITY.get(cat, "NORMAL"),
                "series": series,
            }
        )
    out.sort(key=lambda r: -(r["peak_day"]["rain_mm"] if r["peak_day"] and r["peak_day"]["rain_mm"] else 0))
    return out


def meta() -> dict[str, Any]:
    return {
        "source": "Open-Meteo (ECMWF/GFS/ICON blend) at each district headquarters",
        "categories_mm_per_day": {name: lower for lower, name in IMD_CATEGORIES},
        "note": "Point forecast at district headquarters; IMD intensity categories. Not an IMD-issued warning.",
    }
