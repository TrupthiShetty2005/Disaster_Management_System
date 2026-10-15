"""OpenStreetMap Overpass proxy for Karnataka AOI reference features.

STATIC_EXTERNAL volunteer mapping — not official government infrastructure.
Empty Overpass success means nothing was mapped in OSM for that query, not that
infrastructure is confirmed absent. Timeouts/rate limits are UNAVAILABLE.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.config import settings
from app.core.providers import ProviderUnavailableError

_CACHE: dict[str, Any] = {"ts": 0.0, "payload": None, "key": None}

LAYER_ORDER = (
    "roads",
    "bridges",
    "railways",
    "waterways",
    "buildings",
    "hospitals",
    "fire",
    "shelters",
)

_PER_LAYER_CAP = {
    "roads": 80,
    "bridges": 40,
    "railways": 40,
    "waterways": 50,
    "buildings": 50,
    "hospitals": 40,
    "fire": 20,
    "shelters": 30,
}


def invalidate_gis_cache() -> None:
    _CACHE["payload"] = None
    _CACHE["ts"] = 0.0
    _CACHE["key"] = None


def valid_lonlat(lon: float, lat: float) -> bool:
    if lon != lon or lat != lat:  # NaN
        return False
    return -180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0


def classify_osm_layer(tags: dict[str, Any]) -> str | None:
    amenity = str(tags.get("amenity") or "")
    emergency = str(tags.get("emergency") or "")
    social = str(tags.get("social_facility") or "")
    if amenity in {"hospital", "clinic", "doctors", "pharmacy"} or tags.get("healthcare"):
        return "hospitals"
    if amenity == "fire_station":
        return "fire"
    if amenity == "shelter" or social == "shelter" or emergency in {"assembly_point", "shelter"}:
        return "shelters"
    if tags.get("bridge") in {"yes", "viaduct", "aqueduct"} or tags.get("man_made") == "bridge":
        return "bridges"
    if tags.get("railway") and tags.get("railway") not in {"abandoned", "dismantled"}:
        return "railways"
    if tags.get("waterway"):
        return "waterways"
    if tags.get("building"):
        return "buildings"
    if tags.get("highway"):
        if str(tags.get("highway")) in {"crossing", "traffic_signals"}:
            return "bridges"
        return "roads"
    return None


def geometry_from_osm(el: dict[str, Any]) -> dict[str, Any] | None:
    """Return GeoJSON geometry or None if coordinates are missing/invalid."""
    tags = el.get("tags") or {}
    if "lat" in el and "lon" in el:
        lon, lat = float(el["lon"]), float(el["lat"])
        if not valid_lonlat(lon, lat):
            return None
        return {"type": "Point", "coordinates": [lon, lat]}

    nodes = el.get("geometry")
    if isinstance(nodes, list) and nodes:
        coords: list[list[float]] = []
        for pt in nodes:
            if not isinstance(pt, dict) or "lat" not in pt or "lon" not in pt:
                continue
            lon, lat = float(pt["lon"]), float(pt["lat"])
            if valid_lonlat(lon, lat):
                coords.append([lon, lat])
        if len(coords) >= 4 and coords[0] == coords[-1] and (tags.get("building") or tags.get("amenity")):
            return {"type": "Polygon", "coordinates": [coords]}
        if len(coords) >= 2:
            return {"type": "LineString", "coordinates": coords}
        if len(coords) == 1:
            return {"type": "Point", "coordinates": coords[0]}
        return None

    center = el.get("center")
    if isinstance(center, dict) and "lat" in center and "lon" in center:
        lon, lat = float(center["lon"]), float(center["lat"])
        if valid_lonlat(lon, lat):
            return {"type": "Point", "coordinates": [lon, lat]}
    return None


class GisService:
    name = "osm-overpass"

    def __init__(self) -> None:
        from app.services.geo.aoi import get_aoi
        from app.services.satellite.copernicus_provider import assert_not_kerala_bbox

        aoi = get_aoi()
        self.aoi = aoi
        self.lat = float(aoi["latitude"])
        self.lon = float(aoi["longitude"])
        bbox = aoi.get("bbox") or []
        self.pad = float(aoi.get("bbox_pad_deg") or getattr(settings, "gis_bbox_pad_deg", 0.06) or 0.06)
        self.ttl = int(getattr(settings, "gis_cache_ttl_sec", 3600))
        self.url = getattr(settings, "gis_overpass_url", "https://overpass-api.de/api/interpreter")
        if len(bbox) == 4:
            west, south, east, north = (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
            self._bbox_swn = (south, west, north, east)
            assert_not_kerala_bbox([west, south, east, north])
        else:
            self._bbox_swn = (
                self.lat - self.pad,
                self.lon - self.pad,
                self.lat + self.pad,
                self.lon + self.pad,
            )
            west, south = self.lon - self.pad, self.lat - self.pad
            east, north = self.lon + self.pad, self.lat + self.pad
            assert_not_kerala_bbox([west, south, east, north])

    def _bbox(self) -> tuple[float, float, float, float]:
        return self._bbox_swn

    def _query(self) -> str:
        s, w, n, e = self._bbox()
        return f"""
        [out:json][timeout:12];
        (
          way["highway"~"motorway|trunk|primary|secondary|tertiary|unclassified|residential"]({s},{w},{n},{e});
          way["bridge"="yes"]({s},{w},{n},{e});
          node["highway"="crossing"]({s},{w},{n},{e});
          way["railway"~"rail|light_rail|subway"]({s},{w},{n},{e});
          way["waterway"~"river|canal|stream"]({s},{w},{n},{e});
          way["building"]({s},{w},{n},{e});
          nwr["amenity"~"hospital|clinic|doctors|pharmacy|fire_station|shelter"]({s},{w},{n},{e});
          nwr["healthcare"]({s},{w},{n},{e});
          nwr["emergency"~"assembly_point|shelter"]({s},{w},{n},{e});
          nwr["social_facility"="shelter"]({s},{w},{n},{e});
        );
        out geom 250;
        """.strip()

    def fetch_features(self, *, force: bool = False) -> dict[str, Any]:
        if settings.use_mock_providers:
            raise ProviderUnavailableError(
                "gis",
                "GIS Overpass is disabled in Demo Mode. Operational maps in live mode query OSM; "
                "demo GIS is not substituted into LIVE responses.",
            )
        if not getattr(settings, "gis_overpass_enabled", True):
            raise ProviderUnavailableError(
                "gis",
                "GIS_OVERPASS_ENABLED=false. OSM features are unavailable (not confirmed absence).",
            )

        now = time.time()
        cache_key = tuple(round(x, 5) for x in self._bbox())
        if (
            not force
            and _CACHE["payload"] is not None
            and _CACHE.get("key") == cache_key
            and (now - float(_CACHE["ts"])) < self.ttl
        ):
            payload = dict(_CACHE["payload"])
            age = int(now - float(_CACHE["ts"]))
            payload["cache_hit"] = True
            payload["cache_age_sec"] = age
            payload["freshness"] = "cached_snapshot"
            prov = dict(payload.get("data_provenance") or {})
            prov["cache_age_sec"] = age
            prov["limitations"] = (
                str(prov.get("limitations") or "")
                + f" Serving cached OSM snapshot ({age}s old); not a live field survey."
            )
            payload["data_provenance"] = prov
            return payload

        headers = {
            "User-Agent": "VisionGuardAI/0.1 (research; OSM Overpass client)",
            "Accept": "application/json",
        }
        try:
            response = httpx.post(
                self.url,
                data={"data": self._query()},
                headers=headers,
                timeout=12.0,
            )
        except httpx.TimeoutException as exc:
            stale = _CACHE.get("payload")
            if stale is not None and _CACHE.get("key") == cache_key:
                payload = dict(stale)
                age = int(now - float(_CACHE.get("ts") or now))
                payload["cache_hit"] = True
                payload["cache_age_sec"] = age
                payload["freshness"] = "stale_after_timeout"
                prov = dict(payload.get("data_provenance") or {})
                prov["limitations"] = (
                    str(prov.get("limitations") or "")
                    + " Overpass timed out; serving last cached OSM snapshot. Not a live survey."
                )
                payload["data_provenance"] = prov
                return payload
            raise ProviderUnavailableError(
                "gis",
                "Overpass timed out. OSM features are UNAVAILABLE for this AOI — "
                "this is not evidence that roads, hospitals, or shelters are absent.",
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("gis", f"Overpass network error: {exc}") from exc
        if response.status_code == 429:
            raise ProviderUnavailableError(
                "gis",
                "Overpass rate-limited (HTTP 429). OSM features UNAVAILABLE; no mock catalog inserted.",
            )
        if response.status_code in {502, 504}:
            raise ProviderUnavailableError(
                "gis",
                f"Overpass gateway HTTP {response.status_code}. OSM features UNAVAILABLE.",
            )
        if response.status_code != 200:
            raise ProviderUnavailableError(
                "gis",
                f"Overpass HTTP {response.status_code}. LIVE mode will not substitute demo GIS polygons.",
            )
        try:
            raw = response.json()
        except ValueError as exc:
            raise ProviderUnavailableError("gis", "Overpass returned non-JSON. No mock features inserted.") from exc

        retrieved_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        features, skipped, layer_counts = self._elements_to_features(raw.get("elements") or [], retrieved_at)
        layer_status = {
            layer: (
                "mapped"
                if layer_counts.get(layer, 0) > 0
                else "not_mapped_in_osm_for_this_query"
            )
            for layer in LAYER_ORDER
        }
        payload = {
            "type": "FeatureCollection",
            "features": features,
            "total": len(features),
            "skipped_invalid_geometry": skipped,
            "empty_result": len(features) == 0,
            "cache_hit": False,
            "cache_age_sec": 0,
            "freshness": "fresh_fetch",
            "layer_counts": layer_counts,
            "layer_status": layer_status,
            "data_provenance": {
                "status": "STATIC_EXTERNAL",
                "provider": "OpenStreetMap via Overpass API",
                "license": "ODbL",
                "official_government_data": False,
                "description": (
                    "Volunteer-mapped OSM features for the selected Karnataka AOI. "
                    "Not official government infrastructure, not live incidents, not damage labels."
                ),
                "retrieved_at": retrieved_at,
                "aoi_name": self.aoi.get("aoi_name"),
                "bbox": {
                    "south": self._bbox()[0],
                    "west": self._bbox()[1],
                    "north": self._bbox()[2],
                    "east": self._bbox()[3],
                },
                "limitations": (
                    "OSM completeness varies by mapper coverage. Empty layer means nothing matching "
                    "the query was returned from OSM — not a confirmed absence of infrastructure. "
                    "Ways use OSM node geometry when present. Cached to respect Overpass rate limits."
                ),
            },
        }
        _CACHE["ts"] = now
        _CACHE["payload"] = payload
        _CACHE["key"] = cache_key
        return payload

    def _elements_to_features(
        self, elements: list[dict[str, Any]], retrieved_at: str
    ) -> tuple[list[dict[str, Any]], int, dict[str, int]]:
        features: list[dict[str, Any]] = []
        skipped = 0
        layer_counts = {k: 0 for k in LAYER_ORDER}
        for el in elements:
            if not isinstance(el, dict):
                skipped += 1
                continue
            osm_id = el.get("id")
            if osm_id is None:
                skipped += 1
                continue
            tags = el.get("tags") or {}
            if not isinstance(tags, dict):
                tags = {}
            layer = classify_osm_layer(tags)
            if layer is None:
                continue
            if layer_counts[layer] >= _PER_LAYER_CAP.get(layer, 40):
                continue
            geom = geometry_from_osm(el)
            if geom is None:
                skipped += 1
                continue
            name = (
                tags.get("name")
                or tags.get("amenity")
                or tags.get("highway")
                or tags.get("railway")
                or tags.get("waterway")
                or tags.get("building")
                or "OSM feature"
            )
            layer_counts[layer] += 1
            features.append(
                {
                    "type": "Feature",
                    "geometry": geom,
                    "properties": {
                        "id": f"osm-{el.get('type')}-{osm_id}",
                        "osm_id": osm_id,
                        "osm_type": el.get("type"),
                        "name": name,
                        "layer": layer,
                        "kind": layer,
                        "feature_type": layer,
                        "source": "OpenStreetMap",
                        "retrieved_at": retrieved_at,
                        "tags": {str(k): str(v) for k, v in list(tags.items())[:16]},
                        "description": (
                            "OpenStreetMap (ODbL) volunteer mapping. STATIC_EXTERNAL. "
                            "Not official government infrastructure data."
                        ),
                    },
                }
            )
        return features, skipped, layer_counts
