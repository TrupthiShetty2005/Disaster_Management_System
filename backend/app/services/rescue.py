"""Response planning: nearest real emergency facilities (OpenStreetMap) and road routes (OSRM)."""

from __future__ import annotations

import math
from typing import Any

from app.core.errors import SourceUnavailable
from app.sources import osm

KINDS = {"hospital": 3, "fire_station": 2, "police": 2}


def _km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _kind(tags: dict[str, str]) -> str | None:
    a = tags.get("amenity")
    if a == "hospital" or tags.get("healthcare") == "hospital":
        return "hospital"
    if a in {"fire_station", "police"}:
        return a
    return None


def plan(lat: float, lon: float, search_km: float = 60.0) -> dict[str, Any]:
    elements = [el for el in osm.emergency_facilities() if _km(lat, lon, el["lat"], el["lon"]) <= search_km]
    found: dict[str, list[dict[str, Any]]] = {k: [] for k in KINDS}
    seen = set()
    for el in elements:
        tags = el.get("tags") or {}
        kind = _kind(tags)
        c = {"lat": el["lat"], "lon": el["lon"]}
        if not kind:
            continue
        name = tags.get("name:en") or tags.get("name") or kind.replace("_", " ").title()
        dedupe = (kind, round(c["lat"], 3), round(c["lon"], 3))
        if dedupe in seen:
            continue
        seen.add(dedupe)
        found[kind].append({"kind": kind, "name": name, "latitude": c["lat"], "longitude": c["lon"], "phone": tags.get("phone") or tags.get("contact:phone"), "straight_km": round(_km(lat, lon, c["lat"], c["lon"]), 2), "osm_id": f"{el['type']}/{el['id']}"})
    responders = []
    for kind, n in KINDS.items():
        for fac in sorted(found[kind], key=lambda f: f["straight_km"])[:n]:
            try:
                fac["route"] = osm.route((fac["latitude"], fac["longitude"]), (lat, lon))
            except SourceUnavailable as exc:
                fac["route"] = None
                fac["route_error"] = exc.message
            responders.append(fac)
    responders.sort(key=lambda f: (f["route"] or {}).get("duration_min", 1e9))
    return {
        "target": {"latitude": lat, "longitude": lon},
        "responders": responders,
        "facilities_found": {k: len(v) for k, v in found.items()},
        "sources": {"facilities": "OpenStreetMap (Overpass)", "routing": "OSRM (OpenStreetMap road network)"},
        "note": "Drive times are free-flow estimates on the mapped road network; flooded or blocked roads are not excluded.",
    }
