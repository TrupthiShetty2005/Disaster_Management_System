"""India / Karnataka administrative lookups from OpenStreetMap (Nominatim + Overpass).

STATIC_EXTERNAL. If a lookup fails, status is UNAVAILABLE — no invented boundaries.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.providers import ProviderUnavailableError
from app.services.geo.aoi import set_aoi

NOMINATIM = "https://nominatim.openstreetmap.org"
HEADERS = {
    "User-Agent": "VisionGuardAI/0.1 (research; disaster-management; local-dev)",
    "Accept": "application/json",
}

_CACHE: dict[str, tuple[float, Any]] = {}
_TTL = 6 * 3600


def _cached(key: str) -> Any | None:
    hit = _CACHE.get(key)
    if not hit:
        return None
    ts, payload = hit
    if time.time() - ts > _TTL:
        return None
    return payload


def _store(key: str, payload: Any) -> Any:
    _CACHE[key] = (time.time(), payload)
    return payload


class RegionAdminService:
    def __init__(self) -> None:
        from app.core.config import settings

        self.overpass_url = getattr(settings, "gis_overpass_url", "https://overpass-api.de/api/interpreter")

    def _nominatim_search(self, params: dict[str, str]) -> list[dict[str, Any]]:
        query = {**params, "format": "json", "addressdetails": "1"}
        try:
            response = httpx.get(NOMINATIM + "/search", params=query, headers=HEADERS, timeout=25.0)
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("nominatim", f"Nominatim request failed: {exc}") from exc
        if response.status_code != 200:
            raise ProviderUnavailableError("nominatim", f"Nominatim HTTP {response.status_code}")
        data = response.json()
        return data if isinstance(data, list) else []

    def india_and_karnataka(self) -> dict[str, Any]:
        cached = _cached("india-ka")
        if cached:
            return cached
        out: dict[str, Any] = {
            "country": "India",
            "primary_state": "Karnataka",
            "source": "OpenStreetMap Nominatim",
            "status": "STATIC_EXTERNAL",
            "india": {"status": "UNAVAILABLE", "geojson": None, "bbox": None},
            "karnataka": {"status": "UNAVAILABLE", "geojson": None, "bbox": None},
        }
        try:
            india = self._nominatim_search(
                {"country": "India", "featureType": "country", "polygon_geojson": "1", "limit": "1"}
            )
            if india:
                rec = india[0]
                out["india"] = {
                    "status": "STATIC_EXTERNAL",
                    "name": rec.get("display_name"),
                    "osm_id": rec.get("osm_id"),
                    "osm_type": rec.get("osm_type"),
                    "bbox": _bbox_from_nominatim(rec),
                    "geojson": rec.get("geojson"),
                    "lat": float(rec.get("lat")),
                    "lon": float(rec.get("lon")),
                }
            ka = self._nominatim_search(
                {
                    "state": "Karnataka",
                    "country": "India",
                    "polygon_geojson": "1",
                    "limit": "1",
                }
            )
            if ka:
                rec = ka[0]
                out["karnataka"] = {
                    "status": "STATIC_EXTERNAL",
                    "name": rec.get("display_name"),
                    "osm_id": rec.get("osm_id"),
                    "osm_type": rec.get("osm_type"),
                    "bbox": _bbox_from_nominatim(rec),
                    "geojson": rec.get("geojson"),
                    "lat": float(rec.get("lat")),
                    "lon": float(rec.get("lon")),
                }
            if out["india"]["status"] == "UNAVAILABLE" and out["karnataka"]["status"] == "UNAVAILABLE":
                out["status"] = "UNAVAILABLE"
                out["description"] = "Nominatim returned no India/Karnataka polygons. No fabricated boundary drawn."
            else:
                out["description"] = "Administrative polygons from OpenStreetMap Nominatim."
        except ProviderUnavailableError as exc:
            out["status"] = "UNAVAILABLE"
            out["description"] = str(exc.message)
        return _store("india-ka", out)

    def karnataka_districts(self) -> dict[str, Any]:
        cached = _cached("ka-districts")
        if cached:
            return cached
        from app.core.config import settings

        if settings.use_mock_providers:
            raise ProviderUnavailableError("gis", "District catalog disabled in Demo Mode.")
        query = """
        [out:json][timeout:50];
        area["ISO3166-2"="IN-KA"]["admin_level"="4"]->.ka;
        rel(area.ka)["boundary"="administrative"]["admin_level"="5"];
        out tags center;
        """.strip()
        try:
            response = httpx.post(
                self.overpass_url,
                data={"data": query},
                headers=HEADERS,
                timeout=55.0,
            )
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("overpass", f"District query failed: {exc}") from exc
        if response.status_code != 200:
            raise ProviderUnavailableError(
                "overpass",
                f"District query HTTP {response.status_code}. No fabricated district list.",
            )
        elements = (response.json() or {}).get("elements") or []
        items: list[dict[str, Any]] = []
        seen: set[str] = set()
        for el in elements:
            tags = el.get("tags") or {}
            name = tags.get("name:en") or tags.get("name")
            if not name or name in seen:
                continue
            seen.add(name)
            center = el.get("center") or {}
            if "lat" not in center:
                continue
            items.append(
                {
                    "name": name,
                    "osm_id": el.get("id"),
                    "latitude": float(center["lat"]),
                    "longitude": float(center["lon"]),
                    "admin_level": tags.get("admin_level"),
                    "wikidata": tags.get("wikidata"),
                }
            )
        items.sort(key=lambda r: r["name"])
        if not items:
            raise ProviderUnavailableError(
                "overpass",
                "No Karnataka districts returned from OSM (admin_level=5). List not invented.",
            )
        payload = {
            "state": "Karnataka",
            "country": "India",
            "source": "OpenStreetMap Overpass (ISO3166-2=IN-KA, admin_level=5)",
            "status": "STATIC_EXTERNAL",
            "total": len(items),
            "items": items,
            "limitations": "OSM completeness varies. District polygons loaded on selection via Nominatim.",
        }
        return _store("ka-districts", payload)

    def select_district(self, name: str, *, pad: float | None = None) -> dict[str, Any]:
        hits = self._nominatim_search(
            {
                "county": name,
                "state": "Karnataka",
                "country": "India",
                "polygon_geojson": "1",
                "limit": "1",
            }
        )
        if not hits:
            hits = self._nominatim_search(
                {
                    "q": f"{name} district Karnataka India",
                    "polygon_geojson": "1",
                    "limit": "1",
                }
            )
        if not hits:
            raise ProviderUnavailableError(
                "nominatim",
                f"No OSM/Nominatim boundary for district '{name}'. Boundary not invented.",
            )
        rec = hits[0]
        lat = float(rec["lat"])
        lon = float(rec["lon"])
        bbox = _bbox_from_nominatim(rec)
        from app.core.config import settings

        pad_v = float(pad if pad is not None else getattr(settings, "gis_bbox_pad_deg", 0.06) or 0.06)
        # Prefer official nominatim bounding box for satellite coverage; pad only if bbox missing.
        if not bbox:
            bbox = [lon - pad_v, lat - pad_v, lon + pad_v, lat + pad_v]
        return set_aoi(
            {
                "country": "India",
                "state": "Karnataka",
                "district": name,
                "aoi_name": f"{name}, Karnataka, India",
                "latitude": lat,
                "longitude": lon,
                "bbox": bbox,
                "bbox_pad_deg": pad_v,
                "boundary_geojson": rec.get("geojson"),
                "source": "OpenStreetMap Nominatim",
                "status": "STATIC_EXTERNAL" if rec.get("geojson") else "UNAVAILABLE",
                "coverage_note": (
                    "District centroid/bbox from Nominatim. Satellite uses bbox; weather uses lat/lon. "
                    "Not an official Survey of India product."
                    if rec.get("geojson")
                    else "Point found but polygon missing — no fabricated outline."
                ),
                "osm_id": rec.get("osm_id"),
                "display_name": rec.get("display_name"),
            }
        )


def _bbox_from_nominatim(rec: dict[str, Any]) -> list[float] | None:
    raw = rec.get("boundingbox")
    if not raw or len(raw) != 4:
        return None
    # Nominatim: south, north, west, east
    south, north, west, east = (float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3]))
    return [west, south, east, north]
