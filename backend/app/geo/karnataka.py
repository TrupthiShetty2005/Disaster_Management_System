"""Karnataka reference geography.

District headquarters and river/reservoir locations are fixed geographic reference points.
Boundaries are fetched live from OpenStreetMap (Nominatim) and cached on disk.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any

from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry

from app.core import http
from app.core.errors import SourceUnavailable

# west, south, east, north
KARNATAKA_BBOX = (74.0, 11.5, 78.6, 18.5)
NOMINATIM = "https://nominatim.openstreetmap.org/search"


@dataclass(frozen=True)
class District:
    id: str
    name: str
    hq: str
    latitude: float
    longitude: float
    coastal: bool = False


DISTRICTS: tuple[District, ...] = (
    District("bagalkot", "Bagalkot", "Bagalkot", 16.1817, 75.6958),
    District("ballari", "Ballari", "Ballari", 15.1394, 76.9214),
    District("belagavi", "Belagavi", "Belagavi", 15.8497, 74.4977),
    District("bengaluru-rural", "Bengaluru Rural", "Doddaballapura", 13.2923, 77.5381),
    District("bengaluru-urban", "Bengaluru Urban", "Bengaluru", 12.9716, 77.5946),
    District("bidar", "Bidar", "Bidar", 17.9104, 77.5199),
    District("chamarajanagar", "Chamarajanagar", "Chamarajanagar", 11.9261, 76.9437),
    District("chikkaballapur", "Chikkaballapur", "Chikkaballapur", 13.4355, 77.7315),
    District("chikkamagaluru", "Chikkamagaluru", "Chikkamagaluru", 13.3153, 75.7754),
    District("chitradurga", "Chitradurga", "Chitradurga", 14.2251, 76.3980),
    District("dakshina-kannada", "Dakshina Kannada", "Mangaluru", 12.9141, 74.8560, True),
    District("davanagere", "Davanagere", "Davanagere", 14.4644, 75.9218),
    District("dharwad", "Dharwad", "Dharwad", 15.4589, 75.0078),
    District("gadag", "Gadag", "Gadag", 15.4315, 75.6355),
    District("hassan", "Hassan", "Hassan", 13.0068, 76.0996),
    District("haveri", "Haveri", "Haveri", 14.7951, 75.3991),
    District("kalaburagi", "Kalaburagi", "Kalaburagi", 17.3297, 76.8343),
    District("kodagu", "Kodagu", "Madikeri", 12.4244, 75.7382),
    District("kolar", "Kolar", "Kolar", 13.1362, 78.1291),
    District("koppal", "Koppal", "Koppal", 15.3547, 76.1548),
    District("mandya", "Mandya", "Mandya", 12.5218, 76.8951),
    District("mysuru", "Mysuru", "Mysuru", 12.2958, 76.6394),
    District("raichur", "Raichur", "Raichur", 16.2120, 77.3439),
    District("ramanagara", "Ramanagara", "Ramanagara", 12.7209, 77.2799),
    District("shivamogga", "Shivamogga", "Shivamogga", 13.9299, 75.5681),
    District("tumakuru", "Tumakuru", "Tumakuru", 13.3379, 77.1173),
    District("udupi", "Udupi", "Udupi", 13.3409, 74.7421, True),
    District("uttara-kannada", "Uttara Kannada", "Karwar", 14.8136, 74.1290, True),
    District("vijayanagara", "Vijayanagara", "Hosapete", 15.2689, 76.3909),
    District("vijayapura", "Vijayapura", "Vijayapura", 16.8302, 75.7100),
    District("yadgir", "Yadgir", "Yadgir", 16.7700, 77.1376),
)

DISTRICTS_BY_ID = {d.id: d for d in DISTRICTS}


@dataclass(frozen=True)
class RiverStation:
    id: str
    name: str
    river: str
    district_id: str
    latitude: float
    longitude: float
    kind: str  # "dam" | "river"


RIVER_STATIONS: tuple[RiverStation, ...] = (
    RiverStation("almatti", "Almatti Dam", "Krishna", "vijayapura", 16.3306, 75.8875, "dam"),
    RiverStation("narayanpur", "Narayanpur Dam", "Krishna", "yadgir", 16.2105, 76.3540, "dam"),
    RiverStation("hidkal", "Hidkal Dam", "Ghataprabha", "belagavi", 16.1500, 74.6333, "dam"),
    RiverStation("navilutheertha", "Navilutheertha Dam", "Malaprabha", "belagavi", 15.8167, 75.1167, "dam"),
    RiverStation("yadgir-bhima", "Bhima at Yadgir", "Bhima", "yadgir", 16.7600, 77.1300, "river"),
    RiverStation("tungabhadra", "Tungabhadra Dam", "Tungabhadra", "vijayanagara", 15.2650, 76.3330, "dam"),
    RiverStation("shivamogga-tunga", "Tunga at Shivamogga", "Tunga", "shivamogga", 13.9330, 75.5700, "river"),
    RiverStation("bhadra", "Bhadra Dam", "Bhadra", "chikkamagaluru", 13.7000, 75.6400, "dam"),
    RiverStation("linganamakki", "Linganamakki Dam", "Sharavathi", "shivamogga", 14.1750, 74.8500, "dam"),
    RiverStation("kadra", "Kadra Dam", "Kali", "uttara-kannada", 14.9050, 74.3330, "dam"),
    RiverStation("bantwal", "Netravati at Bantwal", "Netravati", "dakshina-kannada", 12.8900, 75.0350, "river"),
    RiverStation("harangi", "Harangi Dam", "Harangi", "kodagu", 12.4920, 75.9050, "dam"),
    RiverStation("gorur", "Hemavathi Dam (Gorur)", "Hemavathi", "hassan", 12.8250, 76.0650, "dam"),
    RiverStation("krs", "Krishna Raja Sagara Dam", "Kaveri", "mandya", 12.4244, 76.5722, "dam"),
    RiverStation("kabini", "Kabini Dam", "Kabini", "mysuru", 11.9725, 76.3500, "dam"),
    RiverStation("shivanasamudra", "Kaveri at Shivanasamudra", "Kaveri", "chamarajanagar", 12.3000, 77.1700, "river"),
)

STATIONS_BY_ID = {s.id: s for s in RIVER_STATIONS}


def district_dicts() -> list[dict[str, Any]]:
    return [asdict(d) for d in DISTRICTS]


def station_dicts() -> list[dict[str, Any]]:
    return [asdict(s) for s in RIVER_STATIONS]


def _nominatim(params: dict[str, str]) -> dict[str, Any] | None:
    rows = http.get_json(
        "nominatim",
        NOMINATIM,
        params={**params, "format": "json", "polygon_geojson": "1", "polygon_threshold": "0.005", "limit": "1"},
    )
    return rows[0] if isinstance(rows, list) and rows else None


@http.ttl_cache(30 * 86400, disk=True)
def karnataka_boundary() -> dict[str, Any]:
    rec = _nominatim({"state": "Karnataka", "country": "India"})
    if not rec or not rec.get("geojson"):
        raise SourceUnavailable("nominatim", "Karnataka boundary not returned by OpenStreetMap Nominatim")
    return {"type": "Feature", "properties": {"name": "Karnataka", "source": "OpenStreetMap Nominatim"}, "geometry": rec["geojson"]}


@http.ttl_cache(30 * 86400, disk=True)
def district_boundaries() -> dict[str, Any]:
    features = []
    for d in DISTRICTS:
        try:
            rec = _nominatim({"q": f"{d.name} district, Karnataka, India"})
        except SourceUnavailable:
            rec = None
        if rec and rec.get("geojson", {}).get("type") in {"Polygon", "MultiPolygon"}:
            features.append({"type": "Feature", "properties": {"id": d.id, "name": d.name}, "geometry": rec["geojson"]})
        time.sleep(1.1)  # Nominatim usage policy: max 1 request/second
    if not features:
        raise SourceUnavailable("nominatim", "No Karnataka district boundaries returned")
    return {"type": "FeatureCollection", "features": features}


@lru_cache(maxsize=1)
def _state_shape() -> BaseGeometry:
    return shape(karnataka_boundary()["geometry"]).buffer(0)


@lru_cache(maxsize=1)
def _district_shapes() -> tuple[tuple[str, BaseGeometry], ...]:
    return tuple((f["properties"]["id"], shape(f["geometry"]).buffer(0)) for f in district_boundaries()["features"])


def in_karnataka(lat: float, lon: float) -> bool:
    w, s, e, n = KARNATAKA_BBOX
    if not (w <= lon <= e and s <= lat <= n):
        return False
    return _state_shape().contains(Point(lon, lat))


def district_for(lat: float, lon: float) -> str:
    """District containing the point (OSM polygons), else the nearest district HQ."""
    p = Point(lon, lat)
    try:
        for did, geom in _district_shapes():
            if geom.contains(p):
                return did
    except SourceUnavailable:
        pass
    return min(DISTRICTS, key=lambda d: (d.latitude - lat) ** 2 + (d.longitude - lon) ** 2).id


def bbox_around(lat: float, lon: float, half_deg: float) -> list[float]:
    return [round(lon - half_deg, 5), round(lat - half_deg, 5), round(lon + half_deg, 5), round(lat + half_deg, 5)]
