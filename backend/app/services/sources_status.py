"""Health of every live upstream source, probed with small real requests (cached briefly)."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from app.core import http
from app.core.config import settings
from app.core.errors import SourceUnavailable


def _probe(name: str, purpose: str, fn: Callable[[], str]) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        detail = fn()
        ok = True
    except SourceUnavailable as exc:
        detail, ok = exc.message, False
    except Exception as exc:  # noqa: BLE001
        detail, ok = str(exc), False
    return {"name": name, "purpose": purpose, "ok": ok, "latency_ms": round((time.perf_counter() - t0) * 1000), "detail": detail}


def _openweather() -> str:
    from app.sources import openweather

    c = openweather.current(settings.default_latitude, settings.default_longitude)
    return f"{c['station']}: {c['temperature_c']}°C, {c['condition']}"


def _openmeteo() -> str:
    d = http.get_json("open-meteo", "https://api.open-meteo.com/v1/forecast", params={"latitude": 12.97, "longitude": 77.59, "current": "temperature_2m"})
    return f"model time {d['current']['time']}"


def _glofas() -> str:
    d = http.get_json("open-meteo-flood", "https://flood-api.open-meteo.com/v1/flood", params={"latitude": 16.33, "longitude": 75.89, "daily": "river_discharge", "forecast_days": 1})
    return f"Krishna @ Almatti {d['daily']['river_discharge'][0]} m³/s"


def _firms() -> str:
    r = http.request("nasa-firms", "GET", "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_South_Asia_24h.csv", timeout=45)
    return f"{r.text.count(chr(10)) - 1} South Asia detections (24 h)"


def _gdacs() -> str:
    from app.sources import gdacs

    ev = gdacs.india_events()
    return f"{len(ev)} India events (90 days)"


def _planetary() -> str:
    d = http.get_json("planetary-computer", f"{settings.planetary_stac_url}/collections/sentinel-1-rtc")
    return d.get("title", "Sentinel-1 RTC")


def _overpass() -> str:
    from app.sources.osm import overpass

    els = overpass('[out:json][timeout:20];node["amenity"="hospital"](12.95,77.57,12.99,77.61);out ids;')
    return f"{len(els)} hospitals in central Bengaluru"


def _osrm() -> str:
    d = http.get_json("osrm", f"{settings.osrm_url}/nearest/v1/driving/77.5946,12.9716")
    return d.get("code", "?")


def _nominatim() -> str:
    d = http.get_json("nominatim", "https://nominatim.openstreetmap.org/status", params={"format": "json"})
    return d.get("message", "ok")


PROBES = (
    ("OpenWeather", "Current weather and 5-day forecast", _openweather),
    ("Open-Meteo", "District rainfall/weather forecast and 30-day history", _openmeteo),
    ("GloFAS (Open-Meteo Flood)", "River discharge history and 30-day ensemble forecast", _glofas),
    ("NASA FIRMS", "Active fire detections (VIIRS, MODIS)", _firms),
    ("GDACS", "Global disaster alerts for India", _gdacs),
    ("Planetary Computer", "Sentinel-1 SAR and Sentinel-2 imagery", _planetary),
    ("OpenStreetMap Overpass", "Buildings, roads, facilities", _overpass),
    ("OSRM", "Road routing for responders", _osrm),
    ("Nominatim", "Karnataka and district boundaries", _nominatim),
)


@http.ttl_cache(300)
def status() -> list[dict[str, Any]]:
    with ThreadPoolExecutor(max_workers=len(PROBES)) as pool:
        return list(pool.map(lambda p: _probe(*p), PROBES))
