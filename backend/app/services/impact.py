"""Infrastructure exposure and indicative losses: real hazard footprints × OpenStreetMap assets."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

from shapely import affinity
from shapely.geometry import LineString, Point, shape
from shapely.ops import unary_union
from shapely.prepared import prep

from app.core.config import settings
from app.core.errors import SourceUnavailable
from app.sources import osm

MAJOR_ROADS = {"motorway", "trunk", "primary", "secondary"}
FACILITY_TAGS = ("amenity", "healthcare", "power", "man_made", "emergency")


def _to_km(geom, lat0: float):
    """Scale lon/lat degrees to an approximately equal-distance km plane around lat0."""
    return affinity.scale(geom, xfact=111.32 * math.cos(math.radians(lat0)), yfact=110.57, origin=(0, 0))


def _facility_kind(tags: dict[str, str]) -> str | None:
    a = tags.get("amenity")
    if a in {"hospital", "clinic"} or tags.get("healthcare") == "hospital":
        return "health"
    if a in {"school", "college", "university"}:
        return "education"
    if a in {"fire_station", "police"}:
        return "emergency_services"
    if a == "townhall":
        return "government"
    if tags.get("power") in {"substation", "plant"}:
        return "power"
    if tags.get("man_made") in {"water_works", "wastewater_plant", "water_tower"}:
        return "water_supply"
    if tags.get("bridge") == "yes":
        return "bridge"
    if tags.get("emergency") == "assembly_point":
        return "assembly_point"
    return None


def hazard_from_geojson(fc: dict[str, Any], classes: list[str]) -> Any:
    geoms = [shape(f["geometry"]) for f in fc.get("features", []) if f.get("properties", {}).get("class") in classes]
    return unary_union(geoms) if geoms else None


def hazard_from_points(points: list[list[float]], radius_m: float = 500) -> Any:
    lat0 = sum(p[1] for p in points) / len(points)
    deg_lat = radius_m / 110_570
    deg_lon = radius_m / (111_320 * math.cos(math.radians(lat0)))
    circles = [affinity.scale(Point(p).buffer(deg_lat, 16), xfact=deg_lon / deg_lat, yfact=1.0) for p in points]
    return unary_union(circles)


def assess(hazard, hazard_type: str) -> dict[str, Any]:
    if hazard is None or hazard.is_empty:
        return {"status": "no_hazard_footprint", "exposed": {}, "facilities": [], "loss": None}
    w, s, e, n = hazard.bounds
    pad = 0.002
    bbox = (round(w - pad, 4), round(s - pad, 4), round(e + pad, 4), round(n + pad, 4))
    try:
        elements = osm.infrastructure(bbox)
    except SourceUnavailable as exc:
        return {"status": "osm_unavailable", "detail": exc.message, "exposed": {}, "facilities": [], "loss": None}
    lat0 = (s + n) / 2
    hz = prep(hazard)
    hz_km = _to_km(hazard, lat0)
    buildings = 0
    buildings_total = 0
    road_km: Counter[str] = Counter()
    rail_km = 0.0
    power_km = 0.0
    facilities = []
    for el in elements:
        tags = el.get("tags") or {}
        if "building" in tags and "center" in el and el["type"] == "way":
            buildings_total += 1
            if hz.contains(Point(el["center"]["lon"], el["center"]["lat"])):
                buildings += 1
            continue
        geom_pts = el.get("geometry")
        if geom_pts and el["type"] == "way" and ("highway" in tags or "railway" in tags or tags.get("power") == "line"):
            line = LineString([(p["lon"], p["lat"]) for p in geom_pts]) if len(geom_pts) > 1 else None
            if line is None or not hz.intersects(line):
                continue
            km = _to_km(line, lat0).intersection(hz_km).length
            if "highway" in tags:
                road_km[tags["highway"]] += km
            elif "railway" in tags:
                rail_km += km
            else:
                power_km += km
            continue
        kind = _facility_kind(tags)
        if kind:
            c = el.get("center") or ({"lat": el["lat"], "lon": el["lon"]} if "lat" in el else None)
            if c and hz.contains(Point(c["lon"], c["lat"])):
                facilities.append({"kind": kind, "name": tags.get("name") or tags.get("name:en") or kind.replace("_", " "), "latitude": c["lat"], "longitude": c["lon"], "osm_id": f"{el['type']}/{el['id']}"})

    major = sum(v for k, v in road_km.items() if k in MAJOR_ROADS)
    minor = sum(v for k, v in road_km.items() if k not in MAJOR_ROADS)
    ratio = settings.damage_ratio_flood if hazard_type == "flood" else settings.damage_ratio_fire
    parts = {
        "buildings": buildings * settings.loss_building_inr,
        "major_roads": major * settings.loss_road_major_inr_per_km,
        "minor_roads": minor * settings.loss_road_minor_inr_per_km,
        "railways": rail_km * settings.loss_rail_inr_per_km,
        "power_lines": power_km * settings.loss_power_line_inr_per_km,
    }
    replacement = sum(parts.values())
    hazard_km2 = round(hz_km.area, 3)
    return {
        "status": "complete",
        "hazard_type": hazard_type,
        "hazard_area_km2": hazard_km2,
        "exposed": {
            "buildings": buildings,
            "buildings_in_search_area": buildings_total,
            "road_km": round(major + minor, 2),
            "major_road_km": round(major, 2),
            "minor_road_km": round(minor, 2),
            "road_km_by_class": {k: round(v, 2) for k, v in road_km.most_common()},
            "railway_km": round(rail_km, 2),
            "power_line_km": round(power_km, 2),
            "facilities": dict(Counter(f["kind"] for f in facilities)),
        },
        "facilities": facilities[:200],
        "loss": {
            "currency": "INR",
            "exposed_replacement_value": round(replacement),
            "damage_ratio": ratio,
            "estimated_loss": round(replacement * ratio),
            "estimated_loss_crore": round(replacement * ratio / 1e7, 2),
            "by_asset": {k: round(v * ratio) for k, v in parts.items()},
            "assumptions": {
                "building_inr": settings.loss_building_inr,
                "major_road_inr_per_km": settings.loss_road_major_inr_per_km,
                "minor_road_inr_per_km": settings.loss_road_minor_inr_per_km,
                "rail_inr_per_km": settings.loss_rail_inr_per_km,
                "power_line_inr_per_km": settings.loss_power_line_inr_per_km,
                "damage_ratio": ratio,
                "note": "Exposure is measured (satellite footprint × OpenStreetMap). Unit costs and damage ratio are configurable planning assumptions, not surveyed damage.",
            },
        },
        "source": "OpenStreetMap (Overpass API), ODbL",
    }
