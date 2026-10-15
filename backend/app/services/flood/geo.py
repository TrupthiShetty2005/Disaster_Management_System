from __future__ import annotations

from typing import Any

import numpy as np

from app.services.satellite.processing import bbox_area_km2, mask_ratio, mask_to_geojson

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None


def _extent(bbox: dict | None) -> tuple[float, float, float, float]:
    if bbox and bbox.get("type") == "Polygon":
        ring = bbox["coordinates"][0]
        return (
            min(p[0] for p in ring),
            min(p[1] for p in ring),
            max(p[0] for p in ring),
            max(p[1] for p in ring),
        )
    try:
        from app.services.geo.aoi import get_aoi

        bbox_l = get_aoi().get("bbox") or []
        if len(bbox_l) == 4:
            west, south, east, north = (float(x) for x in bbox_l)
            return west, south, east, north
    except Exception:  # noqa: BLE001
        pass
    return 77.53, 12.91, 77.65, 13.03


def pixel_to_lonlat(x: float, y: float, w: int, h: int, bbox: dict | None) -> tuple[float, float]:
    minx, miny, maxx, maxy = _extent(bbox)
    lon = minx + (maxx - minx) * (x / w)
    lat = maxy - (maxy - miny) * (y / h)
    return lon, lat


def extract_polygons(mask: np.ndarray, bbox: dict | None) -> dict[str, Any]:
    """Contour polygons when OpenCV is present; otherwise AABB of water pixels."""
    h, w = mask.shape
    if cv2 is None:
        return mask_to_geojson(mask, bbox, "water-change indication")
    binary = (mask.astype(np.uint8) * 255)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    features: list[dict[str, Any]] = []
    for cnt in contours:
        if cv2.contourArea(cnt) < 4:
            continue
        ring = []
        for pt in cnt.reshape(-1, 2):
            lon, lat = pixel_to_lonlat(float(pt[0]), float(pt[1]), w, h, bbox)
            ring.append([lon, lat])
        if len(ring) < 3:
            continue
        ring.append(ring[0])
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [ring]},
                "properties": {"name": "water-change indication", "pixel_fraction": round(mask_ratio(mask), 4)},
            }
        )
    if not features:
        return mask_to_geojson(mask, bbox, "water-change indication")
    return {"type": "FeatureCollection", "features": features}


def heatmap_geojson(mask: np.ndarray, bbox: dict | None, cells: int = 8) -> dict[str, Any]:
    h, w = mask.shape
    minx, miny, maxx, maxy = _extent(bbox)
    features: list[dict[str, Any]] = []
    for gy in range(cells):
        for gx in range(cells):
            y0, y1 = int(h * gy / cells), int(h * (gy + 1) / cells)
            x0, x1 = int(w * gx / cells), int(w * (gx + 1) / cells)
            block = mask[y0:y1, x0:x1]
            intensity = float(block.mean()) if block.size else 0.0
            if intensity < 0.05:
                continue
            west = minx + (maxx - minx) * gx / cells
            east = minx + (maxx - minx) * (gx + 1) / cells
            north = maxy - (maxy - miny) * gy / cells
            south = maxy - (maxy - miny) * (gy + 1) / cells
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[west, south], [east, south], [east, north], [west, north], [west, south]]],
                    },
                    "properties": {"name": "flood heatmap", "intensity": round(intensity, 3)},
                }
            )
    return {"type": "FeatureCollection", "features": features}


def classify_flood_risk(flood_percentage: float) -> str:
    if flood_percentage < 15:
        return "low"
    if flood_percentage < 35:
        return "moderate"
    if flood_percentage < 60:
        return "high"
    return "critical"


def affected_assets(flood_percentage: float, population: int) -> tuple[int, int, int]:
    pct = flood_percentage / 100.0
    return int(population * pct), int(12 * pct + 0.5), int(80 * pct + 0.5)


def flooded_area_km2(mask: np.ndarray, bbox: dict | None) -> float:
    return round(bbox_area_km2(bbox) * mask_ratio(mask), 2)
