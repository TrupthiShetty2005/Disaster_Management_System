"""Active fires (NASA FIRMS) and fire-danger prediction for Karnataka districts."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.core.errors import SourceUnavailable
from app.geo import karnataka
from app.geo.karnataka import DISTRICTS, DISTRICTS_BY_ID
from app.services.rainfall import district_weather
from app.sources import firms

CLUSTER_KM = 2.0
# Wildfires move and burn out; a hotspot re-detected on most days at one spot is industrial.
PERSISTENT_MIN_DAYS = 4
PERSISTENT_MAX_KM = 8.0


def _km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dy = (lat2 - lat1) * 110.57
    dx = (lon2 - lon1) * 111.32 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dx, dy)


def detections(window: str = "7d") -> dict[str, Any]:
    raw = firms.detections(window)
    try:
        inside = [d for d in raw["detections"] if karnataka.in_karnataka(d["latitude"], d["longitude"])]
        clipped_by = "Karnataka boundary (OpenStreetMap)"
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
                "classification": "Persistent heat source (likely industrial: steel plant, kiln, flare)" if persistent else "Vegetation / open fire",
                "sensors": sorted({m["sensor"] for m in members}),
                "severity": sev,
                "score": round(score, 1),
                "points": [[m["longitude"], m["latitude"]] for m in members],
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


DANGER_METHOD = (
    "Fosberg Fire Weather Index from forecast daily max temperature, min humidity and max wind "
    "(Open-Meteo). Lowered one level for 1–5 mm and two levels for ≥5 mm forecast rain; raised one "
    "level when FIRMS saw ≥5 non-industrial detections in the district in the last 48 h."
)
