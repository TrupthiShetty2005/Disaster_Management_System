"""Active fires (NASA FIRMS) and fire-danger prediction for Karnataka districts."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

from shapely.geometry import Point, box
from shapely.geometry.base import BaseGeometry

from app.core import http
from app.core.config import settings
from app.core.errors import SourceUnavailable
from app.geo import karnataka
from app.geo.industrial_sites import SITES, IndustrialSite
from app.geo.karnataka import DISTRICTS, DISTRICTS_BY_ID
from app.services.rainfall import district_weather
from app.sources import firms, openmeteo

CLUSTER_KM = 2.0
# Wildfires move and burn out; a hotspot re-detected on most days at one spot is industrial.
PERSISTENT_MIN_DAYS = 4
PERSISTENT_MAX_KM = 8.0
# The OSM state outline is simplified (~500 m), so shoreline plants, ports and flares can fall just
# "offshore". Accept points within ~2 km of the boundary, but only along the Arabian Sea coast
# (Talapady to the Goa border) so that detections across inland state borders stay excluded.
COAST_BUFFER_DEG = 0.02
COAST_BOX = (73.9, 12.80, 75.0, 14.88)


def _km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dy = (lat2 - lat1) * 110.57
    dx = (lon2 - lon1) * 111.32 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dx, dy)


@lru_cache(maxsize=1)
def _coastal_band() -> BaseGeometry:
    return karnataka._state_shape().buffer(COAST_BUFFER_DEG).intersection(box(*COAST_BOX))


def in_state(lat: float, lon: float) -> bool:
    """Inside the Karnataka polygon, or within the coastal tolerance band along the Arabian Sea."""
    if karnataka.in_karnataka(lat, lon):
        return True
    w, s, e, n = COAST_BOX
    return w <= lon <= e and s <= lat <= n and _coastal_band().contains(Point(lon, lat))


def nearest_site(lat: float, lon: float) -> dict[str, Any] | None:
    """Closest monitored industrial site whose search radius contains the point."""
    best = min(((_km(lat, lon, s.latitude, s.longitude), s) for s in SITES), key=lambda t: t[0])
    dist, site = best
    return {"id": site.id, "name": site.name, "distance_km": round(dist, 2)} if dist <= site.radius_km else None


def detections(window: str = "7d") -> dict[str, Any]:
    raw = firms.detections(window)
    try:
        inside = [d for d in raw["detections"] if in_state(d["latitude"], d["longitude"])]
        clipped_by = "Karnataka boundary (OpenStreetMap, +2 km tolerance along the coast)"
    except SourceUnavailable:
        inside = raw["detections"]
        clipped_by = "Karnataka bounding box (boundary unavailable)"
    for d in inside:
        d["district_id"] = karnataka.district_for(d["latitude"], d["longitude"])
        d["district"] = DISTRICTS_BY_ID[d["district_id"]].name
    inside.sort(key=lambda d: d["acquired_at"], reverse=True)
    return {**raw, "detections": inside, "count": len(inside), "clipped_by": clipped_by}


def clusters(window: str = "7d") -> list[dict[str, Any]]:
    """Group detections within CLUSTER_KM of each other (single-linkage) into fire events."""
    pts = detections(window)["detections"]
    n = len(pts)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    order = sorted(range(n), key=lambda i: pts[i]["latitude"])
    deg = CLUSTER_KM / 110.57
    for a_idx, i in enumerate(order):
        for j in order[a_idx + 1 :]:
            if pts[j]["latitude"] - pts[i]["latitude"] > deg:
                break
            if _km(pts[i]["latitude"], pts[i]["longitude"], pts[j]["latitude"], pts[j]["longitude"]) <= CLUSTER_KM:
                parent[find(i)] = find(j)
    groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(pts[i])
    now = datetime.now(timezone.utc)
    out = []
    for members in groups.values():
        lats = [m["latitude"] for m in members]
        lons = [m["longitude"] for m in members]
        times = sorted(m["acquired_at"] for m in members)
        frp = sum(m["frp_mw"] for m in members)
        last = datetime.fromisoformat(times[-1])
        high = sum(1 for m in members if m["confidence"] == "high")
        active = (now - last) <= timedelta(hours=24)
        score = len(members) + frp / 10 + 2 * high
        clat, clon = sum(lats) / len(lats), sum(lons) / len(lons)
        days_seen = len({m["acquired_at"][:10] for m in members})
        span_km = _km(min(lats), min(lons), max(lats), max(lons))
        persistent = window == "7d" and days_seen >= PERSISTENT_MIN_DAYS and span_km <= PERSISTENT_MAX_KM
        if persistent:
            sev = "INFO"
        elif active and (frp >= 150 or len(members) >= 15):
            sev = "SEVERE"
        elif active and (frp >= 40 or len(members) >= 5):
            sev = "WARNING"
        else:
            sev = "WATCH" if active else "INFO"
        did = karnataka.district_for(clat, clon)
        site = nearest_site(clat, clon)
        if persistent:
            classification = f"Persistent heat source near {site['name']}" if site else "Persistent heat source (likely industrial: steel plant, kiln, flare)"
        else:
            classification = "Vegetation / open fire" if not site else f"Thermal anomaly at {site['name']} (not persistent)"
        history = sorted(members, key=lambda m: m["acquired_at"], reverse=True)
        out.append(
            {
                "id": f"fire-{round(clat, 3)}-{round(clon, 3)}",
                "latitude": round(clat, 5),
                "longitude": round(clon, 5),
                "bbox": [min(lons), min(lats), max(lons), max(lats)],
                "district_id": did,
                "district": DISTRICTS_BY_ID[did].name,
                "detections": len(members),
                "high_confidence": high,
                "total_frp_mw": round(frp, 1),
                "max_frp_mw": round(max(m["frp_mw"] for m in members), 1),
                "first_seen": times[0],
                "last_seen": times[-1],
                "active_24h": active,
                "days_seen": days_seen,
                "persistent_heat_source": persistent,
                "classification": classification,
                "nearest_site": site,
                "sensors": sorted({m["sensor"] for m in members}),
                "severity": sev,
                "score": round(score, 1),
                "points": [[m["longitude"], m["latitude"]] for m in members],
                "members": [
                    {k: m.get(k) for k in ("latitude", "longitude", "acquired_at", "sensor", "satellite", "confidence", "frp_mw", "daynight")}
                    for m in history
                ],
            }
        )
    out.sort(key=lambda c: (c["persistent_heat_source"], -c["active_24h"], -c["score"]))
    return out


def fosberg_ffwi(temp_c: float, rh_pct: float, wind_kmh: float) -> float:
    """Fosberg Fire Weather Index (0–100+): fuel moisture equilibrium from T/RH, combined with wind."""
    t = temp_c * 9 / 5 + 32
    h = max(0.0, min(100.0, rh_pct))
    u = wind_kmh * 0.621371
    if h < 10:
        m = 0.03229 + 0.281073 * h - 0.000578 * h * t
    elif h < 50:
        m = 2.22749 + 0.160107 * h - 0.01478 * t
    else:
        m = 21.0606 + 0.005565 * h * h - 0.00035 * h * t - 0.483199 * h
    x = m / 30
    eta = 1 - 2 * x + 1.5 * x * x - 0.5 * x**3
    return round(max(0.0, eta * math.sqrt(1 + u * u) / 0.3002), 1)


def ffwi_class(v: float) -> str:
    return "EXTREME" if v >= 75 else "VERY_HIGH" if v >= 50 else "HIGH" if v >= 30 else "MODERATE" if v >= 15 else "LOW"


LEVEL_ORDER = ("LOW", "MODERATE", "HIGH", "VERY_HIGH", "EXTREME")


def danger_forecast() -> list[dict[str, Any]]:
    """Next 3 days per district: FFWI from forecast afternoon conditions, wetted by rain, raised by active fires."""
    try:
        recent = detections("48h")["detections"]
        industrial = [c["bbox"] for c in clusters("7d") if c["persistent_heat_source"]]
    except SourceUnavailable:
        recent, industrial = [], []

    def is_industrial(d: dict[str, Any]) -> bool:
        pad = 0.01
        return any(b[0] - pad <= d["longitude"] <= b[2] + pad and b[1] - pad <= d["latitude"] <= b[3] + pad for b in industrial)

    active_by_district: dict[str, int] = defaultdict(int)
    for d in recent:
        if not is_industrial(d):
            active_by_district[d["district_id"]] += 1
    today = date.today().isoformat()
    out = []
    for dist, row in zip(DISTRICTS, district_weather()):
        daily = row.get("daily") or {}
        days = []
        for i, t in enumerate(daily.get("time", [])):
            if t < today or len(days) >= 3:
                continue
            tmax = daily["temperature_2m_max"][i]
            rhmin = daily["relative_humidity_2m_min"][i]
            wind = daily["wind_speed_10m_max"][i]
            rain = daily["precipitation_sum"][i] or 0.0
            if None in (tmax, rhmin, wind):
                continue
            idx = fosberg_ffwi(tmax, rhmin, wind)
            level = ffwi_class(idx)
            if rain >= 5:
                level = LEVEL_ORDER[max(0, LEVEL_ORDER.index(level) - 2)]
            elif rain >= 1:
                level = LEVEL_ORDER[max(0, LEVEL_ORDER.index(level) - 1)]
            if active_by_district[dist.id] >= 5:
                level = LEVEL_ORDER[min(len(LEVEL_ORDER) - 1, LEVEL_ORDER.index(level) + 1)]
            days.append({"date": t, "ffwi": idx, "level": level, "temp_max_c": tmax, "rh_min_pct": rhmin, "wind_max_kmh": wind, "rain_mm": rain})
        peak = max(days, key=lambda d: LEVEL_ORDER.index(d["level"]), default=None)
        out.append(
            {
                "id": dist.id,
                "name": dist.name,
                "latitude": dist.latitude,
                "longitude": dist.longitude,
                "active_detections_48h": active_by_district[dist.id],
                "days": days,
                "peak_level": peak["level"] if peak else None,
                "peak_ffwi": peak["ffwi"] if peak else None,
            }
        )
    out.sort(key=lambda r: (-(LEVEL_ORDER.index(r["peak_level"]) if r["peak_level"] else -1), -r["active_detections_48h"]))
    return out


SITE_LIMITATIONS = (
    "FIRMS only records a fire if a polar-orbiting satellite passes over while it is burning and the sky is clear. "
    "VIIRS (S-NPP, NOAA-20, NOAA-21) images Karnataka around 01:30 and 13:30 local time and MODIS (Terra/Aqua) around "
    "10:30/22:30 and 13:30/01:30, so a short industrial fire that starts and is put out between passes is never seen. "
    "Cloud blocks the thermal-infrared signal entirely, and a fire inside a building, tank or process unit — or one much "
    "smaller than a 375 m VIIRS / 1 km MODIS pixel — may not heat the pixel enough to be flagged. "
    "Absence of a FIRMS detection therefore does not mean no incident occurred."
)


def _archive_info() -> dict[str, Any]:
    windows = firms.available_windows()
    keyed = bool(settings.firms_map_key)
    note = (
        "FIRMS MAP_KEY configured: the area API adds a 10-day window. Older data needs the FIRMS archive download."
        if keyed
        else "No FIRMS MAP_KEY is configured, so only the public 24 h / 48 h / 7-day feeds are available. "
        "Detections older than 7 days cannot be checked here; add a free key as FIRMS_MAP_KEY in backend/.env for a 10-day window, "
        "or use FIRMS Archive Download for older dates."
    )
    return {"map_key_configured": keyed, "windows": list(windows), "max_days": firms.WINDOW_DAYS[windows[-1]], "note": note}


@http.ttl_cache(3600)
def _cloud_at_satellite_passes(points: tuple[tuple[float, float], ...]) -> list[dict[str, Any]]:
    """Open-Meteo hourly cloud cover at the ~01:30 and ~13:30 IST VIIRS passes for the past 7 days."""
    params = {**openmeteo._coords(points), "hourly": "cloud_cover", "past_days": 7, "forecast_days": 1, "timezone": "Asia/Kolkata"}
    rows = openmeteo._as_list(openmeteo._get("open-meteo", openmeteo.FORECAST_URL, params, openmeteo._weight(len(points), 8, 1)))
    now_ist = (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%dT%H:%M")
    out = []
    for r in rows:
        hourly = r.get("hourly") or {}
        by_day: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"night": [], "day": []})
        for t, c in zip(hourly.get("time", []), hourly.get("cloud_cover", [])):
            if c is None or t > now_ist:
                continue
            hour = int(t[11:13])
            if hour in (1, 2):
                by_day[t[:10]]["night"].append(c)
            elif hour in (13, 14):
                by_day[t[:10]]["day"].append(c)
        days = [
            {"date": d, "night_pct": round(sum(v["night"]) / len(v["night"])) if v["night"] else None, "day_pct": round(sum(v["day"]) / len(v["day"])) if v["day"] else None}
            for d, v in sorted(by_day.items())
        ]
        vals = [x for d in days for x in (d["night_pct"], d["day_pct"]) if x is not None]
        out.append({"mean_pct": round(sum(vals) / len(vals)) if vals else None, "days": days})
    return out


def _site_hit(site: IndustrialSite, d: dict[str, Any], dist: float) -> dict[str, Any]:
    facility = min(site.facilities, key=lambda f: _km(d["latitude"], d["longitude"], f.latitude, f.longitude)).name if site.facilities else site.name
    keys = ("latitude", "longitude", "acquired_at", "sensor", "satellite", "confidence", "frp_mw", "daynight")
    return {**{k: d.get(k) for k in keys}, "distance_km": round(dist, 2), "nearest_facility": facility}


def monitored_sites() -> dict[str, Any]:
    """Live FIRMS detections around each monitored industrial site for every available window."""
    per_window: dict[str, list[dict[str, Any]]] = {}
    unavailable: dict[str, str] = {}
    feeds: dict[str, int] = {}
    for w in firms.available_windows():
        try:
            res = firms.detections(w)
        except SourceUnavailable as exc:
            unavailable[w] = exc.message
            continue
        per_window[w] = res["detections"]
        feeds = res["feeds"]
    if not per_window:
        raise SourceUnavailable("nasa-firms", "; ".join(unavailable.values()))
    longest = max(per_window, key=lambda w: firms.WINDOW_DAYS[w])
    pts = per_window[longest]
    times = sorted(d["acquired_at"] for d in pts)
    coverage = {"window": longest, "from": times[0] if times else None, "to": times[-1] if times else None}
    try:
        clouds: list[dict[str, Any]] | None = _cloud_at_satellite_passes(tuple((s.latitude, s.longitude) for s in SITES))
    except SourceUnavailable:
        clouds = None

    items = []
    for i, site in enumerate(SITES):
        counts = {w: sum(1 for d in rows if _km(d["latitude"], d["longitude"], site.latitude, site.longitude) <= site.radius_km) for w, rows in per_window.items()}
        dists = [(_km(d["latitude"], d["longitude"], site.latitude, site.longitude), d) for d in pts]
        hits = sorted((_site_hit(site, d, dist) for dist, d in dists if dist <= site.radius_km), key=lambda h: h["acquired_at"], reverse=True)
        near = min(dists, key=lambda t: t[0], default=None)
        nearest = _site_hit(site, near[1], near[0]) if near else None
        if hits:
            status = "DETECTED_24H" if counts.get("24h") else "DETECTED"
            summary = (
                f"{len(hits)} FIRMS detection(s) within {site.radius_km:g} km in the last {longest} "
                f"(on {len({h['acquired_at'][:10] for h in hits})} day(s)); latest {hits[0]['acquired_at'][:16].replace('T', ' ')} UTC by {hits[0]['sensor']}."
            )
        else:
            status = "NO_DETECTION"
            summary = f"No satellite thermal detection within {site.radius_km:g} km in the available FIRMS window ({longest})."
            if nearest:
                summary += f" Nearest detection anywhere in Karnataka's bounding box was {nearest['distance_km']:g} km away."
        items.append(
            {
                "id": site.id,
                "name": site.name,
                "kind": site.kind,
                "district_id": site.district_id,
                "district": DISTRICTS_BY_ID[site.district_id].name,
                "latitude": site.latitude,
                "longitude": site.longitude,
                "radius_km": site.radius_km,
                "facilities": [{"name": f.name, "latitude": f.latitude, "longitude": f.longitude} for f in site.facilities],
                "status": status,
                "counts": counts,
                "last_detection": hits[0]["acquired_at"] if hits else None,
                "days_with_detections": len({h["acquired_at"][:10] for h in hits}),
                "total_frp_mw": round(sum(h["frp_mw"] or 0.0 for h in hits), 1),
                "max_frp_mw": round(max((h["frp_mw"] or 0.0 for h in hits), default=0.0), 1),
                "history": hits[:300],
                "nearest_detection": nearest,
                "cloud_at_passes": clouds[i] if clouds and i < len(clouds) else None,
                "summary": summary,
            }
        )
    return {
        "items": items,
        "coverage": coverage,
        "feeds": feeds,
        "unavailable_windows": unavailable,
        "archive": _archive_info(),
        "limitations": SITE_LIMITATIONS,
        "sources": "NASA FIRMS (VIIRS S-NPP/NOAA-20/NOAA-21, MODIS) · site locations: OpenStreetMap · cloud cover: Open-Meteo",
    }


DANGER_METHOD = (
    "Fosberg Fire Weather Index from forecast daily max temperature, min humidity and max wind "
    "(Open-Meteo). Lowered one level for 1–5 mm and two levels for ≥5 mm forecast rain; raised one "
    "level when FIRMS saw ≥5 non-industrial detections in the district in the last 48 h."
)
