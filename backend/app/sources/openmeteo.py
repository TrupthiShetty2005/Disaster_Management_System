"""Open-Meteo: weather forecast/history and GloFAS v4 river discharge (no API key).

Free-tier limits are counted in weighted calls (one call = one location, <=10 variables, <=2 weeks).
`_pace` keeps us under the per-minute budget so bursts never trip HTTP 429.
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from datetime import date
from typing import Any

from app.core import http

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
FLOOD_URL = "https://flood-api.open-meteo.com/v1/flood"
MINUTE_BUDGET = 450

DAILY_WEATHER = (
    "precipitation_sum,precipitation_probability_max,temperature_2m_max,temperature_2m_min,"
    "relative_humidity_2m_min,wind_speed_10m_max,wind_gusts_10m_max,weather_code"
)
DISCHARGE_VARS = "river_discharge,river_discharge_median,river_discharge_max,river_discharge_min,river_discharge_p25,river_discharge_p75"

_window: deque[tuple[float, float]] = deque()
_pace_lock = threading.Lock()


def _weight(locations: int, days: int, variables: int) -> float:
    return locations * max(1.0, days / 14) * max(1, math.ceil(variables / 10))


def _pace(weight: float) -> None:
    with _pace_lock:
        while True:
            now = time.time()
            while _window and now - _window[0][0] > 60:
                _window.popleft()
            used = sum(w for _, w in _window)
            if used + weight <= MINUTE_BUDGET or not _window:
                _window.append((now, weight))
                return
            time.sleep(max(0.5, 60 - (now - _window[0][0])))


def _get(source: str, url: str, params: dict[str, Any], weight: float, timeout: float = 45.0) -> Any:
    _pace(weight)
    return http.get_json(source, url, params=params, timeout=timeout)


def _as_list(payload: Any) -> list[dict[str, Any]]:
    return payload if isinstance(payload, list) else [payload]


def _coords(points: tuple[tuple[float, float], ...]) -> dict[str, str]:
    return {"latitude": ",".join(f"{p[0]:.4f}" for p in points), "longitude": ",".join(f"{p[1]:.4f}" for p in points)}


@http.ttl_cache(2 * 3600)
def daily_weather(points: tuple[tuple[float, float], ...], past_days: int = 30, forecast_days: int = 7) -> list[dict[str, Any]]:
    """Daily weather for many points in one multi-location call."""
    params = {**_coords(points), "daily": DAILY_WEATHER, "past_days": past_days, "forecast_days": forecast_days, "timezone": "Asia/Kolkata"}
    return _as_list(_get("open-meteo", FORECAST_URL, params, _weight(len(points), past_days + forecast_days, 8)))


@http.ttl_cache(1800)
def hourly_weather(lat: float, lon: float, forecast_days: int = 3) -> dict[str, Any]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation,precipitation_probability,temperature_2m,relative_humidity_2m,wind_speed_10m",
        "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
        "forecast_days": forecast_days,
        "timezone": "Asia/Kolkata",
    }
    return _get("open-meteo", FORECAST_URL, params, _weight(1, forecast_days, 10))


@http.ttl_cache(3 * 3600)
def river_discharge(points: tuple[tuple[float, float], ...], past_days: int = 60, forecast_days: int = 30) -> list[dict[str, Any]]:
    """GloFAS daily discharge: recent reanalysis plus ensemble forecast statistics."""
    params = {**_coords(points), "daily": DISCHARGE_VARS, "past_days": past_days, "forecast_days": forecast_days}
    return _as_list(_get("open-meteo-flood", FLOOD_URL, params, _weight(len(points), past_days + forecast_days, 6)))


@http.ttl_cache(30 * 86400, disk=True)
def recent_mean_discharge(points: tuple[tuple[float, float], ...]) -> list[float]:
    params = {**_coords(points), "daily": "river_discharge", "past_days": 28, "forecast_days": 1}
    rows = _as_list(_get("open-meteo-flood", FLOOD_URL, params, _weight(len(points), 29, 1)))
    out = []
    for row in rows:
        vals = [v for v in (row.get("daily") or {}).get("river_discharge", []) if v is not None]
        out.append(sum(vals) / len(vals) if vals else -1.0)
    return out


@http.ttl_cache(180 * 86400, disk=True)
def seasonal_discharge_maxima(lat: float, lon: float, first_year: int = 2005, last_year: int | None = None) -> dict[str, Any]:
    """Annual maximum discharge per year (June–November, when Karnataka's annual peaks occur)."""
    last_year = last_year or date.today().year - 1
    maxima: dict[str, float] = {}
    all_vals: list[float] = []
    for y in range(first_year, last_year + 1):
        start, end = date(y, 6, 1), date(y, 11, 30)
        params = {"latitude": lat, "longitude": lon, "daily": "river_discharge", "start_date": start.isoformat(), "end_date": end.isoformat()}
        d = _get("open-meteo-flood", FLOOD_URL, params, _weight(1, (end - start).days + 1, 1))
        vals = [v for v in (d.get("daily") or {}).get("river_discharge", []) if v is not None]
        if vals:
            maxima[str(y)] = max(vals)
            all_vals.extend(vals)
    all_vals.sort()
    med = all_vals[len(all_vals) // 2] if all_vals else None
    return {"maxima": maxima, "season_median": med, "first_year": first_year, "last_year": last_year}
