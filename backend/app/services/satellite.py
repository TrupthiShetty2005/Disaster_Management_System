"""Real satellite analysis over Karnataka: Sentinel-1 SAR / Sentinel-2 optical flood mapping and
Sentinel-2 burn-scar mapping. All rasters are reprojected to one WGS84 grid, so polygons and areas
are geographically correct."""

from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from rasterio.features import shapes
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

from app.core.config import settings
from app.core.errors import SourceUnavailable
from app.geo import karnataka
from app.geo.karnataka import DISTRICTS_BY_ID, STATIONS_BY_ID
from app.sources import planetary
from app.sources.planetary import S1, S2

MAX_SPAN_DEG = 0.6
SCL_INVALID = {0, 1, 3, 8, 9, 10}  # no-data, saturated, cloud shadow, cloud (medium/high), cirrus
DNBR_CLASSES = ((0.66, "high"), (0.44, "moderate_high"), (0.27, "moderate_low"), (0.10, "low"))


# ---------------------------------------------------------------- areas
def resolve_area(area: dict[str, Any]) -> tuple[str, list[float]]:
    if area.get("district"):
        d = DISTRICTS_BY_ID[area["district"]]
        return f"{d.name} district (around {d.hq})", karnataka.bbox_around(d.latitude, d.longitude, float(area.get("half_deg", 0.15)))
    if area.get("station"):
        s = STATIONS_BY_ID[area["station"]]
        return f"{s.name} ({s.river})", karnataka.bbox_around(s.latitude, s.longitude, float(area.get("half_deg", 0.12)))
    if area.get("bbox"):
        w, s, e, n = (float(v) for v in area["bbox"])
        if e - w > MAX_SPAN_DEG or n - s > MAX_SPAN_DEG or e <= w or n <= s:
            raise ValueError(f"bbox must be a valid box no larger than {MAX_SPAN_DEG}°")
        return str(area.get("name") or "Custom area"), [w, s, e, n]
    if area.get("latitude") is not None and area.get("longitude") is not None:
        half = min(float(area.get("half_deg", 0.08)), MAX_SPAN_DEG / 2)
        return str(area.get("name") or f"Area at {area['latitude']:.3f}, {area['longitude']:.3f}"), karnataka.bbox_around(float(area["latitude"]), float(area["longitude"]), half)
    raise ValueError("area needs district, station, bbox, or latitude+longitude")


def _coverage(items: list[dict[str, Any]], bbox: list[float]) -> float:
    target = box(*bbox)
    geoms = [shape(i["geometry"]) for i in items if i.get("geometry")]
    if not geoms:
        return 0.0
    return round(unary_union(geoms).intersection(target).area / target.area, 3)


def _group(items: list[dict[str, Any]], bbox: list[float]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for it in items:
        orbit = f":{it['orbit_state']}{it['relative_orbit']}" if it["collection"] == S1 else ""
        groups[f"{it['collection']}:{it['date']}{orbit}"].append(it)
    out = []
    for key, members in groups.items():
        clouds = [m["cloud_cover"] for m in members if m.get("cloud_cover") is not None]
        out.append(
            {
                "key": key,
                "collection": members[0]["collection"],
                "sensor": "Sentinel-1 SAR (RTC, VV/VH)" if members[0]["collection"] == S1 else "Sentinel-2 MSI L2A",
                "date": members[0]["date"],
                "datetime": members[0]["datetime"],
                "platform": members[0]["platform"],
                "cloud_cover": round(sum(clouds) / len(clouds), 1) if clouds else None,
                "orbit_state": members[0].get("orbit_state"),
                "relative_orbit": members[0].get("relative_orbit"),
                "item_ids": [m["id"] for m in members],
                "coverage": _coverage(members, bbox),
            }
        )
    out.sort(key=lambda g: g["datetime"], reverse=True)
    return out


def scenes(bbox: list[float], days: int = 120) -> dict[str, Any]:
    tb = tuple(bbox)
    s2 = _group(planetary.recent(S2, tb, days=days, max_cloud=70), bbox)
    s1 = _group(planetary.recent(S1, tb, days=days), bbox)
    return {"bbox": bbox, "sentinel2": s2, "sentinel1": s1, "source": "Microsoft Planetary Computer STAC"}


def _items_for(key: str, bbox: list[float]) -> list[dict[str, Any]]:
    collection, day = key.split(":")[0], key.split(":")[1]
    found = planetary.search(collection, tuple(bbox), day, day)
    groups = {g["key"]: g for g in _group(found, bbox)}
    if key not in groups:
        raise SourceUnavailable("planetary-computer", f"Scene group {key} not found for this area")
    ids = set(groups[key]["item_ids"])
    return [i for i in found if i["id"] in ids]


# ---------------------------------------------------------------- raster helpers
def _pixel_area_km2(bbox: list[float], grid) -> np.ndarray:
    transform, width, height = grid
    lat = bbox[3] + (np.arange(height) + 0.5) * transform.e
    col = (transform.a * 111.32 * np.cos(np.radians(lat))) * (abs(transform.e) * 110.57)
    return np.repeat(col[:, None], width, axis=1)


def _db(linear: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        out = 10 * np.log10(np.where(linear > 0, linear, np.nan))
    return out


def _despeckle(db: np.ndarray) -> np.ndarray:
    filled = np.where(np.isnan(db), -30.0, db).astype("float32")
    smooth = cv2.medianBlur(filled, 5)
    return np.where(np.isnan(db), np.nan, smooth)


def otsu_threshold(values: np.ndarray, lo: float = -24.0, hi: float = -12.0, default: float = -18.0) -> float:
    """Otsu split of the dB histogram, refined to the histogram valley near it (water/land gap)."""
    v = values[np.isfinite(values)]
    v = v[(v > -35) & (v < 5)]
    if v.size < 500:
        return default
    hist, edges = np.histogram(v, bins=240, range=(-35, 5))
    centers = (edges[:-1] + edges[1:]) / 2
    w0 = np.cumsum(hist)
    w1 = w0[-1] - w0
    m0 = np.cumsum(hist * centers) / np.maximum(w0, 1)
    m1 = (np.sum(hist * centers) - np.cumsum(hist * centers)) / np.maximum(w1, 1)
    t = float(centers[int(np.argmax(w0 * w1 * (m0 - m1) ** 2))])
    if not lo <= t <= hi:
        return default
    smooth = np.convolve(hist, np.ones(7) / 7, mode="same")
    near = (centers >= t - 3) & (centers <= t + 1.5)
    valley = float(centers[near][int(np.argmin(smooth[near]))])
    return round(max(lo, min(hi, valley)), 2)


def _clean(mask: np.ndarray, min_px: int = 4) -> np.ndarray:
    m = cv2.morphologyEx(mask.astype("uint8"), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    keep = np.zeros(n, dtype=bool)
    keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= min_px
    return keep[labels]


def _polygons(mask: np.ndarray, grid, cls: str, limit: int = 400) -> list[dict[str, Any]]:
    transform = grid[0]
    tol = abs(transform.a) * 0.8
    geoms = [shape(g).simplify(tol, preserve_topology=True) for g, v in shapes(mask.astype("uint8"), mask=mask, transform=transform) if v == 1]
    geoms = sorted((g for g in geoms if not g.is_empty), key=lambda g: g.area, reverse=True)[:limit]
    return [{"type": "Feature", "properties": {"class": cls}, "geometry": mapping(g)} for g in geoms]


def _rgba_png(rgb: np.ndarray, alpha: np.ndarray) -> bytes:
    bgra = np.dstack([rgb[..., 2], rgb[..., 1], rgb[..., 0], alpha]).astype("uint8")
    ok, buf = cv2.imencode(".png", bgra)
    if not ok:
        raise RuntimeError("PNG encode failed")
    return buf.tobytes()


def _stretch(a: np.ndarray, lo: float, hi: float) -> np.ndarray:
    return (np.clip((a - lo) / (hi - lo), 0, 1) * 255).astype("uint8")


def _sar_png(db: np.ndarray) -> bytes:
    g = _stretch(np.nan_to_num(db, nan=-30), -25, 0)
    return _rgba_png(np.dstack([g, g, g]), np.where(np.isnan(db), 0, 255))


def _index_png(idx: np.ndarray, lo: float, hi: float, cmap: int) -> bytes:
    g = _stretch(np.nan_to_num(idx, nan=lo), lo, hi)
    bgr = cv2.applyColorMap(g, cmap)
    return _rgba_png(bgr[..., ::-1], np.where(np.isnan(idx), 0, 255))


def _change_png(before: np.ndarray, after: np.ndarray, valid: np.ndarray, base: np.ndarray | None = None) -> bytes:
    h, w = before.shape
    rgb = np.zeros((h, w, 3), dtype="uint8")
    if base is not None:
        g = _stretch(np.nan_to_num(base, nan=-30), -25, 0) // 2
        rgb[:] = np.dstack([g, g, g])
    rgb[before & after] = (37, 99, 235)  # persistent water
    rgb[after & ~before] = (239, 68, 68)  # newly flooded
    rgb[before & ~after] = (250, 204, 21)  # receded
    return _rgba_png(rgb, np.where(valid, 255, 0))


def _s2_truecolor(items, bbox, grid) -> tuple[np.ndarray, np.ndarray]:
    bands = [planetary.mosaic(items, "visual", bbox, grid, band=b) for b in (1, 2, 3)]
    rgb = np.dstack([np.nan_to_num(b, nan=0) for b in bands]).astype("uint8")
    return rgb, ~np.isnan(bands[0])


def _s2_mask(items, bbox, grid) -> np.ndarray:
    scl = planetary.mosaic(items, "SCL", bbox, grid, categorical=True)
    bad = np.isnan(scl) | np.isin(np.nan_to_num(scl, nan=0).astype(int), list(SCL_INVALID))
    return ~bad


def _ratio(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        return (a - b) / (a + b)


# ---------------------------------------------------------------- previews
def preview_png(bbox: list[float], key: str, kind: str) -> bytes:
    cache = Path(settings.storage_dir) / "previews" / (hashlib.sha1(f"{bbox}{key}{kind}".encode()).hexdigest() + ".png")
    if cache.is_file():
        return cache.read_bytes()
    items = _items_for(key, bbox)
    grid = planetary.grid_for(bbox)
    if kind == "sar":
        png = _sar_png(_db(planetary.mosaic(items, "vv", bbox, grid)))
    elif kind == "truecolor":
        rgb, valid = _s2_truecolor(items, bbox, grid)
        png = _rgba_png(rgb, np.where(valid, 255, 0))
    elif kind in {"ndwi", "nbr"}:
        b1, b2 = ("B03", "B08") if kind == "ndwi" else ("B08", "B12")
        idx = _ratio(planetary.mosaic(items, b1, bbox, grid), planetary.mosaic(items, b2, bbox, grid))
        idx[~_s2_mask(items, bbox, grid)] = np.nan
        png = _index_png(idx, -0.6, 0.6, cv2.COLORMAP_JET if kind == "ndwi" else cv2.COLORMAP_INFERNO)
    else:
        raise ValueError("kind must be sar, truecolor, ndwi or nbr")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(png)
    return png


# ---------------------------------------------------------------- scene selection
def _pick_after(groups: list[dict[str, Any]], key: str | None, min_cov: float = 0.6, max_cloud: float | None = None) -> dict[str, Any]:
    if key:
        for g in groups:
            if g["key"] == key:
                return g
        raise SourceUnavailable("planetary-computer", f"Scene {key} not available for this area")
    for g in groups:
        if g["coverage"] >= min_cov and (max_cloud is None or (g["cloud_cover"] or 0) <= max_cloud):
            return g
    raise SourceUnavailable("planetary-computer", "No recent scene covers this area well enough")


def _dry_season_window(after_date: str) -> tuple[str, str]:
    d = date.fromisoformat(after_date)
    year = d.year if d.month >= 6 else d.year - 1
    return f"{year}-03-01", f"{year}-05-15"


def _pick_before(collection: str, bbox: list[float], after: dict[str, Any], baseline: str, key: str | None, max_cloud: float | None) -> dict[str, Any]:
    if key:
        found = planetary.search(collection, tuple(bbox), key.split(":")[1], key.split(":")[1])
        return _pick_after(_group(found, bbox), key)
    if baseline == "dry_season":
        start, end = _dry_season_window(after["date"])
        min_gap = 0
    else:
        end = (date.fromisoformat(after["date"]) - timedelta(days=10)).isoformat()
        start = (date.fromisoformat(after["date"]) - timedelta(days=90)).isoformat()
        min_gap = 10
    cands = _group(planetary.search(collection, tuple(bbox), start, end, max_cloud=max_cloud), bbox)
    cands = [g for g in cands if g["coverage"] >= 0.6 and (date.fromisoformat(after["date"]) - date.fromisoformat(g["date"])).days >= min_gap]
    if collection == S1:
        same = [g for g in cands if g["relative_orbit"] == after["relative_orbit"] and g["orbit_state"] == after["orbit_state"]]
        cands = same or cands
    if not cands:
        raise SourceUnavailable("planetary-computer", f"No {baseline.replace('_', ' ')} reference scene found ({start} to {end})")
    return cands[0] if baseline == "previous" else min(cands, key=lambda g: g["cloud_cover"] or 0)


def _scene_meta(g: dict[str, Any]) -> dict[str, Any]:
    return {k: g[k] for k in ("key", "sensor", "date", "datetime", "platform", "cloud_cover", "orbit_state", "relative_orbit", "item_ids", "coverage")}


# ---------------------------------------------------------------- analyses
def flood_analysis(bbox: list[float], method: str = "sar", baseline: str = "dry_season", after_key: str | None = None, before_key: str | None = None) -> dict[str, Any]:
    grid = planetary.grid_for(bbox)
    area_px = _pixel_area_km2(bbox, grid)
    images: dict[str, bytes] = {}
    if method == "sar":
        after = _pick_after(_group(planetary.recent(S1, tuple(bbox), days=60), bbox), after_key)
        before = _pick_before(S1, bbox, after, baseline, before_key, None)
        a_db = _despeckle(_db(planetary.mosaic(_items_for(after["key"], bbox), "vv", bbox, grid)))
        b_db = _despeckle(_db(planetary.mosaic(_items_for(before["key"], bbox), "vv", bbox, grid)))
        valid = np.isfinite(a_db) & np.isfinite(b_db)
        thr = otsu_threshold(np.concatenate([a_db[valid], b_db[valid]]))
        water_a = _clean((a_db < thr) & valid)
        water_b = _clean((b_db < thr) & valid)
        images = {"before.png": _sar_png(b_db), "after.png": _sar_png(a_db)}
        base_layer = a_db
        params = {"vv_threshold_db": thr, "speckle_filter": "median 5x5", "same_orbit": before["relative_orbit"] == after["relative_orbit"]}
        method_text = (
            "Sentinel-1 RTC VV backscatter, 5×5 median despeckle; water = below one threshold for both dates, "
            "found at the water/land valley of the combined histogram (Otsu-initialised, −24…−12 dB)."
        )
    elif method == "optical":
        after = _pick_after(_group(planetary.recent(S2, tuple(bbox), days=60, max_cloud=40), bbox), after_key, max_cloud=40)
        before = _pick_before(S2, bbox, after, baseline, before_key, 20)
        def ndwi(g):
            items = _items_for(g["key"], bbox)
            idx = _ratio(planetary.mosaic(items, "B03", bbox, grid), planetary.mosaic(items, "B08", bbox, grid))
            idx[~_s2_mask(items, bbox, grid)] = np.nan
            return idx
        a_idx, b_idx = ndwi(after), ndwi(before)
        valid = np.isfinite(a_idx) & np.isfinite(b_idx)
        water_a = _clean((a_idx > 0.0) & valid)
        water_b = _clean((b_idx > 0.0) & valid)
        images = {"before.png": _index_png(b_idx, -0.6, 0.6, cv2.COLORMAP_JET), "after.png": _index_png(a_idx, -0.6, 0.6, cv2.COLORMAP_JET)}
        base_layer = None
        params = {"ndwi_threshold": 0.0, "cloud_mask": "Sentinel-2 SCL classes 0,1,3,8,9,10 excluded"}
        method_text = "Sentinel-2 NDWI (B03−B08)/(B03+B08) > 0 with SCL cloud/shadow masking."
    else:
        raise ValueError("method must be 'sar' or 'optical'")

    valid_frac = float(valid.mean())
    if valid_frac < 0.25:
        raise SourceUnavailable("planetary-computer", f"Only {valid_frac:.0%} of the area has valid pixels in both scenes")
    new = water_a & ~water_b
    receded = water_b & ~water_a
    km2 = lambda m: round(float(area_px[m].sum()), 3)  # noqa: E731
    before_km2, after_km2 = km2(water_b), km2(water_a)
    metrics = {
        "method": method_text,
        "parameters": params,
        "valid_coverage_pct": round(100 * valid_frac, 1),
        "analysed_area_km2": round(float(area_px[valid].sum()), 1),
        "water_before_km2": before_km2,
        "water_after_km2": after_km2,
        "newly_flooded_km2": km2(new),
        "receded_km2": km2(receded),
        "water_change_pct": round(100 * (after_km2 - before_km2) / before_km2, 1) if before_km2 > 0 else None,
        "pixel_size_m": round(abs(grid[0].a) * 111320 * math.cos(math.radians((bbox[1] + bbox[3]) / 2)), 1),
        "baseline": baseline,
    }
    images["change.png"] = _change_png(water_b, water_a, valid, base_layer)
    features = _polygons(new, grid, "newly_flooded") + _polygons(water_a & water_b, grid, "persistent_water", limit=150)
    return {
        "before": _scene_meta(before),
        "after": _scene_meta(after),
        "metrics": metrics,
        "geojson": {"type": "FeatureCollection", "features": features},
        "hazard_classes": ["newly_flooded"],
        "images": images,
        "image_bounds": bbox,
    }


def burn_analysis(bbox: list[float], after_key: str | None = None, before_key: str | None = None) -> dict[str, Any]:
    grid = planetary.grid_for(bbox)
    area_px = _pixel_area_km2(bbox, grid)
    after = _pick_after(_group(planetary.recent(S2, tuple(bbox), days=60, max_cloud=40), bbox), after_key, max_cloud=40)
    before = _pick_before(S2, bbox, after, "previous", before_key, 30)

    def nbr(g):
        items = _items_for(g["key"], bbox)
        idx = _ratio(planetary.mosaic(items, "B08", bbox, grid), planetary.mosaic(items, "B12", bbox, grid))
        idx[~_s2_mask(items, bbox, grid)] = np.nan
        return idx, items

    a_nbr, a_items = nbr(after)
    b_nbr, _ = nbr(before)
    valid = np.isfinite(a_nbr) & np.isfinite(b_nbr)
    if valid.mean() < 0.25:
        raise SourceUnavailable("planetary-computer", f"Only {valid.mean():.0%} cloud-free overlap between scenes")
    dnbr = np.where(valid, b_nbr - a_nbr, np.nan)
    classes: dict[str, float] = {}
    upper = np.inf
    for lower, name in DNBR_CLASSES:
        m = valid & (dnbr >= lower) & (dnbr < upper)
        classes[name] = round(float(area_px[m].sum()), 3)
        upper = lower
    burned = _clean(valid & (dnbr >= 0.27))
    rgb, rgb_valid = _s2_truecolor(a_items, bbox, grid)
    overlay = rgb.copy()
    overlay[burned] = (239, 68, 68)
    metrics = {
        "method": "Sentinel-2 dNBR = NBR(before) − NBR(after), NBR = (B08−B12)/(B08+B12); SCL cloud/shadow masked. Severity classes after Key & Benson (USGS).",
        "valid_coverage_pct": round(100 * float(valid.mean()), 1),
        "analysed_area_km2": round(float(area_px[valid].sum()), 1),
        "burned_area_km2": round(float(area_px[burned].sum()), 3),
        "severity_km2": classes,
        "pixel_size_m": round(abs(grid[0].a) * 111320 * math.cos(math.radians((bbox[1] + bbox[3]) / 2)), 1),
        "limitations": "Harvested or ploughed fields can also lower NBR; cross-check with FIRMS detections.",
    }
    return {
        "before": _scene_meta(before),
        "after": _scene_meta(after),
        "metrics": metrics,
        "geojson": {"type": "FeatureCollection", "features": _polygons(burned, grid, "burned")},
        "hazard_classes": ["burned"],
        "images": {
            "before.png": _index_png(b_nbr, -0.5, 0.8, cv2.COLORMAP_VIRIDIS),
            "after.png": _rgba_png(rgb, np.where(rgb_valid, 255, 0)),
            "change.png": _rgba_png(overlay, np.where(rgb_valid, 255, 0)),
        },
        "image_bounds": bbox,
    }
