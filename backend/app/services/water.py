"""River discharge monitoring and flood prediction for Karnataka rivers and reservoirs.

Data: GloFAS v4 (Copernicus Emergency Management Service) via Open-Meteo — daily reanalysis plus a
30-day ensemble forecast. Flood thresholds are the 2/5/20-year return levels fitted (Gumbel, annual
maxima) to each river cell's own record, mirroring GloFAS alert levels.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Any

import numpy as np

from app.core import http
from app.core.errors import SourceUnavailable
from app.geo.karnataka import DISTRICTS_BY_ID, RIVER_STATIONS, STATIONS_BY_ID, RiverStation
from app.sources import openmeteo

LEVELS = ("NORMAL", "WATCH", "WARNING", "SEVERE")
CELL = 0.05  # GloFAS grid spacing (degrees)


@http.ttl_cache(30 * 86400, disk=True)
def snapped_cell(station_id: str) -> dict[str, float]:
    """GloFAS cells are ~5 km; pick the neighbouring cell carrying the main channel (largest mean flow)."""
    st = STATIONS_BY_ID[station_id]
    offsets = (-CELL, 0.0, CELL)
    pts = tuple((round(st.latitude + dy, 4), round(st.longitude + dx, 4)) for dy in offsets for dx in offsets)
    means = openmeteo.recent_mean_discharge(pts)
    best_i = max(range(len(pts)), key=lambda i: means[i])
    if means[best_i] <= 0:
        raise SourceUnavailable("open-meteo-flood", f"No GloFAS river cell found near {st.name}")
    return {"latitude": pts[best_i][0], "longitude": pts[best_i][1], "mean_flow_28d": round(means[best_i], 2)}


def gumbel_return_levels(annual_max: list[float], periods: tuple[int, ...] = (2, 5, 20)) -> dict[str, float]:
    x = np.asarray(annual_max, dtype=float)
    mu, sigma = float(x.mean()), float(x.std(ddof=1))
    alpha = sigma * math.sqrt(6) / math.pi
    u = mu - 0.5772 * alpha
    return {f"q{t}": round(u - alpha * math.log(-math.log(1 - 1 / t)), 1) for t in periods}


def thresholds(station_id: str) -> dict[str, Any]:
    cell = snapped_cell(station_id)
    hist = openmeteo.seasonal_discharge_maxima(cell["latitude"], cell["longitude"])
    maxima = hist["maxima"]
    if len(maxima) < 10:
        raise SourceUnavailable("open-meteo-flood", f"Insufficient discharge record for {station_id}")
    top_year = max(maxima, key=maxima.get)
    return {
        **gumbel_return_levels(list(maxima.values())),
        "record_years": len(maxima),
        "record_period": f"{hist['first_year']}–{hist['last_year']} (Jun–Nov)",
        "season_median_flow": round(hist["season_median"], 1) if hist["season_median"] is not None else None,
        "record_max": round(maxima[top_year], 1),
        "record_max_year": int(top_year),
    }


def thresholds_ready(station_id: str) -> dict[str, Any] | None:
    """Thresholds if already cached; never blocks a request on the ~20-request history download."""
    from app.core.http import is_cached

    cell = snapped_cell(station_id)
    if not is_cached(openmeteo.seasonal_discharge_maxima, cell["latitude"], cell["longitude"]):
        return None
    return thresholds(station_id)


def _level(q: float | None, th: dict[str, Any] | None) -> str | None:
    if th is None:
        return None
    if q is None:
        return "NORMAL"
    if q >= th["q20"]:
        return "SEVERE"
    if q >= th["q5"]:
        return "WARNING"
    if q >= th["q2"]:
        return "WATCH"
    return "NORMAL"


def _station_report(st: RiverStation, row: dict[str, Any], th: dict[str, Any] | None, cell: dict[str, float]) -> dict[str, Any]:
    daily = row.get("daily") or {}
    today = date.today().isoformat()
    series = []
    for i, d in enumerate(daily.get("time", [])):
        def g(k: str):
            v = (daily.get(k) or [None] * (i + 1))[i]
            return None if v is None else round(float(v), 2)

        series.append(
            {
                "date": d,
                "discharge": g("river_discharge"),
                "median": g("river_discharge_median"),
                "p25": g("river_discharge_p25"),
                "p75": g("river_discharge_p75"),
                "min": g("river_discharge_min"),
                "max": g("river_discharge_max"),
                "forecast": d > today,
            }
        )
    past = [p for p in series if not p["forecast"] and p["discharge"] is not None]
    future = [p for p in series if p["forecast"]]
    current = past[-1] if past else None
    week_ago = past[-8] if len(past) >= 8 else None

    def peak(key: str) -> dict[str, Any] | None:
        vals = [p for p in future if p.get(key) is not None]
        if not vals:
            return None
        top = max(vals, key=lambda p: p[key])
        return {"date": top["date"], "discharge": top[key]}

    peak_expected = peak("median") or peak("discharge")
    peak_upper = peak("p75")
    peak_worst = peak("max")
    expected_level = _level(peak_expected["discharge"] if peak_expected else None, th)
    likely_level = _level(peak_upper["discharge"] if peak_upper else None, th)
    current_level = _level(current["discharge"] if current else None, th)
    status = max((current_level, expected_level), key=LEVELS.index) if th else "CALIBRATING"
    trend = None
    if current and week_ago and week_ago["discharge"]:
        trend = round(100 * (current["discharge"] - week_ago["discharge"]) / week_ago["discharge"], 1)
    pct_q2 = round(100 * current["discharge"] / th["q2"], 1) if current and th and th["q2"] else None
    district = DISTRICTS_BY_ID[st.district_id]
    return {
        "id": st.id,
        "name": st.name,
        "river": st.river,
        "kind": st.kind,
        "district_id": st.district_id,
        "district": district.name,
        "latitude": st.latitude,
        "longitude": st.longitude,
        "glofas_cell": cell,
        "current": current,
        "current_level": current_level,
        "percent_of_2yr_flood": pct_q2,
        "trend_7d_pct": trend,
        "forecast_peak": {"expected": peak_expected, "upper_p75": peak_upper, "worst_case": peak_worst},
        "predicted_level": expected_level,
        "predicted_level_upper": likely_level,
        "status": status,
        "thresholds": th,
        "series": series,
        "unit": "m³/s",
        "source": "GloFAS v4 (Copernicus EMS) via Open-Meteo",
        "method": (
            "Forecast peak (ensemble median / p75 / max) vs 2-, 5- and 20-year return levels, Gumbel-fitted to "
            "this river cell's annual Jun–Nov maxima since 2005. CALIBRATING = thresholds still downloading."
        ),
    }


def stations(include_series: bool = True) -> list[dict[str, Any]]:
    cells = {st.id: snapped_cell(st.id) for st in RIVER_STATIONS}
    pts = tuple((cells[s.id]["latitude"], cells[s.id]["longitude"]) for s in RIVER_STATIONS)
    rows = openmeteo.river_discharge(pts, past_days=60, forecast_days=30)
    out = []
    for st, row in zip(RIVER_STATIONS, rows):
        try:
            th = thresholds_ready(st.id)
        except SourceUnavailable:
            th = None
        rep = _station_report(st, row, th, cells[st.id])
        if not include_series:
            rep.pop("series")
        out.append(rep)
    rank = {lvl: i for i, lvl in enumerate(("CALIBRATING",) + LEVELS)}
    out.sort(key=lambda r: (-rank[r["status"]], -(r["percent_of_2yr_flood"] or 0)))
    return out


def station(station_id: str) -> dict[str, Any]:
    if station_id not in STATIONS_BY_ID:
        raise KeyError(station_id)
    for rep in stations():
        if rep["id"] == station_id:
            return rep
    raise SourceUnavailable("open-meteo-flood", f"Station {station_id} could not be evaluated")
