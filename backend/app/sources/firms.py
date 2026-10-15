"""NASA FIRMS active-fire detections (VIIRS S-NPP / NOAA-20 / NOAA-21, MODIS Terra/Aqua)."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any

from app.core import http
from app.core.config import settings
from app.core.errors import SourceUnavailable
from app.geo.karnataka import KARNATAKA_BBOX

BASE = "https://firms.modaps.eosdis.nasa.gov"
FEEDS = {
    "VIIRS_SNPP": "suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_South_Asia_{w}.csv",
    "VIIRS_NOAA20": "noaa-20-viirs-c2/csv/J1_VIIRS_C2_South_Asia_{w}.csv",
    "VIIRS_NOAA21": "noaa-21-viirs-c2/csv/J2_VIIRS_C2_South_Asia_{w}.csv",
    "MODIS": "modis-c6.1/csv/MODIS_C6_1_South_Asia_{w}.csv",
}
AREA_SOURCES = {"VIIRS_SNPP": "VIIRS_SNPP_NRT", "VIIRS_NOAA20": "VIIRS_NOAA20_NRT", "VIIRS_NOAA21": "VIIRS_NOAA21_NRT", "MODIS": "MODIS_NRT"}
WINDOW_DAYS = {"24h": 1, "48h": 2, "7d": 7, "10d": 10}
# Public regional CSVs stop at 7 days; the area API (MAP_KEY) serves up to 10 days of NRT data.
PUBLIC_WINDOWS = ("24h", "48h", "7d")


def available_windows() -> tuple[str, ...]:
    return (*PUBLIC_WINDOWS, "10d") if settings.firms_map_key else PUBLIC_WINDOWS


def _confidence(sensor: str, raw: str) -> str:
    raw = (raw or "").strip().lower()
    if sensor == "MODIS":
        try:
            v = int(raw)
        except ValueError:
            return "nominal"
        return "high" if v >= 80 else "low" if v < 30 else "nominal"
    return {"h": "high", "n": "nominal", "l": "low", "high": "high", "nominal": "nominal", "low": "low"}.get(raw, "nominal")


def _parse(sensor: str, text: str) -> list[dict[str, Any]]:
    w, s, e, n = KARNATAKA_BBOX
    out = []
    for r in csv.DictReader(io.StringIO(text)):
        try:
            lat, lon = float(r["latitude"]), float(r["longitude"])
        except (KeyError, ValueError):
            continue
        if not (s <= lat <= n and w <= lon <= e):
            continue
        t = (r.get("acq_time") or "0000").zfill(4)
        acquired = datetime.strptime(f"{r['acq_date']} {t}", "%Y-%m-%d %H%M").replace(tzinfo=timezone.utc)
        out.append(
            {
                "latitude": lat,
                "longitude": lon,
                "acquired_at": acquired.isoformat(),
                "sensor": sensor,
                "satellite": r.get("satellite"),
                "confidence": _confidence(sensor, r.get("confidence", "")),
                "frp_mw": float(r.get("frp") or 0.0),
                "brightness_k": float(r.get("bright_ti4") or r.get("brightness") or 0.0),
                "daynight": r.get("daynight"),
            }
        )
    return out


@http.ttl_cache(900)
def detections(window: str = "7d") -> dict[str, Any]:
    """All detections in the Karnataka bounding box for the window ("24h", "48h", "7d"; "10d" needs a MAP_KEY)."""
    if window not in available_windows():
        raise SourceUnavailable("nasa-firms", f"The {window} window needs a FIRMS MAP_KEY (public feeds cover 7 days); FIRMS_MAP_KEY is not configured")
    rows: list[dict[str, Any]] = []
    feeds_ok: dict[str, int] = {}
    errors: dict[str, str] = {}
    for sensor, path in FEEDS.items():
        try:
            if settings.firms_map_key:
                days = WINDOW_DAYS[window]
                w, s, e, n = KARNATAKA_BBOX
                url = f"{BASE}/api/area/csv/{settings.firms_map_key}/{AREA_SOURCES[sensor]}/{w},{s},{e},{n}/{days}"
            else:
                url = f"{BASE}/data/active_fire/{path.format(w=window)}"
            parsed = _parse(sensor, http.request("nasa-firms", "GET", url, timeout=60.0).text)
        except SourceUnavailable as exc:
            errors[sensor] = exc.message
            continue
        feeds_ok[sensor] = len(parsed)
        rows.extend(parsed)
    if not feeds_ok:
        raise SourceUnavailable("nasa-firms", "All FIRMS feeds failed: " + "; ".join(errors.values()))
    return {"window": window, "detections": rows, "feeds": feeds_ok, "feed_errors": errors, "retrieved_at": datetime.now(timezone.utc).isoformat()}
