from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
import json
from datetime import date, datetime
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.common import (
    AuditLogList,
    AuditLogOut,
    AlertAckRequest,
    ReportRequest,
    AlertGenerateRequest,
    AlertList,
    AlertOut,
    CycloneRiskOut,
    DisasterList,
    DisasterOut,
    EvacuationCenterList,
    EvacuationCenterOut,
    FloodRiskOut,
    HealthOut,
    RainfallAnalysisOut,
    AllocateRequest,
    AnalyzeRequest,
    CompareRequest,
    RescueDecisionRequest,
    RescuePlanOut,
    RescuePlanRequest,
    RescuePriorityList,
    RescuePriorityOut,
    DamageAnalyzeRequest,
    DamageAssessmentList,
    DamageAssessmentOut,
    AoiSelectRequest,
    FloodAnalyzeRequest,
    FloodEventList,
    FloodEventOut,
    SatelliteAnalysisOut,
    DetectionOut,
    VisionResultOut,
    SatelliteImageList,
    SatelliteImageOut,
    ResourceList,
    RescueResourceOut,
    RiskZoneDetailOut,
    RiskZoneList,
    RiskZoneOut,
    WeatherAlertCandidateOut,
    WeatherAlertsOut,
    WeatherCurrentOut,
    WeatherForecastList,
    WeatherForecastOut,
    WeatherHistoryList,
    WeatherHistoryPointOut,
)
from app.services.ops import (
    DisasterService,
    EvacuationService,
    ResourceService,
    RiskService,
    WeatherService,
)
from app.services.rescue.service import RescuePlanningService, normalize_status, normalize_type
from app.services.alerts.service import EarlyWarningService
from app.services.alerts.rules import disclaimer as alert_disclaimer
from app.services.alerts.stream import recent as alert_events, subscribe as alert_subscribe, unsubscribe as alert_unsubscribe
from app.services.vision.factory import get_vision_model
from app.services.vision.pipeline import VisionPipeline
from app.services.satellite.service import SatelliteService
from app.services.weather_intel import WeatherIntelService
from app.services.flood.service import FloodDetectionService
from app.services.damage.service import DamageAssessmentService
from app.services.analytics.service import AnalyticsService, rows_to_csv
from app.services.reports.service import ReportService
from app.services.incident.service import IncidentCommandService
from app.models import Alert, AuditLog, RescueResource

router = APIRouter()


@router.get("/health", response_model=HealthOut)
def health():
    return HealthOut(
        status="ok",
        service=settings.app_name,
        environment=settings.environment,
        use_mock_providers=settings.use_mock_providers,
        data_mode="DEMO DATA" if settings.use_mock_providers else "REAL DATA",
    )


@router.get("/data-sources")
@router.get("/data-sources/status")
def data_sources(probe: bool = True):
    """Runtime data provenance + provider health. Never hardcodes LIVE without checks."""
    from app.services.provenance import build_data_source_status

    return build_data_source_status(probe=probe)


@router.get("/gis/features")
def gis_features(force: bool = False):
    """OSM Overpass features for the selected Karnataka AOI (STATIC_EXTERNAL, not official)."""
    from app.services.gis import GisService

    return GisService().fetch_features(force=force)


@router.get("/gis/aoi")
def gis_aoi():
    from app.services.geo.aoi import get_aoi

    return get_aoi()


@router.put("/gis/aoi")
def gis_aoi_set(body: AoiSelectRequest):
    from app.core.providers import ProviderUnavailableError
    from app.services.geo.admin import RegionAdminService
    from app.services.geo.aoi import apply_point_aoi, set_aoi

    try:
        if body.district:
            return RegionAdminService().select_district(body.district, pad=body.bbox_pad_deg)
        if body.latitude is not None and body.longitude is not None:
            if body.bbox and len(body.bbox) == 4:
                return set_aoi(
                    {
                        "latitude": body.latitude,
                        "longitude": body.longitude,
                        "bbox": body.bbox,
                        "bbox_pad_deg": body.bbox_pad_deg,
                        "aoi_name": body.aoi_name,
                        "district": None,
                        "boundary_geojson": None,
                        "source": "user-selected bbox",
                        "status": "STATIC_EXTERNAL",
                        "coverage_note": "Custom bbox for satellite/weather queries.",
                    }
                )
            return apply_point_aoi(body.latitude, body.longitude, pad=body.bbox_pad_deg, name=body.aoi_name)
    except ValueError as exc:
        raise ProviderUnavailableError("aoi", str(exc)) from exc
    raise ProviderUnavailableError("aoi", "Provide a Karnataka district name or latitude+longitude.")


@router.get("/gis/india")
def gis_india():
    from app.services.geo.admin import RegionAdminService

    return RegionAdminService().india_and_karnataka()


@router.get("/gis/karnataka/districts")
def gis_karnataka_districts():
    from app.services.geo.admin import RegionAdminService

    return RegionAdminService().karnataka_districts()


@router.get("/disasters", response_model=DisasterList)
def list_disasters(phase: str | None = None, db: Session = Depends(get_db)):
    items, total = DisasterService(db).list(phase)
    return DisasterList(items=[DisasterOut.model_validate(i) for i in items], total=total)


@router.get("/disasters/{disaster_id}", response_model=DisasterOut)
def get_disaster(disaster_id: str, db: Session = Depends(get_db)):
    return DisasterOut.model_validate(DisasterService(db).get(disaster_id))


def _zone_out(svc: RiskService, zone) -> RiskZoneOut:
    base = RiskZoneOut.model_validate(zone)
    extra = svc.explain(zone)
    return base.model_copy(update=extra)


@router.get("/risk-zones", response_model=RiskZoneList)
def list_risk_zones(db: Session = Depends(get_db)):
    svc = RiskService(db)
    items, total = svc.list()
    return RiskZoneList(items=[_zone_out(svc, z) for z in items], total=total)


@router.get("/risk-zones/{zone_id}", response_model=RiskZoneDetailOut)
def get_risk_zone(zone_id: str, db: Session = Depends(get_db)):
    svc = RiskService(db)
    return RiskZoneDetailOut.model_validate(_zone_out(svc, svc.get(zone_id)))


@router.get("/risk/flood", response_model=FloodRiskOut)
def flood_risk(location_id: str | None = None, db: Session = Depends(get_db)):
    result = WeatherIntelService(db).flood(location_id)
    body = dict(result.__dict__)
    body["is_official_warning"] = False
    body["data_provenance"] = {
        "status": "MOCK" if settings.use_mock_providers else "DERIVED_LIVE",
        "provider": "VisionGuard Risk Engine",
        "description": (
            result.estimate_label
            + " NOT an IMD official warning. Missing river/terrain/soil/history terms are omitted, not invented."
        ),
        "inputs": "Available OpenWeather current and/or NASA POWER daily rainfall only (LIVE).",
        "scientifically_established_probability": False,
    }
    return FloodRiskOut.model_validate(body)


@router.get("/risk/cyclone", response_model=CycloneRiskOut)
def cyclone_risk(location_id: str | None = None, db: Session = Depends(get_db)):
    result = WeatherIntelService(db).cyclone(location_id)
    body = dict(result.__dict__)
    body["is_official_warning"] = False
    body["data_provenance"] = {
        "status": "MOCK" if settings.use_mock_providers else "DERIVED_LIVE",
        "provider": "VisionGuard Risk Engine",
        "description": "Rule-based cyclone index from OpenWeather wind/pressure — NOT an official IMD warning.",
        "scientifically_established_probability": False,
    }
    return CycloneRiskOut.model_validate(body)


@router.get("/weather/current", response_model=WeatherCurrentOut)
def weather_current(location_id: str | None = None, db: Session = Depends(get_db)):
    snap = WeatherService(db).current(location_id)
    payload = snap.model_dump()
    live = bool(payload.get("provider_live")) and not settings.use_mock_providers
    payload["river_level_m"] = None
    payload["river_level_available"] = False
    payload["storm_probability"] = None if live else payload.get("storm_probability")
    payload["data_provenance"] = {
        "status": "LIVE" if live else ("MOCK" if settings.use_mock_providers else "UNAVAILABLE"),
        "provider": "OpenWeather" if live else ("MockWeatherProvider" if settings.use_mock_providers else "OpenWeather"),
        "description": (
            "Live observation at selected Karnataka AOI lat/lon (OpenWeather current). "
            "Timestamps from the provider `dt` field. Not a Kerala city lookup."
            if live
            else ("Demo Mode mock weather." if settings.use_mock_providers else "Weather provider not live.")
        ),
        "river_level": "UNAVAILABLE — no gauge API wired; value not invented.",
        "record_kind": "current_observation",
        "seeded_observations_used": False if live else True,
    }
    return WeatherCurrentOut.model_validate(payload)


@router.get("/weather/forecast", response_model=WeatherForecastList)
def weather_forecast(location_id: str | None = None, db: Session = Depends(get_db)):
    items, total, live = WeatherService(db).forecast(location_id)
    return WeatherForecastList(
        items=[WeatherForecastOut.model_validate(i.model_dump()) for i in items],
        total=total,
        provider_live=live,
    )


@router.get("/weather/history", response_model=WeatherHistoryList)
def weather_history(location_id: str | None = None, db: Session = Depends(get_db)):
    items = WeatherIntelService(db).history(location_id)
    live_hist = (not settings.use_mock_providers) and items and items[0].source == "nasa-power"
    return WeatherHistoryList(
        items=[WeatherHistoryPointOut.model_validate(i.model_dump()) for i in items],
        total=len(items),
        data_provenance={
            "status": "LIVE" if live_hist else ("MOCK" if settings.use_mock_providers else "UNAVAILABLE"),
            "provider": "NASA POWER" if live_hist else "MockWeatherProvider",
            "record_kind": "historical_daily",
            "description": (
                "Daily PRECTOTCORR/T2M/RH2M/WS2M at the selected AOI point. ~0.5° grid. "
                "Not a forecast, not a river gauge. Fill values excluded."
                if live_hist
                else "Demo Mode mock history."
            ),
        },
    )


@router.get("/weather/rainfall", response_model=RainfallAnalysisOut)
def weather_rainfall(location_id: str | None = None, db: Session = Depends(get_db)):
    result = WeatherIntelService(db).rainfall(location_id)
    return RainfallAnalysisOut.model_validate(result.__dict__)


@router.get("/weather/alerts", response_model=WeatherAlertsOut)
def weather_alerts(location_id: str | None = None, db: Session = Depends(get_db)):
    payload = WeatherIntelService(db).weather_alerts(location_id)
    items: list[WeatherAlertCandidateOut] = []
    for a in payload["provider_alerts"]:
        items.append(WeatherAlertCandidateOut.model_validate(a.model_dump()))
    from app.core.operational import hide_seeded_operations, is_demo_or_simulated_alert

    for a in payload["generated_candidates"]:
        if hide_seeded_operations() and is_demo_or_simulated_alert(a):
            continue
        items.append(
            WeatherAlertCandidateOut(
                id=a.id,
                title=a.title,
                severity=a.severity,
                category=a.category,
                message=a.message,
                issued_at=a.issued_at,
            )
        )
    return WeatherAlertsOut(
        items=items,
        total=len(items),
        flood_probability=payload["flood_probability"],
        cyclone_risk=payload["cyclone_risk"],
        imd_status=payload.get("imd_status") or "",
        imd_source_status=payload.get("imd_source_status") or "UNAVAILABLE",
    )


def _alert_out(row) -> AlertOut:
    from app.core.operational import alert_provenance_status, is_official_warning

    sev = str(row.severity or "INFO").upper()
    if sev == "SEVERE":
        sev = "CRITICAL"
    provenance = alert_provenance_status(row)
    official = is_official_warning(row)
    message = str(row.message or "")
    if official:
        kind = "official_warning"
    elif provenance == "DERIVED_LIVE":
        kind = "heuristic_risk_estimate"
        prefix = "Derived risk estimate · not an official government warning. "
        if prefix.lower() not in message.lower():
            message = prefix + message
    elif provenance in {"MOCK", "SEEDED"}:
        kind = "demo_simulated"
    else:
        kind = "unverified"
        prefix = "Unverified provenance · not an official warning. "
        if prefix.lower() not in message.lower():
            message = prefix + message
    return AlertOut(
        id=row.id,
        title=row.title,
        severity=sev,
        category=row.category,
        message=message,
        location_id=row.location_id,
        issued_at=row.issued_at,
        alert_type=getattr(row, "alert_type", None) or row.category,
        location_name=getattr(row, "location_name", None) or "",
        latitude=float(getattr(row, "latitude", None) or settings.demo_latitude),
        longitude=float(getattr(row, "longitude", None) or settings.demo_longitude),
        risk_score=float(getattr(row, "risk_score", None) or 0),
        expires_at=getattr(row, "expires_at", None),
        status=getattr(row, "status", None) or "ACTIVE",
        recommended_action=getattr(row, "recommended_action", None) or "",
        source=getattr(row, "source", None) or "engine",
        acknowledged_at=getattr(row, "acknowledged_at", None),
        acknowledged_by=getattr(row, "acknowledged_by", None) or "",
        reason=getattr(row, "reason", None) or "",
        disclaimer=alert_disclaimer(),
        official_warning=official,
        provenance_status=provenance,
        alert_kind=kind,
    )


@router.get("/alerts", response_model=AlertList)
def list_alerts(
    severity: str | None = None,
    location_id: str | None = None,
    status: str | None = None,
    disaster_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
):
    items = EarlyWarningService(db).list(
        severity=severity,
        location_id=location_id,
        status=status,
        disaster_type=disaster_type,
        date_from=date_from,
        date_to=date_to,
    )
    rank = {"CRITICAL": 0, "WARNING": 1, "WATCH": 2, "INFO": 3}
    items = sorted(items, key=lambda a: (rank.get(str(a.severity).upper(), 9), -a.issued_at.timestamp() if a.issued_at else 0))
    return AlertList(items=[_alert_out(i) for i in items], total=len(items))


@router.get("/alerts/stream")
async def alerts_stream():
    async def gen():
        q = alert_subscribe()
        try:
            yield f"data: {json.dumps({'type': 'hello', 'disclaimer': alert_disclaimer()})}\n\n"
            while True:
                event = await q.get()
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            alert_unsubscribe(q)

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/alerts/events")
def alerts_events(since: str | None = None):
    return {"items": alert_events(since), "total": len(alert_events(since))}


@router.post("/alerts/generate", response_model=AlertList)
def generate_alerts(body: AlertGenerateRequest = AlertGenerateRequest(), db: Session = Depends(get_db)):
    items = EarlyWarningService(db).generate(body.location_id)
    return AlertList(items=[_alert_out(i) for i in items], total=len(items))


@router.get("/alerts/{alert_id}", response_model=AlertOut)
def get_alert(alert_id: str, db: Session = Depends(get_db)):
    return _alert_out(EarlyWarningService(db).get(alert_id))


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertOut)
def acknowledge_alert(alert_id: str, body: AlertAckRequest = AlertAckRequest(), db: Session = Depends(get_db)):
    return _alert_out(EarlyWarningService(db).acknowledge(alert_id, body.actor))


@router.post("/alerts/{alert_id}/resolve", response_model=AlertOut)
def resolve_alert(alert_id: str, body: AlertAckRequest = AlertAckRequest(), db: Session = Depends(get_db)):
    return _alert_out(EarlyWarningService(db).resolve(alert_id, body.actor))


def _resource_out(row) -> RescueResourceOut:
    geo = row.geojson
    lat, lon = settings.demo_latitude, settings.demo_longitude
    if geo and geo.get("type") == "Point":
        lon, lat = float(geo["coordinates"][0]), float(geo["coordinates"][1])
    else:
        lat = float(getattr(row, "latitude", None) or lat)
        lon = float(getattr(row, "longitude", None) or lon)
    return RescueResourceOut(
        id=row.id,
        name=row.name,
        resource_type=normalize_type(row.resource_type),
        status=normalize_status(row.status),
        personnel=row.personnel,
        capacity=getattr(row, "capacity", None) or row.personnel,
        latitude=lat,
        longitude=lon,
        available_at=getattr(row, "available_at", None),
        assigned_incident=getattr(row, "assigned_incident", None),
        location_id=row.location_id,
        geojson=geo,
        current_location=geo,
    )


def _priority_out(row) -> RescuePriorityOut:
    return RescuePriorityOut(
        id=row.id,
        disaster_id=row.disaster_id,
        title=row.title,
        priority=row.priority,
        people_affected=row.people_affected,
        status=row.status,
        score=float(getattr(row, "score", 0) or 0),
        level=getattr(row, "level", None) or "MEDIUM",
        factors=getattr(row, "factors", None),
        geojson=row.geojson,
    )


def _plan_out(row) -> RescuePlanOut:
    return RescuePlanOut(
        id=row.id,
        disaster_id=row.disaster_id,
        priority_id=row.priority_id,
        decision=row.decision,
        override_notes=row.override_notes or "",
        plan=row.payload,
        created_at=row.created_at,
    )


@router.get("/resources", response_model=ResourceList)
def list_resources(db: Session = Depends(get_db)):
    items = RescuePlanningService(db).list_resources()
    return ResourceList(items=[_resource_out(i) for i in items], total=len(items))


@router.post("/resources/allocate", response_model=RescueResourceOut)
def allocate_resource(body: AllocateRequest, db: Session = Depends(get_db)):
    return _resource_out(RescuePlanningService(db).allocate(body.resource_id, body.incident_id))


@router.get("/rescue/priorities", response_model=RescuePriorityList)
def rescue_priorities(db: Session = Depends(get_db)):
    items = RescuePlanningService(db).refresh_priorities()
    return RescuePriorityList(items=[_priority_out(i) for i in items], total=len(items))


@router.post("/rescue/plan", response_model=RescuePlanOut)
def create_rescue_plan(body: RescuePlanRequest = RescuePlanRequest(), db: Session = Depends(get_db)):
    return _plan_out(RescuePlanningService(db).generate_plan(body.disaster_id))


@router.get("/rescue/plans/{plan_id}", response_model=RescuePlanOut)
def get_rescue_plan(plan_id: str, db: Session = Depends(get_db)):
    row = RescuePlanningService(db).get_plan(plan_id)
    if not row:
        raise HTTPException(status_code=404, detail="Rescue plan not found")
    return _plan_out(row)


@router.post("/rescue/plans/{plan_id}/decision", response_model=RescuePlanOut)
def rescue_plan_decision(plan_id: str, body: RescueDecisionRequest, db: Session = Depends(get_db)):
    return _plan_out(RescuePlanningService(db).decide(plan_id, body.action, body.notes))


@router.get("/evacuation-centers", response_model=EvacuationCenterList)
def list_centers(db: Session = Depends(get_db)):
    items, total = EvacuationService(db).list()
    return EvacuationCenterList(
        items=[EvacuationCenterOut.model_validate(i) for i in items], total=total
    )


def _sat_out(row) -> SatelliteImageOut:
    meta = row.extra_metadata or {}
    lat = getattr(row, "latitude", None)
    lon = getattr(row, "longitude", None)
    if lat is None:
        lat = meta.get("scene_centroid_latitude")
    if lon is None:
        lon = meta.get("scene_centroid_longitude")
    footprint_ok = bool(meta.get("footprint_available", lat is not None and lon is not None))
    return SatelliteImageOut(
        id=row.id,
        source=getattr(row, "source", None) or row.provider,
        acquisition_time=row.captured_at,
        latitude=float(lat) if footprint_ok and lat is not None else None,
        longitude=float(lon) if footprint_ok and lon is not None else None,
        bounding_box=row.bbox_geojson,
        resolution=getattr(row, "resolution", None) or "10m",
        cloud_cover=getattr(row, "cloud_cover", None) or 0,
        image_url=getattr(row, "image_url", None) or f"/api/v1/satellite/images/{row.id}/preview",
        thumbnail_url=getattr(row, "thumbnail_url", None) or f"/api/v1/satellite/images/{row.id}/preview",
        status=getattr(row, "status", None) or "ready",
        metadata=meta,
        title=meta.get("title", row.provider),
        provider=row.provider,
        location_id=row.location_id,
    )


def _analysis_out(row) -> SatelliteAnalysisOut:
    return SatelliteAnalysisOut(
        id=row.id,
        satellite_image_id=row.satellite_image_id,
        model_name=row.model_name,
        analysis_type=row.analysis_type,
        summary=row.summary,
        confidence=row.confidence,
        result_geojson=row.result_geojson,
        metrics=row.metrics,
        created_at=row.created_at,
    )


@router.get("/satellite/images", response_model=SatelliteImageList)
def list_satellite_images(
    start: date | None = None,
    end: date | None = None,
    max_cloud: float | None = None,
    db: Session = Depends(get_db),
):
    items, query = SatelliteService(db).list_catalog(start=start, end=end, max_cloud=max_cloud)
    return SatelliteImageList(items=[_sat_out(i) for i in items], total=len(items), query=query)


@router.get("/satellite/images/{image_id}", response_model=SatelliteImageOut)
def get_satellite_image(image_id: str, db: Session = Depends(get_db)):
    return _sat_out(SatelliteService(db).get_image(image_id))


@router.get("/satellite/images/{image_id}/preview")
def satellite_preview(image_id: str, db: Session = Depends(get_db)):
    data = SatelliteService(db).preview_png(image_id)
    media = "image/jpeg" if data[:3] == b"\xff\xd8\xff" else "image/png"
    return Response(content=data, media_type=media)


@router.post("/satellite/analyze", response_model=SatelliteAnalysisOut)
def analyze_satellite(body: AnalyzeRequest, db: Session = Depends(get_db)):
    return _analysis_out(SatelliteService(db).analyze(body.image_id, body.analysis_type))


@router.get("/satellite/analysis/{analysis_id}", response_model=SatelliteAnalysisOut)
def get_satellite_analysis(analysis_id: str, db: Session = Depends(get_db)):
    return _analysis_out(SatelliteService(db).get_analysis(analysis_id))


@router.post("/satellite/compare", response_model=SatelliteAnalysisOut)
def compare_satellite(body: CompareRequest, db: Session = Depends(get_db)):
    return _analysis_out(SatelliteService(db).compare(body.before_image, body.after_image))


def _vision_out(job) -> VisionResultOut:
    return VisionResultOut(
        image_id=job.id,
        model_name=job.model_name,
        backend=job.backend,
        overall_severity=job.overall_severity,
        processing_time_ms=job.processing_ms,
        detections=[DetectionOut.model_validate(d) for d in (job.detections or [])],
        incident=job.incident,
        notes="CPU inference. Demo backend unless local YOLO weights are configured.",
        annotated_url=f"/api/v1/vision/jobs/{job.id}/annotated",
        gpu_required=False,
    )


@router.get("/vision/health")
def vision_health():
    return get_vision_model().health()


@router.post("/vision/detect", response_model=VisionResultOut)
async def vision_detect(file: UploadFile = File(...), db: Session = Depends(get_db)):
    data = await file.read()
    job = VisionPipeline(db).run(file.filename or "upload.jpg", data, mode="detect")
    return _vision_out(job)


@router.post("/vision/analyze", response_model=VisionResultOut)
async def vision_analyze(file: UploadFile = File(...), db: Session = Depends(get_db)):
    data = await file.read()
    job = VisionPipeline(db).run(file.filename or "upload.jpg", data, mode="analyze")
    return _vision_out(job)


@router.get("/vision/jobs/{job_id}/annotated")
def vision_annotated(job_id: str, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    from app.models import VisionJob

    job = db.query(VisionJob).filter(VisionJob.id == job_id).first()
    if not job or not job.annotated_path:
        raise HTTPException(status_code=404, detail="Annotated image not found")
    return FileResponse(job.annotated_path, media_type="image/jpeg")


def _flood_out(row) -> FloodEventOut:
    notes = (row.notes or "").strip()
    scene = (row.scene_kind or "").lower()
    boundary = row.boundary_geojson if isinstance(row.boundary_geojson, dict) else {}
    change = boundary.get("visionguard_change") if isinstance(boundary, dict) else None
    if not isinstance(change, dict):
        change = {}
    metrics = change.get("metrics") if isinstance(change.get("metrics"), dict) else {}
    if "requires validation" in notes.lower() or scene == "sentinel2-change" or metrics:
        label = "Satellite-derived water-change indication — requires validation"
    elif "Satellite-derived" in notes or scene.startswith("sentinel"):
        label = "Satellite-derived water indication — requires validation"
    elif notes:
        label = notes.split(" | ")[0] if " | " in notes else notes
        if len(label) > 160:
            label = "Prototype flood extent (OpenCV/NumPy demo, not a trained U-Net/DeepLab)"
    else:
        label = "Prototype flood extent (OpenCV/NumPy demo, not a trained U-Net/DeepLab)"
    # Strip internal payload from geojson returned as map boundary (keep FeatureCollection clean).
    boundary_out = None
    if isinstance(boundary, dict) and boundary.get("type") == "FeatureCollection":
        boundary_out = {"type": "FeatureCollection", "features": boundary.get("features") or []}
    elif row.boundary_geojson is not None:
        boundary_out = row.boundary_geojson
    return FloodEventOut(
        id=row.id,
        model_name=row.model_name,
        scene_kind=row.scene_kind,
        flooded_area=row.flooded_area,
        flood_percentage=row.flood_percentage,
        severity=row.severity,
        confidence=row.confidence,
        boundary_geojson=boundary_out,
        heatmap_geojson=row.heatmap_geojson,
        affected_population=row.affected_population,
        affected_roads=row.affected_roads,
        affected_buildings=row.affected_buildings,
        notes=row.notes,
        created_at=row.created_at,
        estimate_label=label,
        before_water_area_km2=metrics.get("before_water_area_km2"),
        after_water_area_km2=metrics.get("after_water_area_km2"),
        newly_flooded_area_km2=metrics.get("newly_flooded_area_km2", row.flooded_area if metrics else None),
        newly_flooded_percentage=metrics.get("newly_flooded_percentage", row.flood_percentage if metrics else None),
        percentage_change=metrics.get("percentage_change"),
        before_image_id=change.get("before_image_id"),
        after_image_id=change.get("after_image_id"),
        before_stac_id=change.get("before_stac_id"),
        after_stac_id=change.get("after_stac_id"),
        before_date=change.get("before_date"),
        after_date=change.get("after_date"),
        before_cloud=change.get("before_cloud"),
        after_cloud=change.get("after_cloud"),
        before_preview_url=change.get("before_preview_url"),
        after_preview_url=change.get("after_preview_url"),
        before_water_geojson=change.get("before_water_geojson"),
        after_water_geojson=change.get("after_water_geojson"),
        newly_flooded_geojson=change.get("newly_flooded_geojson"),
        change_metrics=metrics or None,
        analysis_status=change.get("analysis_status"),
        processing_method=change.get("processing_method") or metrics.get("method"),
        spatial_resolution=change.get("spatial_resolution") or metrics.get("spatial_resolution"),
        validated_flood_boundary=False,
        impact_stats_available=False if not settings.use_mock_providers else True,
    )


def _damage_out(row) -> DamageAssessmentOut:
    return DamageAssessmentOut(
        id=row.id,
        model_name=row.model_name,
        before_kind=row.before_kind,
        after_kind=row.after_kind,
        report=row.report,
        overlay_geojson=row.overlay_geojson,
        created_at=row.created_at,
        pdf_available=False,
    )


@router.post("/flood/analyze", response_model=FloodEventOut)
def flood_analyze(body: FloodAnalyzeRequest, db: Session = Depends(get_db)):
    if body.latitude is not None and body.longitude is not None:
        from app.services.geo.aoi import apply_point_aoi

        apply_point_aoi(body.latitude, body.longitude, pad=body.bbox_pad_deg)
    pop = body.population if body.population is not None else (42000 if settings.use_mock_providers else 0)
    return _flood_out(FloodDetectionService(db).analyze(body.scene_kind, pop))


@router.get("/flood/events", response_model=FloodEventList)
def flood_events(db: Session = Depends(get_db)):
    items = FloodDetectionService(db).list_events()
    return FloodEventList(items=[_flood_out(i) for i in items], total=len(items))


@router.get("/flood/events/{event_id}", response_model=FloodEventOut)
def flood_event(event_id: str, db: Session = Depends(get_db)):
    row = FloodDetectionService(db).get(event_id)
    if not row:
        raise HTTPException(status_code=404, detail="Flood event not found")
    return _flood_out(row)


@router.post("/damage/analyze", response_model=DamageAssessmentOut)
def damage_analyze(body: DamageAnalyzeRequest, db: Session = Depends(get_db)):
    return _damage_out(DamageAssessmentService(db).analyze(body.before_kind, body.after_kind))


@router.get("/damage/assessments", response_model=DamageAssessmentList)
def damage_assessments(db: Session = Depends(get_db)):
    items = DamageAssessmentService(db).list_assessments()
    return DamageAssessmentList(items=[_damage_out(i) for i in items], total=len(items))


@router.get("/damage/assessments/{assessment_id}", response_model=DamageAssessmentOut)
def damage_assessment(assessment_id: str, db: Session = Depends(get_db)):
    row = DamageAssessmentService(db).get(assessment_id)
    if not row:
        raise HTTPException(status_code=404, detail="Damage assessment not found")
    return _damage_out(row)


def _analytics_filters(
    date_from: datetime | None,
    date_to: datetime | None,
    disaster_type: str | None,
    location_id: str | None,
    severity: str | None,
) -> dict:
    return {
        "date_from": date_from,
        "date_to": date_to,
        "disaster_type": disaster_type,
        "location_id": location_id,
        "severity": severity,
    }


@router.get("/analytics/overview")
def analytics_overview(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    disaster_type: str | None = None,
    location_id: str | None = None,
    severity: str | None = None,
    db: Session = Depends(get_db),
):
    return AnalyticsService(db).overview(**_analytics_filters(date_from, date_to, disaster_type, location_id, severity))


@router.get("/analytics/disasters")
def analytics_disasters(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    disaster_type: str | None = None,
    location_id: str | None = None,
    severity: str | None = None,
    db: Session = Depends(get_db),
):
    return AnalyticsService(db).disasters(**_analytics_filters(date_from, date_to, disaster_type, location_id, severity))


@router.get("/analytics/damage")
def analytics_damage(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
):
    return AnalyticsService(db).damage(date_from=date_from, date_to=date_to)


@router.get("/analytics/resources")
def analytics_resources(db: Session = Depends(get_db)):
    return AnalyticsService(db).resources()


@router.get("/analytics/risks")
def analytics_risks(db: Session = Depends(get_db)):
    return AnalyticsService(db).risks()


@router.get("/analytics/alerts")
def analytics_alerts(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
):
    return AnalyticsService(db).alerts(date_from=date_from, date_to=date_to)


@router.get("/incidents/{incident_id}")
def incident_command(incident_id: str, db: Session = Depends(get_db)):
    return IncidentCommandService(db).picture(incident_id)


@router.post("/reports/generate")
def generate_report(body: ReportRequest, db: Session = Depends(get_db)):
    return ReportService(db).generate(body.kind, body.disaster_id)


@router.get("/audit-logs", response_model=AuditLogList)
def list_audit_logs(db: Session = Depends(get_db)):
    items = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
    return AuditLogList(
        items=[
            AuditLogOut(
                id=i.id,
                action=i.action,
                entity_type=i.entity_type,
                entity_id=i.entity_id,
                details=i.details or "",
                created_at=i.created_at,
            )
            for i in items
        ],
        total=len(items),
    )


@router.get("/exports/{dataset}")
def export_dataset(dataset: str, db: Session = Depends(get_db)):
    svc = AnalyticsService(db)
    if dataset == "analytics":
        ov = svc.overview()
        rows = [{"metric": k, "value": v} for k, v in ov["kpis"].items() if not isinstance(v, dict)]
    elif dataset == "alerts":
        rows = [
            {"id": a.id, "title": a.title, "severity": a.severity, "status": getattr(a, "status", ""), "issued_at": str(a.issued_at)}
            for a in db.query(Alert).all()
        ]
    elif dataset == "resources":
        rows = [{"id": r.id, "name": r.name, "type": r.resource_type, "status": r.status} for r in db.query(RescueResource).all()]
    elif dataset == "damage":
        dmg = svc.damage()
        rows = [{"category": k, "value": v} for k, v in dmg["series"].items()]
    elif dataset == "incident":
        pic = IncidentCommandService(db).picture()
        rows = [{"event": t["event"], "t": t["t"]} for t in pic["timeline"]]
    else:
        raise HTTPException(status_code=404, detail="Unknown export dataset")
    csv_body = rows_to_csv(rows)
    return Response(content=csv_body, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={dataset}.csv"})
