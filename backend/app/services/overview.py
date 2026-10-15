"""Dashboard aggregate. Each section reports its own status; a failed source is shown as unavailable."""

from __future__ import annotations

from collections import Counter
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import SourceUnavailable
from app.db import Alert, Analysis
from app.geo.karnataka import KARNATAKA_BBOX, in_karnataka
from app.services import fire, rainfall, water
from app.sources import gdacs


def _section(fn: Callable[[], Any]) -> dict[str, Any]:
    try:
        return {"status": "live", "data": fn()}
    except SourceUnavailable as exc:
        return {"status": "unavailable", "source": exc.source, "detail": exc.message}


def _water() -> dict[str, Any]:
    st = water.stations(include_series=False)
    return {
        "stations": st,
        "by_status": dict(Counter(s["status"] for s in st)),
        "highest": st[0] if st else None,
    }


def _fire() -> dict[str, Any]:
    det = fire.detections("24h")
    cl = fire.clusters("7d")
    wild = [c for c in cl if not c["persistent_heat_source"]]
    return {
        "detections_24h": det["count"],
        "detections_24h_points": [
            {"latitude": d["latitude"], "longitude": d["longitude"], "frp_mw": d["frp_mw"], "confidence": d["confidence"], "acquired_at": d["acquired_at"], "district": d["district"]}
            for d in det["detections"]
        ],
        "active_clusters": [c for c in wild if c["active_24h"]],
        "clusters_7d": len(wild),
        "industrial_sources": [c for c in cl if c["persistent_heat_source"]],
        "by_district_24h": dict(Counter(d["district"] for d in det["detections"]).most_common(10)),
    }


def _rain() -> dict[str, Any]:
    ds = rainfall.districts()
    return {
        "districts": [{k: v for k, v in d.items() if k != "series"} for d in ds],
        "heavy_forecast": [d["name"] for d in ds if d["alert_level"] != "NORMAL"],
        "wettest_7d": max(ds, key=lambda d: d["observed_7d_mm"])["name"] if ds else None,
    }


def _events() -> list[dict[str, Any]]:
    w, s, e, n = KARNATAKA_BBOX
    out = []
    for ev in gdacs.india_events():
        if ev["latitude"] is None:
            continue
        near = s - 1 <= ev["latitude"] <= n + 1 and w - 1 <= ev["longitude"] <= e + 1
        out.append({**ev, "near_karnataka": near, "inside_karnataka": near and in_karnataka(ev["latitude"], ev["longitude"])})
    return sorted(out, key=lambda e: (not e["near_karnataka"], not e["is_current"], e["from_date"] or ""), reverse=False)


def overview(db: Session) -> dict[str, Any]:
    alerts = db.scalars(select(Alert).where(Alert.status.in_(("ACTIVE", "ACKNOWLEDGED")))).all()
    analyses = db.scalars(select(Analysis).order_by(Analysis.created_at.desc()).limit(6)).all()
    return {
        "alerts": {
            "open": len(alerts),
            "by_severity": dict(Counter(a.severity for a in alerts)),
            "by_hazard": dict(Counter(a.hazard for a in alerts)),
        },
        "water": _section(_water),
        "fire": _section(_fire),
        "rain": _section(_rain),
        "events": _section(_events),
        "recent_analyses": [
            {"id": a.id, "kind": a.kind, "area_name": a.area_name, "created_at": a.created_at, "metrics": a.metrics, "impact_summary": (a.impact or {}).get("exposed"), "loss": ((a.impact or {}).get("loss") or {}).get("estimated_loss_crore"), "bbox": a.bbox}
            for a in analyses
        ],
    }
