"""OpenStreetMap Overpass (infrastructure) and OSRM (road routing)."""

from __future__ import annotations

import time
from typing import Any

from app.core import http
from app.core.config import settings
from app.core.errors import SourceUnavailable

OVERPASS_MIRRORS = (settings.overpass_url, "https://overpass.kumi.systems/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter")


def overpass(query: str, rounds: int = 2) -> list[dict[str, Any]]:
    """Run an Overpass QL query, cycling through public mirrors (they are frequently overloaded)."""
    last = "no mirror tried"
    for attempt in range(rounds):
        if attempt:
            time.sleep(5)
        for url in OVERPASS_MIRRORS:
            try:
                resp = http.request("overpass", "POST", url, data={"data": query}, retries=0, timeout=180.0)
                return resp.json().get("elements", [])
            except (SourceUnavailable, ValueError) as exc:
                last = str(exc)
    raise SourceUnavailable("overpass", f"All Overpass mirrors failed ({last})")


def _bb(bbox: list[float]) -> str:
    w, s, e, n = bbox
    return f"{s},{w},{n},{e}"


@http.ttl_cache(3 * 86400, disk=True)
def infrastructure(bbox: tuple[float, ...]) -> list[dict[str, Any]]:
    """Buildings (as centroids), roads/rail (geometry), and critical facilities inside bbox."""
    b = _bb(list(bbox))
    q = f"""
    [out:json][timeout:110][maxsize:268435456];
    (
      way["building"]({b});
    )->.bld;
    .bld out center qt;
    (
      way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|service)$"]({b});
      way["railway"="rail"]({b});
      way["power"="line"]({b});
    );
    out geom qt;
    (
      nwr["amenity"~"^(hospital|clinic|school|college|university|fire_station|police|townhall)$"]({b});
      nwr["healthcare"="hospital"]({b});
      nwr["bridge"="yes"]["highway"]({b});
      nwr["power"~"^(substation|plant)$"]({b});
      nwr["man_made"~"^(water_works|wastewater_plant|water_tower)$"]({b});
      nwr["emergency"="assembly_point"]({b});
    );
    out center tags qt;
    """
    return overpass(q)


BUILDING_ID_CHUNK = 1500


@http.ttl_cache(3 * 86400, disk=True)
def _building_chunk(ids: tuple[int, ...]) -> list[dict[str, Any]]:
    q = f"[out:json][timeout:110];way(id:{','.join(str(i) for i in ids)});out geom qt;"
    return [{"id": el["id"], "geometry": el.get("geometry") or []} for el in overpass(q) if el.get("type") == "way"]


def building_geometries(way_ids: list[int]) -> dict[int, list[dict[str, float]]]:
    """Full footprint outlines (lat/lon rings) for specific building ways, fetched by id in chunks."""
    ids = sorted(set(way_ids))
    out: dict[int, list[dict[str, float]]] = {}
    for i in range(0, len(ids), BUILDING_ID_CHUNK):
        for el in _building_chunk(tuple(ids[i : i + BUILDING_ID_CHUNK])):
            out[el["id"]] = el["geometry"]
    return out


@http.ttl_cache(7 * 86400, disk=True)
def emergency_facilities() -> list[dict[str, Any]]:
    """Every mapped hospital, fire station and police station in and around Karnataka (one statewide query)."""
    from app.geo.karnataka import KARNATAKA_BBOX

    w, s, e, n = KARNATAKA_BBOX
    b = _bb([w - 0.3, s - 0.3, e + 0.3, n + 0.3])
    q = f"""
    [out:json][timeout:170];
    (
      nwr["amenity"~"^(hospital|fire_station|police)$"]({b});
      nwr["healthcare"="hospital"]({b});
    );
    out center tags qt;
    """
    out = []
    for el in overpass(q):
        c = el.get("center") or ({"lat": el["lat"], "lon": el["lon"]} if "lat" in el else None)
        if c:
            out.append({"type": el["type"], "id": el["id"], "lat": c["lat"], "lon": c["lon"], "tags": el.get("tags") or {}})
    return out


@http.ttl_cache(6 * 3600)
def route(origin: tuple[float, float], dest: tuple[float, float]) -> dict[str, Any]:
    """Driving route via OSRM. origin/dest are (lat, lon)."""
    coords = f"{origin[1]},{origin[0]};{dest[1]},{dest[0]}"
    d = http.get_json("osrm", f"{settings.osrm_url}/route/v1/driving/{coords}", params={"overview": "full", "geometries": "geojson"})
    if d.get("code") != "Ok" or not d.get("routes"):
        raise SourceUnavailable("osrm", f"No route: {d.get('code')}")
    r = d["routes"][0]
    return {"distance_km": round(r["distance"] / 1000, 2), "duration_min": round(r["duration"] / 60, 1), "geometry": r["geometry"]}
