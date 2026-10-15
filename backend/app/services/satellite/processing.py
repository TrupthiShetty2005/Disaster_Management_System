"""Demo raster generation and baseline detectors. Replace masks with trained models later."""

from __future__ import annotations

from typing import Any

import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

try:
    import rasterio
    from rasterio.transform import from_bounds
except ImportError:  # pragma: no cover
    rasterio = None
    from_bounds = None


SCENE_KINDS = ("normal", "flood", "flood_before", "burn", "urban", "vegetation", "landslide")


def generate_demo_raster(kind: str, size: int = 48) -> np.ndarray:
    """Synthetic RGB scene (not copyrighted imagery)."""
    rgb = np.zeros((size, size, 3), dtype=np.uint8)
    yy, xx = np.mgrid[0:size, 0:size]
    if kind in {"normal", "flood_before"}:
        rgb[..., 1] = 90
        rgb[..., 0] = 40
        rgb[..., 2] = 35
        water = (xx < size * 0.18) & (yy > size * 0.4)
        rgb[water] = (30, 60, 160)
    elif kind == "flood":
        rgb[..., 1] = 70
        rgb[..., 0] = 35
        rgb[..., 2] = 30
        water = (xx < size * 0.55) | ((yy > size * 0.35) & (xx < size * 0.7))
        rgb[water] = (25, 55, 175)
    elif kind == "burn":
        rgb[..., :] = 50
        rgb[..., 0] = 90
        burn = (xx - size * 0.5) ** 2 + (yy - size * 0.45) ** 2 < (size * 0.22) ** 2
        rgb[burn] = (70, 25, 15)
        rgb[yy > size * 0.75] = (35, 80, 30)
    elif kind == "urban":
        rgb[..., :] = 110
        rgb[(xx // 6 + yy // 6) % 2 == 0] = (130, 130, 125)
        rgb[yy > size * 0.85] = (40, 90, 40)
    elif kind == "vegetation":
        rgb[..., 1] = 140
        rgb[..., 0] = 30
        rgb[..., 2] = 25
        rgb[(xx + yy) % 11 == 0] = (20, 70, 20)
    elif kind == "landslide":
        rgb[..., 1] = 80
        rgb[..., 0] = 90
        rgb[..., 2] = 40
        scar = (np.abs(xx - yy) < 4) & (yy > size * 0.2) & (yy < size * 0.8)
        rgb[scar] = (140, 110, 70)
    else:
        rgb[..., 1] = 80
    return rgb


def preprocess(rgb: np.ndarray) -> np.ndarray:
    arr = np.clip(rgb.astype(np.float32), 0, 255)
    if cv2 is not None:
        blur = cv2.GaussianBlur(arr, (3, 3), 0)
        return np.clip(blur, 0, 255).astype(np.uint8)
    return rgb


def _channel_mask(rgb: np.ndarray, fn) -> np.ndarray:
    r, g, b = rgb[..., 0].astype(np.int16), rgb[..., 1].astype(np.int16), rgb[..., 2].astype(np.int16)
    return fn(r, g, b)


def detect_water(rgb: np.ndarray) -> np.ndarray:
    """Legacy blue-channel heuristic tuned for synthetic demo rasters."""
    rgb = preprocess(rgb)
    return _channel_mask(rgb, lambda r, g, b: (b > r + 40) & (b > g + 25) & (b > 100))


def detect_water_sentinel_rgb(rgb: np.ndarray) -> np.ndarray:
    """Heuristic water mask for true-color Sentinel-2 previews (RGB only, no NIR band).

    Combines:
    - dark surface detection (typical open water in true color)
    - blue/green dominance vs red
    - green-red NDWI proxy
    followed by morphological cleanup when OpenCV is available.
    Not a trained semantic segmentation model.
    """
    if rgb.ndim != 3 or rgb.shape[2] < 3:
        raise ValueError("RGB image required for Sentinel water detection")
    work = preprocess(rgb).astype(np.float32)
    r, g, b = work[..., 0], work[..., 1], work[..., 2]
    intensity = (r + g + b) / 3.0
    # Avoid divide-by-zero for index terms.
    eps = 1.0
    ndwi_proxy = (g - r) / (g + r + eps)
    blue_dom = (b - r) / (b + r + eps)
    # Water in true-color previews is often dark and relatively blue/cyan.
    dark = intensity < 95
    blueish = (b > r + 8) & (b >= g - 5)
    wet_index = (ndwi_proxy > 0.05) | (blue_dom > 0.08)
    mask = dark & (blueish | wet_index)
    # Also catch brighter turbid water common in wetlands.
    turbid = (intensity < 140) & (b > r + 15) & (g > r + 5) & (b > 60)
    mask = mask | turbid
    if cv2 is not None:
        binary = (mask.astype(np.uint8) * 255)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
        # Drop tiny speckles.
        n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
        cleaned = np.zeros_like(binary)
        min_area = max(12, int(0.0005 * binary.shape[0] * binary.shape[1]))
        for label in range(1, n_labels):
            if stats[label, cv2.CC_STAT_AREA] >= min_area:
                cleaned[labels == label] = 255
        mask = cleaned > 0
    return mask


def detect_vegetation(rgb: np.ndarray) -> np.ndarray:
    rgb = preprocess(rgb)
    return _channel_mask(rgb, lambda r, g, b: (g > r + 20) & (g > b + 20) & (g > 70))


def detect_burned(rgb: np.ndarray) -> np.ndarray:
    rgb = preprocess(rgb)
    return _channel_mask(rgb, lambda r, g, b: (r > g + 15) & (r > b + 20) & (r < 120) & (g < 50))


def detect_urban(rgb: np.ndarray) -> np.ndarray:
    rgb = preprocess(rgb)
    return _channel_mask(
        rgb,
        lambda r, g, b: (np.abs(r.astype(np.int16) - g) < 18)
        & (np.abs(g.astype(np.int16) - b) < 18)
        & (r > 90)
        & (r < 160),
    )


def mask_ratio(mask: np.ndarray) -> float:
    return float(mask.mean()) if mask.size else 0.0


WATER_CHANGE_LABEL = "Satellite-derived water-change indication — requires validation"
HEURISTIC_METHOD = (
    "OpenCV/NumPy RGB water heuristic on Sentinel-2 true-color previews "
    "(not a trained flood-segmentation model; not a validated flood boundary)"
)


def _aoi_polygon_or_none() -> dict | None:
    try:
        from app.services.geo.aoi import get_aoi
        from app.services.satellite.copernicus_provider import _bbox_polygon

        bbox = get_aoi().get("bbox")
        if bbox and len(bbox) == 4:
            return _bbox_polygon([float(x) for x in bbox])
    except Exception:  # noqa: BLE001
        return None
    return None


def bbox_area_km2(bbox: dict | None, default: float = 64.0) -> float:
    if not bbox or bbox.get("type") != "Polygon":
        aoi = _aoi_polygon_or_none()
        if aoi:
            bbox = aoi
        else:
            return default
    ring = bbox["coordinates"][0]
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    # rough equirectangular km
    dlon = (max(lons) - min(lons)) * 111.32 * np.cos(np.radians(sum(lats) / len(lats)))
    dlat = (max(lats) - min(lats)) * 110.57
    return abs(float(dlon * dlat))


def mask_to_geojson(mask: np.ndarray, bbox: dict | None, name: str) -> dict[str, Any]:
    h, w = mask.shape
    if bbox and bbox.get("type") == "Polygon":
        ring = bbox["coordinates"][0]
        minx, maxx = min(p[0] for p in ring), max(p[0] for p in ring)
        miny, maxy = min(p[1] for p in ring), max(p[1] for p in ring)
    else:
        aoi = _aoi_polygon_or_none()
        if aoi and aoi.get("type") == "Polygon":
            ring = aoi["coordinates"][0]
            minx, maxx = min(p[0] for p in ring), max(p[0] for p in ring)
            miny, maxy = min(p[1] for p in ring), max(p[1] for p in ring)
        else:
            # Karnataka / Bengaluru default — never the Kerala demo box.
            minx, miny, maxx, maxy = 77.53, 12.91, 77.65, 13.03
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return {"type": "FeatureCollection", "features": []}
    x0, x1 = xs.min() / w, (xs.max() + 1) / w
    y0, y1 = ys.min() / h, (ys.max() + 1) / h
    west = minx + (maxx - minx) * x0
    east = minx + (maxx - minx) * x1
    south = maxy - (maxy - miny) * y1
    north = maxy - (maxy - miny) * y0
    poly = {
        "type": "Polygon",
        "coordinates": [[[west, south], [east, south], [east, north], [west, north], [west, south]]],
    }
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": poly,
                "properties": {"name": name, "pixel_fraction": round(mask_ratio(mask), 4)},
            }
        ],
    }


def cloud_mask_rgb(rgb: np.ndarray) -> np.ndarray:
    """Bright near-white pixels treated as cloud/haze on true-color previews (heuristic)."""
    work = rgb.astype(np.float32)
    intensity = work.mean(axis=2)
    spread = work.max(axis=2) - work.min(axis=2)
    return (intensity > 205) & (spread < 35)


def flooded_metrics(mask: np.ndarray, bbox: dict | None, population: int | None = None) -> dict:
    pct = mask_ratio(mask)
    area = bbox_area_km2(bbox) * pct
    out = {
        "water_area_km2": round(area, 2),
        "flooded_area_km2": round(area, 2),
        "percent_affected": round(pct * 100, 1),
        "label": "Satellite-derived water indication — requires validation",
        "method": HEURISTIC_METHOD,
        "validated_flood_boundary": False,
    }
    if population is not None:
        out["estimated_population_affected"] = int(population * pct)
    return out


def _resize_mask_pair(before: np.ndarray, after: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Align RGB (or mask) arrays to a common HxW for before/after comparison."""
    if before.shape[:2] == after.shape[:2]:
        return before, after
    h = min(before.shape[0], after.shape[0])
    w = min(before.shape[1], after.shape[1])
    if cv2 is not None:
        before = cv2.resize(before, (w, h), interpolation=cv2.INTER_AREA)
        after = cv2.resize(after, (w, h), interpolation=cv2.INTER_AREA)
        return before, after
    return before[:h, :w], after[:h, :w]


def compare_water_change(
    before: np.ndarray,
    after: np.ndarray,
    bbox: dict | None,
    *,
    use_sentinel_heuristic: bool = False,
) -> dict:
    """Before/after water masks → newly water-covered pixels (after & ~before).

    Does not claim permanent water was newly flooded; reports change indication only.
    """
    before, after = _resize_mask_pair(before, after)
    detector = detect_water_sentinel_rgb if use_sentinel_heuristic else detect_water
    water_b = detector(before)
    water_a = detector(after)
    if water_b.shape != water_a.shape:
        water_b, water_a = _resize_mask_pair(water_b.astype(np.uint8), water_a.astype(np.uint8))
        water_b = water_b > 0
        water_a = water_a > 0
    if use_sentinel_heuristic:
        clouds = cloud_mask_rgb(before) | cloud_mask_rgb(after)
        water_b = water_b & ~clouds
        water_a = water_a & ~clouds
    newly = water_a & ~water_b
    lost = water_b & ~water_a
    before_pct = mask_ratio(water_b)
    after_pct = mask_ratio(water_a)
    new_pct = mask_ratio(newly)
    before_area = round(bbox_area_km2(bbox) * before_pct, 2)
    after_area = round(bbox_area_km2(bbox) * after_pct, 2)
    newly_area = round(bbox_area_km2(bbox) * new_pct, 2)
    if before_pct > 1e-6:
        pct_change = round(((after_pct - before_pct) / before_pct) * 100.0, 1)
    else:
        pct_change = round(after_pct * 100.0, 1) if after_pct > 0 else 0.0
    metrics = {
        "before_water_fraction": round(before_pct, 4),
        "after_water_fraction": round(after_pct, 4),
        "newly_flooded_fraction": round(new_pct, 4),
        "water_lost_fraction": round(mask_ratio(lost), 4),
        "before_water_area_km2": before_area,
        "after_water_area_km2": after_area,
        "newly_flooded_area_km2": newly_area,
        "newly_flooded_percentage": round(new_pct * 100.0, 1),
        "percentage_change": pct_change,
        "flood_expansion_fraction": round(new_pct, 4),
        "flooded_area_km2": newly_area,
        "label": WATER_CHANGE_LABEL,
        "method": HEURISTIC_METHOD,
        "validated_flood_boundary": False,
        "interprets_all_water_as_flood": False,
        "permanent_water_excluded_from_new": True,
        "cloud_pixels_excluded": bool(use_sentinel_heuristic),
        "spatial_alignment": "previews resized to common pixel grid (approximate; not orthorectified matching)",
        "spatial_resolution": "Sentinel-2 10 m native; analysis uses STAC RGB preview (lower, unknown exact GSD)",
    }
    before_geo = mask_to_geojson(water_b, bbox, "before water")
    after_geo = mask_to_geojson(water_a, bbox, "after water")
    newly_geo = mask_to_geojson(newly, bbox, "newly water-covered (not validated as flood)")
    geojson = {
        "type": "FeatureCollection",
        "features": newly_geo["features"] + after_geo["features"] + before_geo["features"],
    }
    return {
        "metrics": metrics,
        "geojson": geojson,
        "before_mask": water_b,
        "after_mask": water_a,
        "expansion_mask": newly,
        "before_water_geojson": before_geo,
        "after_water_geojson": after_geo,
        "newly_flooded_geojson": newly_geo,
    }


def compare_scenes(before: np.ndarray, after: np.ndarray, bbox: dict | None, *, use_sentinel_heuristic: bool = False) -> dict:
    water = compare_water_change(before, after, bbox, use_sentinel_heuristic=use_sentinel_heuristic)
    before, after = _resize_mask_pair(before, after)
    veg_b, veg_a = detect_vegetation(before), detect_vegetation(after)
    urban_b, urban_a = detect_urban(before), detect_urban(after)
    expansion = water["expansion_mask"]
    veg_loss = veg_b & ~veg_a
    urban_change = urban_a ^ urban_b
    damaged = expansion | veg_loss
    metrics = {
        **water["metrics"],
        "changed_area_fraction": round(float((expansion | veg_loss | urban_change).mean()), 4),
        "vegetation_loss_fraction": round(float(veg_loss.mean()), 4),
        "urban_change_fraction": round(float(urban_change.mean()), 4),
    }
    geojson = {
        "type": "FeatureCollection",
        "features": water["newly_flooded_geojson"]["features"]
        + water["after_water_geojson"]["features"]
        + water["before_water_geojson"]["features"]
        + mask_to_geojson(veg_loss, bbox, "vegetation loss")["features"]
        + mask_to_geojson(damaged, bbox, "damaged region candidates")["features"],
    }
    return {
        "metrics": metrics,
        "geojson": geojson,
        "expansion_mask": expansion,
        "before_water_geojson": water["before_water_geojson"],
        "after_water_geojson": water["after_water_geojson"],
        "newly_flooded_geojson": water["newly_flooded_geojson"],
    }


def encode_png(rgb: np.ndarray) -> bytes:
    if cv2 is not None:
        ok, buf = cv2.imencode(".png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        if ok:
            return bytes(buf)
    # Minimal uncompressed PPM as fallback
    header = f"P6\n{rgb.shape[1]} {rgb.shape[0]}\n255\n".encode()
    return header + rgb.tobytes()


def write_raster_stub(path: str, rgb: np.ndarray, bbox: dict | None = None) -> str:
    """Optional GeoTIFF via rasterio; otherwise numpy .npy."""
    if rasterio is not None and from_bounds is not None and path.endswith(".tif"):
        west, south, east, north = 77.53, 12.91, 77.65, 13.03
        if bbox and bbox.get("type") == "Polygon":
            ring = bbox["coordinates"][0]
            west, east = min(p[0] for p in ring), max(p[0] for p in ring)
            south, north = min(p[1] for p in ring), max(p[1] for p in ring)
        transform = from_bounds(west, south, east, north, rgb.shape[1], rgb.shape[0])
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=rgb.shape[0],
            width=rgb.shape[1],
            count=3,
            dtype="uint8",
            transform=transform,
            crs="EPSG:4326",
        ) as dst:
            for i in range(3):
                dst.write(rgb[..., i], i + 1)
        return path
    np.save(path if path.endswith(".npy") else path + ".npy", rgb)
    return path
