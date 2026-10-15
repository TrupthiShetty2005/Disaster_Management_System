"""OpenWeather current conditions and 5-day / 3-hour forecast."""

from __future__ import annotations

from typing import Any

from app.core import http
from app.core.config import settings
from app.core.errors import SourceUnavailable

BASE = "https://api.openweathermap.org/data/2.5"


def _key() -> str:
    if not settings.openweather_api_key:
        raise SourceUnavailable("openweather", "OPENWEATHER_API_KEY is not set in backend/.env")
    return settings.openweather_api_key


@http.ttl_cache(600)
def current(lat: float, lon: float) -> dict[str, Any]:
    d = http.get_json("openweather", f"{BASE}/weather", params={"lat": lat, "lon": lon, "appid": _key(), "units": "metric"})
    rain = d.get("rain") or {}
    return {
        "observed_at": d.get("dt"),
        "station": d.get("name"),
        "temperature_c": d["main"]["temp"],
        "feels_like_c": d["main"].get("feels_like"),
        "humidity_pct": d["main"]["humidity"],
        "pressure_hpa": d["main"]["pressure"],
        "wind_speed_ms": (d.get("wind") or {}).get("speed"),
        "wind_gust_ms": (d.get("wind") or {}).get("gust"),
        "rain_1h_mm": rain.get("1h"),
        "rain_3h_mm": rain.get("3h"),
        "clouds_pct": (d.get("clouds") or {}).get("all"),
        "visibility_m": d.get("visibility"),
        "condition": (d.get("weather") or [{}])[0].get("description"),
        "icon": (d.get("weather") or [{}])[0].get("icon"),
        "source": "OpenWeather",
    }


@http.ttl_cache(1800)
def forecast(lat: float, lon: float) -> list[dict[str, Any]]:
    d = http.get_json("openweather", f"{BASE}/forecast", params={"lat": lat, "lon": lon, "appid": _key(), "units": "metric"})
    return [
        {
            "time": item.get("dt"),
            "temperature_c": item["main"]["temp"],
            "humidity_pct": item["main"]["humidity"],
            "wind_speed_ms": (item.get("wind") or {}).get("speed"),
            "rain_3h_mm": (item.get("rain") or {}).get("3h", 0.0),
            "pop": item.get("pop"),
            "condition": (item.get("weather") or [{}])[0].get("description"),
        }
        for item in d.get("list", [])
    ]
