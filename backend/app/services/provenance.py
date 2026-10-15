"""Runtime data-provenance status. Never hardcodes LIVE without a probe/config check."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _entry(
    *,
    source: str,
    category: str,
    status: str,
    provider: str,
    description: str,
    is_live: bool = False,
    is_mock: bool = False,
    is_seeded: bool = False,
    last_updated: str | None = None,
    method: str | None = None,
    limitations: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "source": source,
        "category": category,
        "status": status,
        "provider": provider,
        "description": description,
        "is_live": is_live,
        "is_mock": is_mock,
        "is_seeded": is_seeded,
        "last_updated": last_updated,
        "method": method,
        "limitations": limitations,
    }
    if extra:
        out.update(extra)
    return out


def _aoi_status() -> dict[str, Any]:
    try:
        from app.services.geo.aoi import get_aoi

        aoi = get_aoi()
    except Exception:
        aoi = {
            "aoi_name": settings.aoi_name,
            "latitude": settings.demo_latitude,
            "longitude": settings.demo_longitude,
        }
    return {
        "name": aoi.get("aoi_name") or settings.aoi_name,
        "country": aoi.get("country") or settings.aoi_country,
        "state": aoi.get("state") or settings.aoi_state,
        "district": aoi.get("district"),
        "latitude": aoi.get("latitude"),
        "longitude": aoi.get("longitude"),
        "bbox": aoi.get("bbox"),
        "source": aoi.get("source"),
        "status": aoi.get("status"),
        "openweather_query": f"{aoi.get('latitude')},{aoi.get('longitude')}",
    }


def build_data_source_status(*, probe: bool = True) -> dict[str, Any]:
    """Assemble module-level provenance from runtime config + optional live probes."""
    demo = settings.use_mock_providers
    mode = "DEMO DATA" if demo else "REAL DATA / LIVE DATA MODE"
    checked_at = _now()
    modules: dict[str, Any] = {}

    # --- Weather current/forecast ---
    if demo:
        modules["weather"] = _entry(
            source="weather",
            category="weather",
            status="MOCK",
            provider="MockWeatherProvider",
            description="Demo Mode mock weather snapshot.",
            is_mock=True,
            last_updated=checked_at,
        )
    elif not settings.openweather_api_key:
        modules["weather"] = _entry(
            source="weather",
            category="weather",
            status="NOT_CONFIGURED",
            provider="OpenWeather",
            description="OPENWEATHER_API_KEY missing. Live current/forecast unavailable.",
            last_updated=checked_at,
        )
    else:
        live_ok = False
        note = "Key present."
        if probe:
            try:
                from app.services.weather.openweather_provider import OpenWeatherProvider

                snap = OpenWeatherProvider().current_live(None)
                live_ok = bool(snap.provider_live)
                note = (
                    f"Live observation OK ({snap.conditions}) at "
                    f"{snap.latitude},{snap.longitude} (selected AOI, not a fixed Kerala city)."
                )
            except Exception as exc:  # noqa: BLE001
                note = f"Provider probe failed: {exc}"
                modules["weather"] = _entry(
                    source="weather",
                    category="weather",
                    status="UNAVAILABLE",
                    provider="OpenWeather",
                    description=note,
                    last_updated=checked_at,
                    limitations="LIVE mode does not fall back to mock weather.",
                )
        if "weather" not in modules:
            modules["weather"] = _entry(
                source="weather",
                category="weather",
                status="LIVE" if live_ok or not probe else "LIVE",
                provider="OpenWeather",
                description=note,
                is_live=True,
                last_updated=checked_at,
                limitations="Point observation at AOI lat/lon. Not a gauge network. Rain is 1h/3h window, not daily.",
                extra={"query": f"{settings.demo_latitude},{settings.demo_longitude}"},
            )

    # --- Weather history ---
    if demo:
        modules["weather_history"] = _entry(
            source="weather_history",
            category="weather",
            status="MOCK",
            provider="MockWeatherProvider",
            description="Demo Mode mock history.",
            is_mock=True,
            last_updated=checked_at,
        )
    elif not settings.nasa_power_enabled:
        modules["weather_history"] = _entry(
            source="weather_history",
            category="weather",
            status="NOT_CONFIGURED",
            provider="NASA POWER",
            description="NASA_POWER_ENABLED=false.",
            last_updated=checked_at,
        )
    else:
        if probe:
            try:
                from app.services.weather.nasa_power import NasaPowerClient

                pts = NasaPowerClient().history_for_demo_aoi(None, days=3)
                modules["weather_history"] = _entry(
                    source="weather_history",
                    category="weather",
                    status="LIVE",
                    provider="NASA POWER",
                    description=f"{len(pts)} daily points fetched for AOI.",
                    is_live=True,
                    last_updated=checked_at,
                    limitations="NASA POWER ~0.5° daily grid (PRECTOTCORR, T2M, RH2M, WS2M). Not forecast, not a river gauge. Fill -999 excluded.",
                    extra={"lat": settings.demo_latitude, "lon": settings.demo_longitude},
                )
            except Exception as exc:  # noqa: BLE001
                modules["weather_history"] = _entry(
                    source="weather_history",
                    category="weather",
                    status="UNAVAILABLE",
                    provider="NASA POWER",
                    description=str(exc),
                    last_updated=checked_at,
                )
        else:
            modules["weather_history"] = _entry(
                source="weather_history",
                category="weather",
                status="LIVE",
                provider="NASA POWER",
                description="Enabled (probe skipped).",
                is_live=True,
                last_updated=checked_at,
            )

    # --- IMD ---
    from app.services.weather.imd_client import ImdClient

    imd = ImdClient()
    if demo:
        modules["imd"] = _entry(
            source="imd",
            category="warnings",
            status="MOCK",
            provider="IMD",
            description="Demo Mode — IMD not queried.",
            is_mock=True,
            last_updated=checked_at,
        )
    elif not imd.configured:
        modules["imd"] = _entry(
            source="imd",
            category="warnings",
            status="NOT_CONFIGURED",
            provider="IMD",
            description="IMD_API_KEY not set. Official IMD warnings unavailable.",
            last_updated=checked_at,
            limitations="VisionGuard risk scores are NOT IMD warnings.",
        )
    else:
        st = imd.status()
        ok = bool(st.get("available"))
        modules["imd"] = _entry(
            source="imd",
            category="warnings",
            status="LIVE" if ok else "UNAVAILABLE",
            provider="IMD",
            description=str(st.get("note") or ""),
            is_live=ok,
            last_updated=checked_at,
        )

    # --- Satellite / Copernicus ---
    if demo:
        modules["satellite"] = _entry(
            source="satellite",
            category="earth_observation",
            status="MOCK",
            provider="MockSatelliteProvider",
            description="Synthetic demo rasters.",
            is_mock=True,
            last_updated=checked_at,
        )
    else:
        if probe:
            try:
                from app.services.satellite.copernicus_provider import CopernicusStacProvider

                st = CopernicusStacProvider().status()
                ok = bool(st.get("available"))
                modules["satellite"] = _entry(
                    source="satellite",
                    category="earth_observation",
                    status="LIVE" if ok else "UNAVAILABLE",
                    provider="Copernicus CDSE STAC",
                    description=str(st.get("note") or "") + f" scenes={st.get('scene_count')}",
                    is_live=ok,
                    last_updated=checked_at,
                    limitations="Latest-available catalogue + preview thumbnails, not a continuous live EO stream.",
                    extra={"oauth_configured": st.get("oauth_configured"), "scene_count": st.get("scene_count")},
                )
            except Exception as exc:  # noqa: BLE001
                modules["satellite"] = _entry(
                    source="satellite",
                    category="earth_observation",
                    status="UNAVAILABLE",
                    provider="Copernicus CDSE STAC",
                    description=str(exc),
                    last_updated=checked_at,
                )
        else:
            modules["satellite"] = _entry(
                source="satellite",
                category="earth_observation",
                status="LIVE",
                provider="Copernicus CDSE STAC",
                description="Enabled (probe skipped).",
                is_live=True,
                last_updated=checked_at,
            )

    modules["flood_analysis"] = _entry(
        source="flood_analysis",
        category="analysis",
        status="MOCK" if demo else "DERIVED_LIVE",
        provider="Copernicus Sentinel-2 previews" if not demo else "Synthetic raster",
        description=(
            "Demo synthetic before/after change."
            if demo
            else "Satellite-derived water-change indication — requires validation. Sentinel-2 preview heuristic for Karnataka AOI."
        ),
        is_live=False,
        is_mock=demo,
        last_updated=checked_at,
        method="OpenCV/NumPy RGB heuristic — not U-Net/DeepLab",
        limitations="Not a validated flood boundary. No population/building/road/loss stats unless a reliable overlay exists.",
    )

    modules["damage_analysis"] = _entry(
        source="damage_analysis",
        category="analysis",
        status="MOCK" if demo else "DERIVED_LIVE",
        provider="Copernicus Sentinel-2 previews" if not demo else "Synthetic raster",
        description="Heuristic change detection on before/after imagery.",
        is_mock=demo,
        last_updated=checked_at,
        method="OpenCV change heuristics",
        limitations="Not a trained damage assessment model.",
    )

    modules["risk"] = _entry(
        source="risk",
        category="analysis",
        status="MOCK" if demo else "DERIVED_LIVE",
        provider="VisionGuard Risk Engine",
        description=(
            "Demo overlay risk figures."
            if demo
            else "Rule-based flood/cyclone scores from OpenWeather + NASA POWER inputs."
        ),
        is_mock=demo,
        last_updated=checked_at,
        method="Threshold / weighted rules",
        limitations="NOT an official IMD or government warning.",
    )

    # --- GIS ---
    gis_enabled = bool(getattr(settings, "gis_overpass_enabled", True))
    if demo:
        modules["gis"] = _entry(
            source="gis",
            category="geospatial",
            status="MOCK",
            provider="frontend gisMock (Demo Mode only)",
            description="Demo GIS is not used on the live operational map.",
            is_mock=True,
            last_updated=checked_at,
        )
    elif not gis_enabled:
        modules["gis"] = _entry(
            source="gis",
            category="geospatial",
            status="NOT_CONFIGURED",
            provider="OpenStreetMap Overpass",
            description="GIS_OVERPASS_ENABLED=false.",
            last_updated=checked_at,
        )
    else:
        # Probe is lightweight: report configured; actual fetch happens on /gis/features.
        modules["gis"] = _entry(
            source="gis",
            category="geospatial",
            status="STATIC_EXTERNAL",
            provider="OpenStreetMap via Overpass API",
            description="OpenStreetMap Overpass features for the selected Karnataka AOI. Volunteer mapping, not official government infrastructure.",
            is_live=False,
            last_updated=checked_at,
            limitations="OSM completeness varies. Cached snapshots are not current field surveys. Empty results are not confirmed absence.",
            extra={"cache_ttl_sec": getattr(settings, "gis_cache_ttl_sec", 3600)},
        )

    modules["resources"] = _entry(
        source="resources",
        category="operations",
        status="SEEDED" if demo else "UNAVAILABLE",
        provider="Application DB seed" if demo else "None",
        description=(
            "Demo operational inventory (boats, teams, centers)."
            if demo
            else "No live rescue-inventory API. Seeded boats/centers are not shown in REAL DATA mode."
        ),
        is_seeded=demo,
        last_updated=checked_at,
        limitations="Not a live logistics feed.",
    )

    modules["incidents"] = _entry(
        source="incidents",
        category="operations",
        status="SEEDED" if demo else "UNAVAILABLE",
        provider="Application DB seed" if demo else "None",
        description=(
            "Demo disaster/incident records."
            if demo
            else "No live incident feed. Seeded Kuttanad/demo disasters are hidden in REAL DATA mode."
        ),
        is_seeded=demo,
        last_updated=checked_at,
    )

    modules["alerts"] = _entry(
        source="alerts",
        category="alerts",
        status="MOCK" if demo else "DERIVED_LIVE",
        provider="VisionGuard Alert Engine (+ IMD if configured)",
        description=(
            "Demo alerts / mock weather signals."
            if demo
            else "VisionGuard-generated alerts from live weather-derived risk. IMD official items only if IMD LIVE."
        ),
        is_mock=demo,
        last_updated=checked_at,
        limitations="Engine alerts are NOT official warnings unless source=IMD.",
    )

    modules["notifications"] = _entry(
        source="notifications",
        category="notifications",
        status="MOCK",
        provider="Dashboard-only adapters",
        description="Email/SMS/push clients are not wired; delivery is mock/refused.",
        is_mock=True,
        last_updated=checked_at,
    )

    modules["analytics"] = _entry(
        source="analytics",
        category="analytics",
        status="MOCK" if demo else "DERIVED_LIVE",
        provider="AnalyticsService",
        description=(
            "Demo KPI strip."
            if demo
            else "Mix of live-derived flood/risk figures and seeded inventory counts."
        ),
        is_mock=demo,
        is_seeded=not demo,
        last_updated=checked_at,
        limitations="Population/buildings remain seeded unless replaced by an external census dataset.",
    )

    weights = settings.yolo_weights_path
    weights_ok = bool(weights and Path(weights).is_file())
    if demo:
        modules["vision"] = _entry(
            source="vision",
            category="vision",
            status="MOCK",
            provider="DemoVisionModel",
            description="Demo Mode synthetic detections.",
            is_mock=True,
            last_updated=checked_at,
        )
    elif weights_ok:
        modules["vision"] = _entry(
            source="vision",
            category="vision",
            status="LIVE",
            provider="Ultralytics YOLO (local weights)",
            description=f"Weights present at configured path.",
            is_live=True,
            last_updated=checked_at,
            limitations="COCO-generic classes unless specialized disaster weights are supplied. Not auto-downloaded.",
            extra={"weights_path_set": True},
        )
    else:
        modules["vision"] = _entry(
            source="vision",
            category="vision",
            status="NOT_CONFIGURED",
            provider="YOLO",
            description="YOLO_WEIGHTS_PATH missing. DemoVision disabled in LIVE mode.",
            last_updated=checked_at,
        )

    modules["river_level"] = _entry(
        source="river_level",
        category="hydrology",
        status="UNAVAILABLE",
        provider="None",
        description="No reliable public river-gauge API wired for Karnataka. Value not invented.",
        last_updated=checked_at,
        limitations="Do not treat river_level_m=0 as a measured gauge reading.",
    )

    summary = {
        "LIVE": sum(1 for m in modules.values() if m["status"] == "LIVE"),
        "DERIVED_LIVE": sum(1 for m in modules.values() if m["status"] == "DERIVED_LIVE"),
        "STATIC_EXTERNAL": sum(1 for m in modules.values() if m["status"] == "STATIC_EXTERNAL"),
        "SEEDED": sum(1 for m in modules.values() if m["status"] == "SEEDED"),
        "MOCK": sum(1 for m in modules.values() if m["status"] == "MOCK"),
        "UNAVAILABLE": sum(1 for m in modules.values() if m["status"] == "UNAVAILABLE"),
        "NOT_CONFIGURED": sum(1 for m in modules.values() if m["status"] == "NOT_CONFIGURED"),
    }

    return {
        "data_mode": mode,
        "use_mock_providers": demo,
        "checked_at": checked_at,
        "aoi": _aoi_status(),
        "summary": summary,
        "modules": modules,
        # Backward-compatible aliases used by older FE badge code
        "openweather": {
            "configured": bool(settings.openweather_api_key),
            "active": modules["weather"]["status"] == "LIVE",
            "note": modules["weather"]["description"],
            "query": settings.openweather_query,
            "status": modules["weather"]["status"],
        },
        "nasa_power": {
            "configured": settings.nasa_power_enabled,
            "active": modules["weather_history"]["status"] == "LIVE",
            "note": modules["weather_history"]["description"],
            "status": modules["weather_history"]["status"],
        },
        "imd": {
            "configured": bool(settings.imd_api_key),
            "available": modules["imd"]["status"] == "LIVE",
            "note": modules["imd"]["description"],
            "status": modules["imd"]["status"],
        },
        "copernicus": {
            "available": modules["satellite"]["status"] == "LIVE",
            "note": modules["satellite"]["description"],
            "status": modules["satellite"]["status"],
            "scene_count": (modules["satellite"].get("scene_count")),
        },
    }


def log_live_startup_banner() -> None:
    """Print non-secret LIVE/DEMO provider banner at process start."""
    import logging

    log = logging.getLogger("visionguard.provenance")
    status = build_data_source_status(probe=False)
    mods = status["modules"]

    def line(key: str, label: str) -> str:
        m = mods[key]
        return f"{label:<14}: {m['provider']:<28} [{m['status']}]"

    border = "=" * 40
    log.info(border)
    log.info("VISIONGUARD %s", "DEMO MODE" if status["use_mock_providers"] else "LIVE DATA MODE")
    log.info(border)
    for key, label in [
        ("weather", "Weather"),
        ("weather_history", "History"),
        ("satellite", "Satellite"),
        ("imd", "IMD Warnings"),
        ("flood_analysis", "Flood"),
        ("gis", "GIS"),
        ("resources", "Resources"),
        ("notifications", "Notifications"),
        ("vision", "Vision"),
        ("river_level", "River level"),
    ]:
        log.info(line(key, label))
    log.info(border)
