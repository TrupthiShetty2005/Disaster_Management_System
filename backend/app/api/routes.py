from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Literal

import cv2
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import SourceUnavailable
from app.db import Alert, Analysis, VisionJob, get_db
from app.geo import karnataka
from app.services import alerts as alert_svc
from app.services import analytics as analytics_svc
from app.services import events, fire, impact, rainfall, rescue, satellite, sources_status, vision, water
from app.services import overview as overview_svc
from app.sources import openmeteo, openweather

router = APIRouter()


# ---------------------------------------------------------------- system
@router.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name, "region": "Karnataka, India"}


@router.get("/sources")
def sources():
    return {"items": sources_status.status()}


# ---------------------------------------------------------------- geography
@router.get("/geo/karnataka")
def geo_karnataka():
    return karnataka.karnataka_boundary()


@router.get("/geo/districts")
def geo_districts(boundaries: bool = False):
    out: dict[str, Any] = {"items": karnataka.district_dicts()}
    if boundaries:
        out["boundaries"] = karnataka.district_boundaries()
    return out


@router.get("/geo/stations")
def geo_stations():
    return {"items": karnataka.station_dicts()}


# ---------------------------------------------------------------- dashboard
@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    return overview_svc.overview(db)


# ---------------------------------------------------------------- water
@router.get("/water/stations")
def water_stations(series: bool = True):
    return {"items": water.stations(include_series=series)}


@router.get("/water/stations/{station_id}")
def water_station(station_id: str):
    try:
        return water.station(station_id)
    except KeyError:
        raise HTTPException(404, "Unknown station") from None


# ---------------------------------------------------------------- rain & weather
@router.get("/rainfall/districts")
def rainfall_districts():
    return {"items": rainfall.districts(), **rainfall.meta()}


@router.get("/weather/{district_id}")
def weather(district_id: str):
    d = karnataka.DISTRICTS_BY_ID.get(district_id)
    if not d:
        raise HTTPException(404, "Unknown district")
    out: dict[str, Any] = {"district": {"id": d.id, "name": d.name, "hq": d.hq, "latitude": d.latitude, "longitude": d.longitude}}
    for key, fn in (("current", lambda: openweather.current(d.latitude, d.longitude)), ("forecast", lambda: openweather.forecast(d.latitude, d.longitude)), ("hourly", lambda: openmeteo.hourly_weather(d.latitude, d.longitude))):
        try:
            out[key] = fn()
        except SourceUnavailable as exc:
            out[key] = None
            out.setdefault("unavailable", {})[key] = exc.message
    return out


# ---------------------------------------------------------------- fire
Window = Literal["24h", "48h", "7d"]


@router.get("/fire/detections")
def fire_detections(window: Window = "24h"):
    return fire.detections(window)


@router.get("/fire/clusters")
def fire_clusters(window: Window = "7d"):
    return {"items": fire.clusters(window), "cluster_km": fire.CLUSTER_KM}


@router.get("/fire/danger")
def fire_danger():
    return {"items": fire.danger_forecast(), "method": fire.DANGER_METHOD}


@router.get("/events")
def disaster_events():
    return {"items": overview_svc._events(), "source": "GDACS"}


# ---------------------------------------------------------------- satellite
def _area_from_query(district: str | None, station: str | None, lat: float | None, lon: float | None, half_deg: float | None) -> dict[str, Any]:
    area: dict[str, Any] = {}
    if district:
        area["district"] = district
    elif station:
        area["station"] = station
    elif lat is not None and lon is not None:
        area.update(latitude=lat, longitude=lon)
    if half_deg:
        area["half_deg"] = half_deg
    return area


@router.get("/satellite/scenes")
def satellite_scenes(district: str | None = None, station: str | None = None, lat: float | None = None, lon: float | None = None, half_deg: float | None = Query(None, gt=0, le=0.3)):
    try:
        name, bbox = satellite.resolve_area(_area_from_query(district, station, lat, lon, half_deg))
    except (ValueError, KeyError) as exc:
        raise HTTPException(400, str(exc)) from None
    return {"area_name": name, **satellite.scenes(bbox)}


@router.get("/satellite/preview")
def satellite_preview(key: str, kind: Literal["sar", "truecolor", "ndwi", "nbr"], bbox: str):
    try:
        box = [float(v) for v in bbox.split(",")]
        satellite.resolve_area({"bbox": box})
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    return Response(satellite.preview_png(box, key, kind), media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


class AnalyzeRequest(BaseModel):
    kind: Literal["flood", "burn"]
    area: dict[str, Any]
    method: Literal["sar", "optical"] = "sar"
    baseline: Literal["dry_season", "previous"] = "dry_season"
    after_key: str | None = None
    before_key: str | None = None


def _analysis_out(a: Analysis) -> dict[str, Any]:
    return {
        "id": a.id,
        "kind": a.kind,
        "area_name": a.area_name,
        "bbox": a.bbox,
        "status": a.status,
        "before": a.before_scene,
        "after": a.after_scene,
        "metrics": a.metrics,
        "geojson": a.geojson,
        "impact": a.impact,
        "images": {name: f"/api/v1/analyses/{a.id}/images/{name}" for name in (a.images or {}).get("files", [])},
        "image_bounds": (a.images or {}).get("bounds"),
        "created_at": a.created_at,
    }


@router.post("/satellite/analyze")
def satellite_analyze(body: AnalyzeRequest, db: Session = Depends(get_db)):
    try:
        name, bbox = satellite.resolve_area(body.area)
    except (ValueError, KeyError) as exc:
        raise HTTPException(400, str(exc)) from None
    if body.kind == "flood":
        result = satellite.flood_analysis(bbox, body.method, body.baseline, body.after_key, body.before_key)
    else:
        result = satellite.burn_analysis(bbox, body.after_key, body.before_key)
    hazard = impact.hazard_from_geojson(result["geojson"], result["hazard_classes"])
    imp = impact.assess(hazard, "flood" if body.kind == "flood" else "fire")
    a = Analysis(kind=body.kind, area_name=name, bbox=bbox, before_scene=result["before"], after_scene=result["after"], metrics=result["metrics"], geojson=result["geojson"], impact=imp)
    db.add(a)
    db.flush()
    folder = Path(settings.storage_dir) / "analyses" / a.id
    folder.mkdir(parents=True, exist_ok=True)
    for fname, data in result["images"].items():
        (folder / fname).write_bytes(data)
    a.images = {"files": list(result["images"]), "bounds": result["image_bounds"]}
    db.commit()
    events.publish({"type": "analysis_complete", "id": a.id, "kind": a.kind, "area": name})
    return _analysis_out(a)


@router.get("/analyses")
def list_analyses(db: Session = Depends(get_db)):
    rows = db.scalars(select(Analysis).order_by(Analysis.created_at.desc()).limit(100)).all()
    return {"items": [{k: v for k, v in _analysis_out(a).items() if k != "geojson"} for a in rows]}


@router.get("/analyses/{analysis_id}")
def get_analysis(analysis_id: str, db: Session = Depends(get_db)):
    a = db.get(Analysis, analysis_id)
    if not a:
        raise HTTPException(404, "Analysis not found")
    return _analysis_out(a)


@router.get("/analyses/{analysis_id}/images/{name}")
def analysis_image(analysis_id: str, name: Literal["before.png", "after.png", "change.png"]):
    path = Path(settings.storage_dir) / "analyses" / analysis_id / name
    if not path.is_file():
        raise HTTPException(404, "Image not found")
    return FileResponse(path, media_type="image/png")


class FireImpactRequest(BaseModel):
    cluster_id: str
    radius_m: float = Field(500, ge=100, le=3000)


@router.post("/impact/fire-cluster")
def fire_cluster_impact(body: FireImpactRequest):
    cluster = next((c for c in fire.clusters("7d") if c["id"] == body.cluster_id), None)
    if not cluster:
        raise HTTPException(404, "Fire cluster not found in the last 7 days")
    return {"cluster": cluster, "impact": impact.assess(impact.hazard_from_points(cluster["points"], body.radius_m), "fire")}


# ---------------------------------------------------------------- alerts
def _alert_out(a: Alert) -> dict[str, Any]:
    return {c: getattr(a, c) for c in ("id", "key", "hazard", "severity", "title", "message", "district", "latitude", "longitude", "source", "source_url", "observed_value", "threshold", "unit", "valid_from", "valid_until", "status", "acknowledged_by", "acknowledged_at", "payload", "created_at", "updated_at")}


@router.get("/alerts")
def list_alerts(status: str | None = "open", hazard: str | None = None, severity: str | None = None, db: Session = Depends(get_db)):
    q = select(Alert)
    if status == "open":
        q = q.where(Alert.status.in_(("ACTIVE", "ACKNOWLEDGED")))
    elif status and status != "all":
        q = q.where(Alert.status == status.upper())
    if hazard:
        q = q.where(Alert.hazard == hazard)
    if severity:
        q = q.where(Alert.severity == severity.upper())
    rows = db.scalars(q.order_by(Alert.updated_at.desc()).limit(500)).all()
    rank = alert_svc.SEVERITY_RANK
    rows = sorted(rows, key=lambda a: (a.status != "ACTIVE", -rank.get(a.severity, 0)))
    return {"items": [_alert_out(a) for a in rows], "total": len(rows)}


@router.post("/alerts/refresh")
def refresh_alerts(db: Session = Depends(get_db)):
    return alert_svc.refresh(db)


@router.get("/alerts/stream")
async def alert_stream(request: Request):
    sub = events.subscribe()

    async def gen():
        try:
            yield f"data: {json.dumps({'type': 'hello'})}\n\n"
            while not await request.is_disconnected():
                try:
                    ev = await asyncio.wait_for(sub[1].get(), timeout=15)
                    yield f"data: {json.dumps(ev, default=str)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            events.unsubscribe(sub)

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/alerts/events")
def alert_events(since: str | None = None):
    items = events.recent(since)
    return {"items": items, "total": len(items)}


class ActorBody(BaseModel):
    actor: str = Field("operator", max_length=80)


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge(alert_id: str, body: ActorBody = ActorBody(), db: Session = Depends(get_db)):
    try:
        return _alert_out(alert_svc.set_status(db, alert_id, "ACKNOWLEDGED", body.actor))
    except KeyError:
        raise HTTPException(404, "Alert not found") from None


@router.post("/alerts/{alert_id}/resolve")
def resolve(alert_id: str, body: ActorBody = ActorBody(), db: Session = Depends(get_db)):
    try:
        return _alert_out(alert_svc.set_status(db, alert_id, "RESOLVED", body.actor))
    except KeyError:
        raise HTTPException(404, "Alert not found") from None


# ---------------------------------------------------------------- analytics & rescue
@router.get("/analytics")
def analytics(db: Session = Depends(get_db)):
    return analytics_svc.analytics(db)


@router.get("/rescue/plan")
def rescue_plan(lat: float = Query(..., ge=11.0, le=19.0), lon: float = Query(..., ge=73.5, le=79.0)):
    return rescue.plan(lat, lon)


# ---------------------------------------------------------------- vision
@router.get("/vision/status")
def vision_status():
    return vision.status()


def _vision_out(job: VisionJob) -> dict[str, Any]:
    return {"id": job.id, "filename": job.filename, "model": job.model_name, "detections": job.detections, "summary": job.summary, "processing_ms": job.processing_ms, "image_url": f"/api/v1/vision/jobs/{job.id}/image", "created_at": job.created_at}


@router.post("/vision/detect")
def vision_detect(file: UploadFile = File(...), db: Session = Depends(get_db)):
    limit = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB")
    try:
        img = vision.decode(file.filename or "", data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    dets, annotated, ms = vision.detect(img)
    job = VisionJob(filename=Path(file.filename or "upload").name[:200], model_name=settings.yolo_model, detections=dets, summary=vision.summarize(dets), annotated_path="", processing_ms=round(ms, 1))
    db.add(job)
    db.flush()
    out = Path(settings.storage_dir) / "vision" / f"{job.id}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), annotated)
    job.annotated_path = str(out)
    db.commit()
    return _vision_out(job)


@router.get("/vision/jobs/{job_id}/image")
def vision_image(job_id: str, db: Session = Depends(get_db)):
    job = db.get(VisionJob, job_id)
    if not job or not Path(job.annotated_path).is_file():
        raise HTTPException(404, "Image not found")
    return FileResponse(job.annotated_path, media_type="image/jpeg")


@router.get("/vision/jobs")
def vision_jobs(db: Session = Depends(get_db)):
    rows = db.scalars(select(VisionJob).order_by(VisionJob.created_at.desc()).limit(20)).all()
    return {"items": [_vision_out(j) for j in rows]}

