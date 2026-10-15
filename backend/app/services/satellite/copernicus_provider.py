"""Copernicus Data Space STAC provider for Sentinel-2 metadata + genuine thumbnails."""

from __future__ import annotations

import hashlib
import time
import uuid
from datetime import date, datetime, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.core.providers import ProviderUnavailableError
from app.services.satellite.models import SatelliteScene

SATELLITE_MIN_START = date(2026, 5, 1)
_STAC_TTL_SEC = 300.0
_STAC_BACKOFF_SEC = 120.0
_STAC_CACHE: dict[str, Any] = {
    "key": None,
    "scenes": None,
    "ts": 0.0,
    "backoff_until": 0.0,
}


def clear_stac_catalogue_cache() -> None:
    _STAC_CACHE["key"] = None
    _STAC_CACHE["scenes"] = None
    _STAC_CACHE["ts"] = 0.0
    _STAC_CACHE["backoff_until"] = 0.0

# Central/south Kerala (Kuttanad demo ~9.52N, 76.52E). Karnataka districts sit north of ~11.5N.
_KERALA_LAT = (8.0, 11.2)
_KERALA_LON = (74.85, 77.45)


def _stable_id(stac_id: str) -> str:
    digest = hashlib.md5(stac_id.encode("utf-8")).hexdigest()
    return str(uuid.UUID(digest))


def _bbox_polygon(bbox: list[float]) -> dict:
    minx, miny, maxx, maxy = bbox
    return {
        "type": "Polygon",
        "coordinates": [[[minx, miny], [maxx, miny], [maxx, maxy], [minx, maxy], [minx, miny]]],
    }


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    text = value.replace("Z", "+00:00")
    return datetime.fromisoformat(text)


def bbox_centroid(bbox: list[float]) -> tuple[float, float]:
    west, south, east, north = (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
    return ((west + east) / 2.0, (south + north) / 2.0)


def bboxes_intersect(a: list[float], b: list[float], *, eps: float = 1e-9) -> bool:
    if len(a) < 4 or len(b) < 4:
        return False
    aw, aso, ae, an = (float(a[0]), float(a[1]), float(a[2]), float(a[3]))
    bw, bso, be, bn = (float(b[0]), float(b[1]), float(b[2]), float(b[3]))
    if ae < aw:
        aw, ae = ae, aw
    if an < aso:
        aso, an = an, aso
    if be < bw:
        bw, be = be, bw
    if bn < bso:
        bso, bn = bn, bso
    return not (ae + eps < bw or be + eps < aw or an + eps < bso or bn + eps < aso)


def geometry_bbox(geometry: dict | None) -> list[float] | None:
    if not isinstance(geometry, dict):
        return None
    coords = geometry.get("coordinates")
    if not coords:
        return None
    lons: list[float] = []
    lats: list[float] = []

    def _walk(node) -> None:
        if isinstance(node, (list, tuple)) and len(node) >= 2 and isinstance(node[0], (int, float)):
            lons.append(float(node[0]))
            lats.append(float(node[1]))
            return
        if isinstance(node, (list, tuple)):
            for child in node:
                _walk(child)

    _walk(coords)
    if not lons or not lats:
        return None
    return [min(lons), min(lats), max(lons), max(lats)]


def stac_scene_bbox(feature: dict) -> list[float] | None:
    raw = feature.get("bbox")
    if isinstance(raw, (list, tuple)) and len(raw) >= 4:
        try:
            return [float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3])]
        except (TypeError, ValueError):
            pass
    return geometry_bbox(feature.get("geometry") if isinstance(feature.get("geometry"), dict) else None)


def feature_intersects_aoi(feature: dict, aoi_bbox: list[float]) -> bool:
    scene_bbox = stac_scene_bbox(feature)
    if scene_bbox is None:
        return False
    return bboxes_intersect(scene_bbox, aoi_bbox)


def is_kerala_demo_bbox(bbox: list[float]) -> bool:
    lon, lat = bbox_centroid(bbox)
    return _KERALA_LAT[0] <= lat <= _KERALA_LAT[1] and _KERALA_LON[0] <= lon <= _KERALA_LON[1]


def assert_not_kerala_bbox(bbox: list[float]) -> None:
    if is_kerala_demo_bbox(bbox):
        raise ProviderUnavailableError(
            "copernicus",
            "Refusing Kerala/Kuttanad bounding box. Select a Karnataka district or AOI in India.",
        )


def resolve_search_window(
    start: date | None = None,
    end: date | None = None,
    *,
    today: date | None = None,
) -> tuple[date, date]:
    today = today or datetime.now(timezone.utc).date()
    start_d = start or SATELLITE_MIN_START
    end_d = end or today
    if start_d < SATELLITE_MIN_START:
        raise ValueError(
            f"Start date cannot be before {SATELLITE_MIN_START.isoformat()} "
            "(default analysis period for this deployment)."
        )
    if end_d < start_d:
        raise ValueError("End date must be on or after the start date.")
    if end_d > today:
        raise ValueError("End date cannot be in the future. Sentinel acquisitions are not real-time.")
    return start_d, end_d


def stac_datetime_range(start_d: date, end_d: date) -> str:
    return f"{start_d.isoformat()}T00:00:00Z/{end_d.isoformat()}T23:59:59Z"


def _asset_auth_required(href: str, key: str) -> bool:
    h = href.lower()
    k = key.lower()
    if k in {"thumbnail", "preview", "rendered_preview"} or "thumbnail" in h or "preview" in h:
        return False
    if "odata" in h or "catalogue.dataspace" in h or "zipper" in h:
        return True
    return True


def classify_assets(assets: dict[str, Any]) -> dict[str, Any]:
    classified: dict[str, Any] = {}
    for key, asset in (assets or {}).items():
        if not isinstance(asset, dict):
            continue
        href = str(asset.get("href") or "")
        if not href:
            continue
        role = "other"
        lk = key.lower()
        if lk in {"thumbnail", "preview", "rendered_preview"}:
            role = "preview"
        elif lk in {"visual", "tci", "overview"}:
            role = "visual_raster"
        elif lk.startswith("b") or lk in {"product", "data"}:
            role = "downloadable_raster"
        auth = _asset_auth_required(href, key)
        classified[key] = {
            "href": href,
            "type": asset.get("type") or asset.get("media_type"),
            "role": role,
            "auth_required": auth,
            "downloaded": False,
        }
    return classified


def pick_preview_href(assets: dict[str, Any]) -> tuple[str, bool]:
    classified = classify_assets(assets)
    for key in ("thumbnail", "preview", "rendered_preview"):
        item = classified.get(key)
        if item:
            return str(item["href"]), bool(item["auth_required"])
    for item in classified.values():
        if item.get("role") == "preview":
            return str(item["href"]), bool(item["auth_required"])
    return "", True


def build_search_body(
    *,
    collections: list[str],
    bbox: list[float],
    start_d: date,
    end_d: date,
    limit: int = 12,
    max_cloud: float | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "collections": collections,
        "bbox": bbox,
        "datetime": stac_datetime_range(start_d, end_d),
        "limit": limit,
        "sortby": [{"field": "properties.datetime", "direction": "desc"}],
    }
    if max_cloud is not None and any("sentinel-2" in c for c in collections):
        body["filter-lang"] = "cql2-text"
        body["filter"] = f"eo:cloud_cover < {max_cloud}"
    return body


class CopernicusStacProvider:
    """Sentinel-2 catalogue via CDSE STAC for the selected India/Karnataka AOI.

    Acquisition dates are scene timestamps, not a real-time video feed.
    """

    name = "copernicus-stac"
    live = True

    def __init__(self) -> None:
        self.stac_url = settings.copernicus_stac_url.rstrip("/")
        self._scenes: list[SatelliteScene] | None = None
        self._by_id: dict[str, SatelliteScene] = {}
        self._token: str | None = None
        self._cache_key: tuple | None = None

    def _aoi(self):
        from app.services.geo.aoi import get_aoi

        return get_aoi()

    @property
    def lat(self) -> float:
        return float(self._aoi()["latitude"])

    @property
    def lon(self) -> float:
        return float(self._aoi()["longitude"])

    def _aoi_bbox(self, pad: float = 0.06) -> list[float]:
        aoi = self._aoi()
        bbox = aoi.get("bbox")
        if bbox and len(bbox) == 4:
            out = [float(x) for x in bbox]
        else:
            out = [self.lon - pad, self.lat - pad, self.lon + pad, self.lat + pad]
        assert_not_kerala_bbox(out)
        return out

    def _oauth_token(self) -> str | None:
        if not (settings.copernicus_client_id and settings.copernicus_client_secret):
            return None
        if self._token:
            return self._token
        try:
            response = httpx.post(
                settings.copernicus_token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.copernicus_client_id,
                    "client_secret": settings.copernicus_client_secret,
                },
                timeout=20.0,
            )
        except httpx.HTTPError:
            return None
        if response.status_code != 200:
            return None
        token = response.json().get("access_token")
        if token:
            self._token = str(token)
        return self._token

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        token = self._oauth_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _search(
        self,
        collections: list[str],
        *,
        start_d: date,
        end_d: date,
        limit: int = 12,
        max_cloud: float | None = None,
    ) -> list[dict]:
        bbox = self._aoi_bbox()
        body = build_search_body(
            collections=collections,
            bbox=bbox,
            start_d=start_d,
            end_d=end_d,
            limit=limit,
            max_cloud=max_cloud,
        )
        try:
            response = httpx.post(
                f"{self.stac_url}/search",
                json=body,
                headers=self._headers(),
                timeout=45.0,
            )
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("copernicus", f"Network error during STAC search: {exc}") from exc
        if response.status_code != 200 and max_cloud is not None:
            body.pop("filter", None)
            body.pop("filter-lang", None)
            try:
                response = httpx.post(
                    f"{self.stac_url}/search",
                    json=body,
                    headers=self._headers(),
                    timeout=45.0,
                )
            except httpx.HTTPError as exc:
                raise ProviderUnavailableError("copernicus", f"Network error during STAC search: {exc}") from exc
        if response.status_code != 200:
            raise ProviderUnavailableError(
                "copernicus", f"STAC HTTP {response.status_code}: {response.text[:200]}"
            )
        features = response.json().get("features") or []
        aoi_bbox = bbox
        features = [f for f in features if feature_intersects_aoi(f, aoi_bbox)]
        if max_cloud is not None:
            filtered = [
                f
                for f in features
                if float((f.get("properties") or {}).get("eo:cloud_cover") or 0) <= max_cloud
            ]
            if not filtered and features:
                raise ProviderUnavailableError(
                    "copernicus",
                    f"Scenes found but all exceed max cloud cover {max_cloud}%. "
                    "Widen the date range or raise the cloud threshold.",
                )
            return filtered
        return features

    def _feature_to_scene(self, feature: dict, *, kind: str) -> SatelliteScene | None:
        props = feature.get("properties") or {}
        assets = feature.get("assets") or {}
        stac_id = str(feature.get("id") or "")
        if not stac_id:
            return None
        aoi_bbox = self._aoi_bbox()
        scene_bbox = stac_scene_bbox(feature)
        if scene_bbox is None or not bboxes_intersect(scene_bbox, aoi_bbox):
            return None
        geom = feature.get("geometry") if isinstance(feature.get("geometry"), dict) else None
        footprint = geom or _bbox_polygon(scene_bbox)
        lon, lat = bbox_centroid(scene_bbox)
        thumb, thumb_auth = pick_preview_href(assets)
        classified = classify_assets(assets)
        db_id = _stable_id(stac_id)
        cloud = float(props.get("eo:cloud_cover") or 0)
        platform = str(props.get("platform") or props.get("constellation") or "sentinel")
        acquired = _parse_dt(props.get("datetime"))
        collection = (feature.get("collection") or "").lower()
        source = "sentinel-2" if "sentinel-2" in collection or kind.startswith("s2") else "sentinel-1"
        preview_ok = bool(thumb) and not thumb_auth
        if thumb and thumb_auth:
            status = "auth_required"
        elif thumb:
            status = "preview_available"
        else:
            status = "catalogue_only"
        aoi = self._aoi()
        title = f"{platform.upper()} · {acquired.date().isoformat()} · cloud {cloud:.1f}%"
        image_url = f"/api/v1/satellite/images/{db_id}/preview" if preview_ok or thumb else ""
        return SatelliteScene(
            id=db_id,
            title=title,
            source=source,
            acquisition_time=acquired,
            latitude=lat,
            longitude=lon,
            bounding_box=footprint,
            resolution="10m" if source == "sentinel-2" else "SAR",
            cloud_cover=cloud,
            image_url=image_url,
            thumbnail_url=image_url,
            location_id=str(aoi.get("district") or aoi.get("aoi_name") or ""),
            scene_kind=kind,
            status=status,
            metadata={
                "layer": "catalogue",
                "stac_id": stac_id,
                "collection": feature.get("collection"),
                "platform": platform,
                "thumbnail_href": thumb,
                "preview_available": bool(thumb),
                "preview_auth_required": thumb_auth and bool(thumb),
                "assets": classified,
                "full_raster_downloaded": False,
                "processed_analysis": False,
                "data_label": "Latest available Sentinel catalogue (not real-time)",
                "live_stream": False,
                "provider": "Copernicus Data Space Ecosystem STAC",
                "aoi_name": aoi.get("aoi_name"),
                "aoi_bbox": aoi_bbox,
                "aoi_latitude": float(aoi.get("latitude")),
                "aoi_longitude": float(aoi.get("longitude")),
                "scene_bbox": scene_bbox,
                "scene_centroid_latitude": lat,
                "scene_centroid_longitude": lon,
                "footprint_available": True,
                "intersects_selected_aoi": True,
                "note": (
                    "Catalogue item from CDSE STAC. Preview is the STAC thumbnail when publicly fetchable. "
                    "Downloadable rasters typically require Copernicus OAuth and are not fetched unless configured. "
                    "latitude/longitude are the scene footprint centroid, not the selected AOI center."
                ),
            },
        )

    def refresh(
        self,
        *,
        start: date | None = None,
        end: date | None = None,
        max_cloud: float | None = None,
    ) -> list[SatelliteScene]:
        start_d, end_d = resolve_search_window(start, end)
        cloud = settings.copernicus_max_cloud if max_cloud is None else max_cloud
        s2 = self._search(
            ["sentinel-2-l2a"],
            start_d=start_d,
            end_d=end_d,
            limit=12,
            max_cloud=cloud,
        )
        scenes: list[SatelliteScene] = []
        for i, feature in enumerate(s2[:8]):
            kind = "flood" if i == 0 else ("flood_before" if i == 1 else "normal")
            scene = self._feature_to_scene(feature, kind=kind)
            if scene:
                scenes.append(scene)
        if not scenes:
            aoi = self._aoi()
            raise ProviderUnavailableError(
                "copernicus",
                "No Sentinel-2 scenes found for "
                f"{aoi.get('aoi_name') or 'the selected AOI'} "
                f"between {start_d.isoformat()} and {end_d.isoformat()}. "
                "Try another district, a wider date range, or a higher cloud threshold. "
                "Imagery is latest-available archive, not a live stream.",
            )
        self._scenes = scenes
        self._by_id = {s.id: s for s in scenes}
        return scenes

    def list_scenes(
        self,
        start: date | None = None,
        end: date | None = None,
        max_cloud: float | None = None,
    ) -> list[SatelliteScene]:
        key = (
            tuple(round(x, 5) for x in self._aoi_bbox()),
            start.isoformat() if start else "",
            end.isoformat() if end else "",
            float(max_cloud) if max_cloud is not None else float(settings.copernicus_max_cloud),
        )
        now = time.time()
        cached = _STAC_CACHE.get("scenes")
        same_key = _STAC_CACHE.get("key") == key
        if cached and same_key and now < float(_STAC_CACHE.get("backoff_until") or 0):
            self._scenes = cached
            self._by_id = {s.id: s for s in cached}
            self._cache_key = key
            return cached
        if cached and same_key and (now - float(_STAC_CACHE.get("ts") or 0)) < _STAC_TTL_SEC:
            self._scenes = cached
            self._by_id = {s.id: s for s in cached}
            self._cache_key = key
            return cached
        try:
            scenes = self.refresh(start=start, end=end, max_cloud=max_cloud)
        except ProviderUnavailableError as exc:
            msg = str(exc.message if hasattr(exc, "message") else exc)
            if cached and same_key and ("429" in msg or "Rate limit" in msg):
                _STAC_CACHE["backoff_until"] = now + _STAC_BACKOFF_SEC
                self._scenes = cached
                self._by_id = {s.id: s for s in cached}
                return cached
            raise
        _STAC_CACHE["key"] = key
        _STAC_CACHE["scenes"] = scenes
        _STAC_CACHE["ts"] = now
        _STAC_CACHE["backoff_until"] = 0.0
        self._cache_key = key
        return scenes

    def get_scene(self, scene_id: str) -> SatelliteScene | None:
        if self._scenes is None:
            self.refresh()
        return self._by_id.get(scene_id)

    def scene_kind(self, scene_id: str) -> str:
        scene = self.get_scene(scene_id)
        return scene.scene_kind if scene else "normal"

    def fetch_thumbnail_bytes(self, scene_id: str) -> bytes:
        scene = self.get_scene(scene_id)
        if not scene:
            raise ProviderUnavailableError("copernicus", "Scene not found in the current catalogue query.")
        href = (scene.metadata or {}).get("thumbnail_href")
        if not href:
            raise ProviderUnavailableError(
                "copernicus",
                "No preview thumbnail on this STAC item. Catalogue metadata only — "
                "no image was generated or substituted.",
            )
        if (scene.metadata or {}).get("preview_auth_required") and not self._oauth_token():
            raise ProviderUnavailableError(
                "copernicus",
                "Copernicus OAuth is required for this preview asset. "
                "Set COPERNICUS_CLIENT_ID and COPERNICUS_CLIENT_SECRET. "
                "The asset was not downloaded.",
            )
        headers = self._headers()
        try:
            response = httpx.get(href, headers=headers, timeout=90.0, follow_redirects=True)
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("copernicus", f"Network error fetching preview: {exc}") from exc
        if response.status_code in {401, 403}:
            raise ProviderUnavailableError(
                "copernicus",
                f"Preview HTTP {response.status_code}: authentication required for this asset. "
                "Configure Copernicus OAuth. The asset was not downloaded.",
            )
        if response.status_code != 200 or not response.content:
            raise ProviderUnavailableError(
                "copernicus",
                f"Preview unavailable (HTTP {response.status_code}). No substitute image was used.",
            )
        return response.content

    def status(self) -> dict:
        cached = _STAC_CACHE.get("scenes") or self._scenes
        if cached:
            return {
                "provider": self.name,
                "available": True,
                "scene_count": len(cached),
                "oauth_configured": bool(settings.copernicus_client_id and settings.copernicus_client_secret),
                "live_stream": False,
                "note": "STAC catalogue for selected AOI (cached list); genuine thumbnails only when the asset fetches.",
            }
        try:
            scenes = self.list_scenes()
            return {
                "provider": self.name,
                "available": True,
                "scene_count": len(scenes),
                "oauth_configured": bool(settings.copernicus_client_id and settings.copernicus_client_secret),
                "live_stream": False,
                "note": "STAC catalogue for selected AOI; genuine thumbnails only when the asset fetches.",
            }
        except (ProviderUnavailableError, ValueError) as exc:
            message = exc.message if isinstance(exc, ProviderUnavailableError) else str(exc)
            return {
                "provider": self.name,
                "available": False,
                "scene_count": 0,
                "oauth_configured": bool(settings.copernicus_client_id and settings.copernicus_client_secret),
                "live_stream": False,
                "note": message,
            }
