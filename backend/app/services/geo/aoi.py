"""Operational area of interest. Defaults to Karnataka / Bengaluru — never Kerala demo coords."""

from __future__ import annotations

from typing import Any

from app.core.config import settings

# Kerala demo point (must never be the live default).
_KERALA_DEMO = (9.517, 76.522)

_AOI: dict[str, Any] | None = None


def _default_bbox(lat: float, lon: float, pad: float) -> list[float]:
    return [lon - pad, lat - pad, lon + pad, lat + pad]


def reset_aoi_to_default() -> dict[str, Any]:
    global _AOI
    lat = float(settings.demo_latitude)
    lon = float(settings.demo_longitude)
    pad = float(getattr(settings, "gis_bbox_pad_deg", 0.06) or 0.06)
    _AOI = {
        "country": settings.aoi_country,
        "state": settings.aoi_state,
        "district": None,
        "aoi_name": settings.aoi_name,
        "latitude": lat,
        "longitude": lon,
        "bbox": _default_bbox(lat, lon, pad),
        "bbox_pad_deg": pad,
        "boundary_geojson": None,
        "source": "application default (Bengaluru, Karnataka)",
        "status": "STATIC_EXTERNAL",
        "coverage_note": "Default analysis point until an OSM district or custom AOI is selected.",
    }
    return dict(_AOI)


def get_aoi() -> dict[str, Any]:
    global _AOI
    if _AOI is None:
        reset_aoi_to_default()
    assert _AOI is not None
    lat, lon = float(_AOI["latitude"]), float(_AOI["longitude"])
    if abs(lat - _KERALA_DEMO[0]) < 0.01 and abs(lon - _KERALA_DEMO[1]) < 0.01:
        return reset_aoi_to_default()
    return dict(_AOI)


def set_aoi(payload: dict[str, Any]) -> dict[str, Any]:
    global _AOI
    current = get_aoi()
    merged = {**current, **payload}
    lat = float(merged["latitude"])
    lon = float(merged["longitude"])
    if abs(lat - _KERALA_DEMO[0]) < 0.01 and abs(lon - _KERALA_DEMO[1]) < 0.01:
        raise ValueError("Kerala demo coordinates are not allowed for live India/Karnataka analysis.")
    pad = float(merged.get("bbox_pad_deg") or getattr(settings, "gis_bbox_pad_deg", 0.06) or 0.06)
    bbox = merged.get("bbox")
    if not bbox or len(bbox) != 4:
        bbox = _default_bbox(lat, lon, pad)
    merged["latitude"] = lat
    merged["longitude"] = lon
    merged["bbox"] = [float(x) for x in bbox]
    merged["bbox_pad_deg"] = pad
    merged["country"] = merged.get("country") or "India"
    merged["state"] = merged.get("state") or "Karnataka"
    _AOI = merged
    try:
        from app.services.gis.overpass import invalidate_gis_cache

        invalidate_gis_cache()
    except Exception:
        pass
    return get_aoi()


def apply_point_aoi(lat: float, lon: float, *, pad: float | None = None, name: str | None = None) -> dict[str, Any]:
    pad_v = float(pad if pad is not None else getattr(settings, "gis_bbox_pad_deg", 0.06) or 0.06)
    return set_aoi(
        {
            "latitude": lat,
            "longitude": lon,
            "bbox_pad_deg": pad_v,
            "bbox": _default_bbox(lat, lon, pad_v),
            "aoi_name": name or f"Custom AOI {lat:.4f}N {lon:.4f}E",
            "district": None,
            "boundary_geojson": None,
            "source": "user-selected point",
            "status": "STATIC_EXTERNAL",
            "coverage_note": "Satellite/weather queries use this point and bbox. Not an administrative district.",
        }
    )
