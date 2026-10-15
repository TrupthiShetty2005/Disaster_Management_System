"""Microsoft Planetary Computer: Sentinel-2 L2A and Sentinel-1 RTC imagery (anonymous SAS access)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_bounds as transform_from_bounds
from rasterio.warp import reproject, transform_bounds
from rasterio.windows import from_bounds as window_from_bounds

from app.core import http
from app.core.config import settings
from app.core.errors import SourceUnavailable

S2 = "sentinel-2-l2a"
S1 = "sentinel-1-rtc"

_GDAL_ENV = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "GDAL_HTTP_MULTIRANGE": "YES",
    "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES",
    "GDAL_HTTP_TIMEOUT": "60",
    "GDAL_HTTP_MAX_RETRY": "3",
}


@http.ttl_cache(1800)
def _token(collection: str) -> str:
    return http.get_json("planetary-computer", f"{settings.planetary_sas_url}/{collection}")["token"]


def signed(href: str, collection: str) -> str:
    return f"{href}?{_token(collection)}"


def recent(collection: str, bbox: tuple[float, ...], days: int = 120, max_cloud: float | None = None, limit: int = 80) -> list[dict[str, Any]]:
    end = date.today() + timedelta(days=1)
    return search(collection, bbox, (end - timedelta(days=days + 1)).isoformat(), end.isoformat(), max_cloud, limit)


@http.ttl_cache(1800)
def search(collection: str, bbox: tuple[float, ...], start: str, end: str, max_cloud: float | None = None, limit: int = 80) -> list[dict[str, Any]]:
    body: dict[str, Any] = {
        "collections": [collection],
        "bbox": list(bbox),
        "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z",
        "limit": limit,
        "sortby": [{"field": "datetime", "direction": "desc"}],
    }
    if max_cloud is not None:
        body["query"] = {"eo:cloud_cover": {"lt": max_cloud}}
    data = http.request("planetary-computer", "POST", f"{settings.planetary_stac_url}/search", json=body, timeout=60.0).json()
    items = []
    for f in data.get("features", []):
        p = f.get("properties", {})
        items.append(
            {
                "id": f["id"],
                "collection": collection,
                "datetime": p.get("datetime"),
                "date": (p.get("datetime") or "")[:10],
                "platform": p.get("platform"),
                "cloud_cover": p.get("eo:cloud_cover"),
                "orbit_state": p.get("sat:orbit_state"),
                "relative_orbit": p.get("sat:relative_orbit"),
                "tile": p.get("s2:mgrs_tile"),
                "geometry": f.get("geometry"),
                "assets": {k: v["href"] for k, v in f.get("assets", {}).items() if "image/tiff" in str(v.get("type", ""))},
            }
        )
    return items


def grid_for(bbox: list[float], max_px: int | None = None) -> tuple[Any, int, int]:
    """WGS84 grid covering bbox; longest side has max_px pixels."""
    max_px = max_px or settings.satellite_max_pixels
    w, s, e, n = bbox
    aspect = (e - w) / max(n - s, 1e-9)
    width, height = (max_px, max(1, round(max_px / aspect))) if aspect >= 1 else (max(1, round(max_px * aspect)), max_px)
    return transform_from_bounds(w, s, e, n, width, height), width, height


def read_to_grid(href: str, collection: str, bbox: list[float], grid: tuple[Any, int, int], *, band: int = 1, categorical: bool = False) -> np.ndarray:
    """Read one band of a COG, clipped to bbox and reprojected onto the shared WGS84 grid. NaN = no data."""
    dst_transform, width, height = grid
    dst = np.full((height, width), np.nan, dtype="float32")
    try:
        with rasterio.Env(**_GDAL_ENV), rasterio.open(signed(href, collection)) as ds:
            native = transform_bounds("EPSG:4326", ds.crs, *bbox, densify_pts=21)
            win = window_from_bounds(*native, ds.transform).round_offsets().round_lengths()
            scale = max(win.width / (width * 1.5), win.height / (height * 1.5), 1.0)
            out_shape = (max(1, int(win.height / scale)), max(1, int(win.width / scale)))
            src = ds.read(band, window=win, out_shape=out_shape, boundless=True, fill_value=0, resampling=Resampling.nearest if categorical else Resampling.average).astype("float32")
            src_transform = ds.window_transform(win) * rasterio.Affine.scale(win.width / out_shape[1], win.height / out_shape[0])
            nodata = ds.nodata if ds.nodata is not None else 0
            src[src == nodata] = np.nan
            reproject(
                source=src,
                destination=dst,
                src_transform=src_transform,
                src_crs=ds.crs,
                dst_transform=dst_transform,
                dst_crs="EPSG:4326",
                src_nodata=np.nan,
                dst_nodata=np.nan,
                resampling=Resampling.nearest if categorical else Resampling.bilinear,
            )
    except rasterio.errors.RasterioError as exc:
        raise SourceUnavailable("planetary-computer", f"Could not read {collection} asset: {exc}") from exc
    return dst


def mosaic(items: list[dict[str, Any]], asset: str, bbox: list[float], grid: tuple[Any, int, int], *, band: int = 1, categorical: bool = False) -> np.ndarray:
    """Combine same-date tiles: first valid pixel wins."""
    out: np.ndarray | None = None
    for item in items:
        href = item["assets"].get(asset)
        if not href:
            continue
        arr = read_to_grid(href, item["collection"], bbox, grid, band=band, categorical=categorical)
        out = arr if out is None else np.where(np.isnan(out), arr, out)
        if not np.isnan(out).any():
            break
    if out is None:
        raise SourceUnavailable("planetary-computer", f"Asset {asset} not present in the selected scenes")
    return out
