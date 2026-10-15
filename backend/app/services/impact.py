"""Infrastructure exposure and indicative losses: real hazard footprints × OpenStreetMap assets."""

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from shapely import STRtree, affinity
from shapely.geometry import LineString, Point, Polygon, box, mapping, shape
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


def _search_bbox(hazard) -> tuple[float, float, float, float]:
    w, s, e, n = hazard.bounds
    pad = 0.002
    return (round(w - pad, 4), round(s - pad, 4), round(e + pad, 4), round(n + pad, 4))


def assess(hazard, hazard_type: str) -> dict[str, Any]:
    if hazard is None or hazard.is_empty:
        return {"status": "no_hazard_footprint", "exposed": {}, "facilities": [], "loss": None}
    w, s, e, n = hazard.bounds
    bbox = _search_bbox(hazard)
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


# ---------------------------------------------------------------- per-asset GeoJSON (3D damage view)
HAZARD_CLASSES = {"flood": ["newly_flooded"], "burn": ["burned"]}
LEVEL_HEIGHT_M = 3.0
DEFAULT_LEVELS = 1
CONTEXT_M = 200
MAX_AFFECTED_BUILDINGS = 3000
MAX_CONTEXT_BUILDINGS = 1500
MAX_AFFECTED_LINES = 2500
MAX_CONTEXT_LINES = 1200
MAX_FACILITIES = 400
BUILDING_SIMPLIFY_DEG = 0.000004  # ≈ 0.4 m
LINE_SIMPLIFY_DEG = 0.00001  # ≈ 1 m
HEIGHT_METHOD = (
    f"OSM `height` tag when present; otherwise OSM `building:levels` × {LEVEL_HEIGHT_M:g} m per storey; "
    f"otherwise an estimated default of {DEFAULT_LEVELS} storey × {LEVEL_HEIGHT_M:g} m = {DEFAULT_LEVELS * LEVEL_HEIGHT_M:g} m (height_source = 'estimated_default')."
)
_NUM = re.compile(r"\d+(?:[.,]\d+)?")


def _num(value: str | None) -> float | None:
    m = _NUM.search(value or "")
    return float(m.group().replace(",", ".")) if m else None


def building_height(tags: dict[str, str]) -> dict[str, Any]:
    levels = _num(tags.get("building:levels"))
    levels = levels if levels and 0 < levels < 150 else None
    raw = tags.get("height") or ""
    h = _num(raw)
    if h and ("ft" in raw.lower() or "'" in raw):
        h *= 0.3048
    if h and 0 < h < 500:
        return {"height_m": round(h, 1), "height_source": "osm_height", "levels": levels}
    if levels:
        return {"height_m": round(levels * LEVEL_HEIGHT_M, 1), "height_source": "osm_levels", "levels": levels}
    return {"height_m": DEFAULT_LEVELS * LEVEL_HEIGHT_M, "height_source": "estimated_default", "levels": None}


def _round(coords: Any) -> Any:
    if isinstance(coords, (list, tuple)) and coords and isinstance(coords[0], (int, float)):
        return [round(coords[0], 6), round(coords[1], 6)]
    return [_round(c) for c in coords]


def _geojson(geom) -> dict[str, Any]:
    g = mapping(geom)
    return {"type": g["type"], "coordinates": _round(g["coordinates"])}


def _parts(geom) -> list[Any]:
    return list(getattr(geom, "geoms", [geom]))


class _Index:
    """Spatial index over hazard polygons so per-asset clipping touches only nearby parts."""

    def __init__(self, geom):
        self.parts = [p for p in _parts(geom) if not p.is_empty] if geom is not None and not geom.is_empty else []
        self.tree = STRtree(self.parts) if self.parts else None

    def local(self, geom):
        if self.tree is None:
            return None
        hits = [self.parts[i] for i in self.tree.query(geom, predicate="intersects")]
        return unary_union(hits) if hits else None


def _name(tags: dict[str, str]) -> str | None:
    return tags.get("name") or tags.get("name:en")


def assets(hazard, hazard_type: str, context_water=None) -> dict[str, Any]:
    """Affected (and nearby unaffected) OSM assets as GeoJSON for a 3D view.

    Building `affected` uses the same rule as `assess` (footprint centroid inside the hazard), so
    counts match the loss summary; buildings whose outline only touches the hazard are
    `edge_contact`. Flood depth is not observable from Sentinel-1/2 and is never inferred.
    """
    if hazard is None or hazard.is_empty:
        return {"status": "no_hazard_footprint"}
    w, s, e, n = hazard.bounds
    lat0 = (s + n) / 2
    bbox = _search_bbox(hazard)
    try:
        elements = osm.infrastructure(bbox)
    except SourceUnavailable as exc:
        return {"status": "osm_unavailable", "detail": exc.message}
    deg = CONTEXT_M / 110_570
    near = prep(hazard.buffer(deg, quad_segs=2))
    hz = prep(hazard)
    idx = _Index(hazard)
    water = prep(context_water) if context_water is not None and not context_water.is_empty else None
    area_box = box(*bbox)
    damage = "newly_flooded" if hazard_type == "flood" else "burned"

    cand_aff: list[dict[str, Any]] = []
    cand_ctx: list[dict[str, Any]] = []
    lines: list[dict[str, Any]] = []
    ctx_lines: list[dict[str, Any]] = []
    facilities: list[dict[str, Any]] = []
    totals = Counter()
    for el in elements:
        tags = el.get("tags") or {}
        if "building" in tags and "center" in el and el["type"] == "way":
            c = Point(el["center"]["lon"], el["center"]["lat"])
            if hz.contains(c):
                totals["buildings_affected"] += 1
                cand_aff.append(el)
            elif near.contains(c):
                totals["buildings_nearby"] += 1
                cand_ctx.append(el)
            continue
        pts = el.get("geometry")
        if pts and el["type"] == "way" and ("highway" in tags or "railway" in tags or tags.get("power") == "line"):
            if len(pts) < 2:
                continue
            line = LineString([(p["lon"], p["lat"]) for p in pts])
            if not near.intersects(line):
                continue
            kind = "road" if "highway" in tags else "railway" if "railway" in tags else "power_line"
            props = {"osm_id": f"way/{el['id']}", "kind": kind, "class": tags.get("highway") or tags.get("railway") or "line", "name": _name(tags), "major": tags.get("highway") in MAJOR_ROADS}
            if kind == "power_line" and tags.get("voltage"):
                props["voltage"] = tags["voltage"]
            clipped = line.intersection(area_box)
            local = idx.local(clipped)
            inside = clipped.intersection(local) if local is not None else None
            outside = clipped.difference(local) if local is not None else clipped
            for geom, bucket, affected in ((inside, lines, True), (outside, ctx_lines, False)):
                if geom is None or geom.is_empty:
                    continue
                geom = geom.simplify(LINE_SIMPLIFY_DEG)
                for part in _parts(geom):
                    if part.geom_type != "LineString" or part.is_empty:
                        continue
                    km = _to_km(part, lat0).length
                    totals[f"{kind}_km_{'affected' if affected else 'nearby'}"] += km
                    bucket.append({"type": "Feature", "geometry": _geojson(part), "properties": {**props, "affected": affected, "damage_class": damage if affected else "none", "length_km": round(km, 3)}})
            continue
        kind = _facility_kind(tags)
        if kind:
            c = el.get("center") or ({"lat": el["lat"], "lon": el["lon"]} if "lat" in el else None)
            if not c:
                continue
            p = Point(c["lon"], c["lat"])
            if not near.contains(p):
                continue
            affected = hz.contains(p)
            facilities.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(c["lon"], 6), round(c["lat"], 6)]}, "properties": {"osm_id": f"{el['type']}/{el['id']}", "kind": kind, "name": _name(tags) or kind.replace("_", " "), "affected": affected, "damage_class": damage if affected else "none"}})

    aff, ctx = cand_aff[:MAX_AFFECTED_BUILDINGS], cand_ctx[:MAX_CONTEXT_BUILDINGS]
    try:
        outlines = osm.building_geometries([el["id"] for el in aff + ctx])
    except SourceUnavailable as exc:
        return {"status": "osm_unavailable", "detail": f"Building outlines: {exc.message}"}

    buildings: list[dict[str, Any]] = []
    heights = Counter()
    for el, affected in [(x, True) for x in aff] + [(x, False) for x in ctx]:
        ring = [(p["lon"], p["lat"]) for p in outlines.get(el["id"], []) if p]
        if len(ring) < 4:
            totals["buildings_without_outline"] += 1
            continue
        poly = Polygon(ring)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty or poly.area <= 0:
            totals["buildings_without_outline"] += 1
            continue
        local = idx.local(poly)
        overlap = poly.intersection(local).area / poly.area if local is not None else 0.0
        c = Point(el["center"]["lon"], el["center"]["lat"])
        if affected:
            cls = damage
        elif overlap > 0:
            cls = "edge_contact"
        elif water is not None and water.contains(c):
            cls = "persistent_water"
        else:
            cls = "none"
        tags = el.get("tags") or {}
        h = building_height(tags)
        heights[h["height_source"]] += 1
        footprint = poly.simplify(BUILDING_SIMPLIFY_DEG, preserve_topology=True)
        buildings.append(
            {
                "type": "Feature",
                "geometry": _geojson(footprint),
                "properties": {
                    "osm_id": f"way/{el['id']}",
                    "name": _name(tags),
                    "building": tags.get("building"),
                    **h,
                    "affected": affected,
                    "damage_class": cls,
                    "overlap_pct": round(100 * overlap, 1),
                    "footprint_m2": round(_to_km(poly, lat0).area * 1e6, 1),
                },
            }
        )

    fc = lambda feats: {"type": "FeatureCollection", "features": feats}  # noqa: E731
    return {
        "status": "complete",
        "hazard_type": hazard_type,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "center": [round((w + e) / 2, 6), round((s + n) / 2, 6)],
        "search_bbox": list(bbox),
        "buildings": fc(buildings),
        "lines": fc(lines[:MAX_AFFECTED_LINES] + ctx_lines[:MAX_CONTEXT_LINES]),
        "facilities": fc(facilities[:MAX_FACILITIES]),
        "summary": {
            "buildings_affected": totals["buildings_affected"],
            "buildings_nearby_unaffected": totals["buildings_nearby"],
            "buildings_edge_contact": sum(1 for b in buildings if b["properties"]["damage_class"] == "edge_contact"),
            "buildings_returned": len(buildings),
            "buildings_without_outline": totals["buildings_without_outline"],
            "height_sources": dict(heights),
            "road_km_affected": round(totals["road_km_affected"], 2),
            "railway_km_affected": round(totals["railway_km_affected"], 2),
            "power_line_km_affected": round(totals["power_line_km_affected"], 2),
            "facilities_affected": sum(1 for f in facilities if f["properties"]["affected"]),
        },
        "limits": {
            "max_affected_buildings": MAX_AFFECTED_BUILDINGS,
            "max_context_buildings": MAX_CONTEXT_BUILDINGS,
            "context_radius_m": CONTEXT_M,
            "truncated": len(cand_aff) > len(aff) or len(cand_ctx) > len(ctx) or len(lines) > MAX_AFFECTED_LINES or len(ctx_lines) > MAX_CONTEXT_LINES or len(facilities) > MAX_FACILITIES,
        },
        "method": {
            "affected_rule": "A building is affected when its OSM footprint centroid lies inside the satellite hazard footprint (same rule as the loss summary). Lines are clipped to the footprint; facilities use their point/centroid.",
            "damage_classes": {
                damage: "Inside the mapped hazard footprint" + (" (new water vs baseline)" if hazard_type == "flood" else " (dNBR ≥ 0.27, moderate–high burn severity)"),
                "edge_contact": "Outline overlaps the footprint but centroid lies outside — not counted as affected",
                "persistent_water": "Centroid in water present in both scenes — not counted",
                "none": f"Within {CONTEXT_M} m of the footprint, not affected",
            },
            "height": HEIGHT_METHOD,
            "flood_depth": "Unknown — Sentinel-1/2 map water extent, not depth; extrusion is building height, not water level." if hazard_type == "flood" else None,
        },
        "source": "OpenStreetMap (Overpass API), ODbL",
    }
