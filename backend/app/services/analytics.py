"""Trends computed from live feeds and the stored alert/observation history."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import SourceUnavailable
from app.db import Alert, Analysis, Observation, utcnow
from app.services import fire, rainfall, water


def _safe(fn):
    try:
        return {"status": "live", **fn()}
    except SourceUnavailable as exc:
        return {"status": "unavailable", "detail": exc.message}


def _fires() -> dict[str, Any]:
    det = fire.detections("7d")["detections"]
    industrial = [c["bbox"] for c in fire.clusters("7d") if c["persistent_heat_source"]]

    def is_ind(d):
        return any(b[0] - 0.01 <= d["longitude"] <= b[2] + 0.01 and b[1] - 0.01 <= d["latitude"] <= b[3] + 0.01 for b in industrial)

    daily: dict[str, Counter] = defaultdict(Counter)
    by_district: Counter = Counter()
    for d in det:
        kind = "industrial" if is_ind(d) else "vegetation"
        daily[d["acquired_at"][:10]][kind] += 1
        if kind == "vegetation":
            by_district[d["district"]] += 1
    days = sorted(daily)
    return {
        "days": days,
        "vegetation": [daily[d]["vegetation"] for d in days],
        "industrial": [daily[d]["industrial"] for d in days],
        "by_district": dict(by_district.most_common(12)),
    }


def _rain() -> dict[str, Any]:
    ds = rainfall.districts()
    dates = [p["date"] for p in ds[0]["series"]] if ds else []
    avg = []
    for i, _ in enumerate(dates):
        vals = [d["series"][i]["rain_mm"] for d in ds if d["series"][i]["rain_mm"] is not None]
        avg.append(round(sum(vals) / len(vals), 1) if vals else None)
    forecast = [p["forecast"] for p in ds[0]["series"]] if ds else []
    return {
        "dates": dates,
        "state_mean_mm": avg,
        "forecast": forecast,
        "wettest_30d": sorted(({"name": d["name"], "mm": d["observed_30d_mm"]} for d in ds), key=lambda r: -r["mm"])[:10],
    }


def _rivers() -> dict[str, Any]:
    st = water.stations()
    return {
        "stations": [
            {
                "id": s["id"],
                "name": s["name"],
                "status": s["status"],
                "q2": (s["thresholds"] or {}).get("q2"),
                "dates": [p["date"] for p in s["series"]],
                "discharge": [p["discharge"] for p in s["series"]],
                "forecast_from": next((p["date"] for p in s["series"] if p["forecast"]), None),
            }
            for s in st[:8]
        ]
    }


def analytics(db: Session) -> dict[str, Any]:
    since = utcnow() - timedelta(days=30)
    alerts = db.scalars(select(Alert).where(Alert.created_at >= since)).all()
    per_day: dict[str, Counter] = defaultdict(Counter)
    for a in alerts:
        per_day[a.created_at.date().isoformat()][a.hazard] += 1
    days = sorted(per_day)
    hazards = sorted({h for c in per_day.values() for h in c})
    obs = db.scalars(select(Observation).where(Observation.kind == "fire_detections_24h").order_by(Observation.observed_at)).all()
    analyses = db.scalars(select(Analysis).order_by(Analysis.created_at.desc()).limit(50)).all()
    return {
        "fires": _safe(_fires),
        "rain": _safe(_rain),
        "rivers": _safe(_rivers),
        "alerts": {
            "days": days,
            "series": {h: [per_day[d][h] for d in days] for h in hazards},
            "by_severity": dict(Counter(a.severity for a in alerts)),
            "total_30d": len(alerts),
        },
        "fire_history": {"times": [o.observed_at.isoformat() for o in obs], "detections_24h": [o.value for o in obs]},
        "analyses": [
            {
                "id": a.id,
                "kind": a.kind,
                "area_name": a.area_name,
                "created_at": a.created_at.isoformat(),
                "hazard_km2": a.metrics.get("newly_flooded_km2", a.metrics.get("burned_area_km2")),
                "buildings": ((a.impact or {}).get("exposed") or {}).get("buildings"),
                "road_km": ((a.impact or {}).get("exposed") or {}).get("road_km"),
                "loss_crore": ((a.impact or {}).get("loss") or {}).get("estimated_loss_crore"),
            }
            for a in analyses
        ],
    }
