"""Alert engine: turns live conditions into deduplicated alerts and records observations."""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import SourceUnavailable
from app.db import Alert, Observation, utcnow
from app.geo.karnataka import KARNATAKA_BBOX, in_karnataka
from app.services import events, fire, rainfall, water

log = logging.getLogger("visionguard.alerts")
SEVERITY_RANK = {"INFO": 0, "WATCH": 1, "WARNING": 2, "SEVERE": 3}
OPEN = ("ACTIVE", "ACKNOWLEDGED")
GDACS_LEVEL = {"Green": "INFO", "Orange": "WARNING", "Red": "SEVERE"}
NEAR_KARNATAKA_DEG = 1.0


def _end_of(day: str, extra_days: int = 1) -> datetime:
    return datetime.combine(datetime.fromisoformat(day).date() + timedelta(days=extra_days), time(0), tzinfo=timezone.utc)


def _water_conditions() -> list[dict[str, Any]]:
    out = []
    level_name = {"WATCH": "2-year", "WARNING": "5-year", "SEVERE": "20-year"}
    for st in water.stations(include_series=False):
        if st["status"] not in level_name:
            continue
        peak = st["forecast_peak"]["expected"] or st["current"]
        th = st["thresholds"]
        thr = {"WATCH": th["q2"], "WARNING": th["q5"], "SEVERE": th["q20"]}[st["status"]]
        when = "now" if st["current_level"] == st["status"] else f"by {peak['date']}"
        out.append(
            {
                "key": f"water:{st['id']}",
                "hazard": "flood",
                "severity": st["status"],
                "title": f"{st['name']} ({st['river']}): flow at {level_name[st['status']]} flood level {when}",
                "message": (
                    f"GloFAS discharge {peak['discharge']:.0f} m³/s ({peak['date']}) vs {level_name[st['status']]} return level "
                    f"{thr:.0f} m³/s. Current {st['current']['discharge']:.0f} m³/s, 7-day trend {st['trend_7d_pct']}%. "
                    "Check downstream villages and reservoir release schedules."
                ),
                "district": st["district"],
                "latitude": st["latitude"],
                "longitude": st["longitude"],
                "source": "GloFAS v4 via Open-Meteo",
                "observed_value": peak["discharge"],
                "threshold": thr,
                "unit": "m³/s",
                "valid_until": _end_of(peak["date"], 2),
                "payload": {"station_id": st["id"]},
            }
        )
    return out


def _rain_conditions() -> list[dict[str, Any]]:
    out = []
    for d in rainfall.districts():
        if d["alert_level"] == "NORMAL" or not d["peak_day"]:
            continue
        p = d["peak_day"]
        out.append(
            {
                "key": f"rain:{d['id']}",
                "hazard": "rain",
                "severity": d["alert_level"],
                "title": f"{d['name']}: {d['category'].replace('_', ' ').lower()} rainfall forecast on {p['date']}",
                "message": f"{p['rain_mm']:.0f} mm forecast in 24 h at {d['hq']} (IMD category {d['category'].replace('_', ' ').title()}). 3-day total {d['forecast_3d_mm']} mm.",
                "district": d["name"],
                "latitude": d["latitude"],
                "longitude": d["longitude"],
                "source": "Open-Meteo forecast",
                "observed_value": p["rain_mm"],
                "threshold": 64.5,
                "unit": "mm/24h",
                "valid_until": _end_of(p["date"]),
                "payload": {"district_id": d["id"]},
            }
        )
    return out


def _fire_conditions() -> list[dict[str, Any]]:
    out = []
    for c in fire.clusters("7d"):
        if c["persistent_heat_source"] or not c["active_24h"] or c["severity"] == "INFO":
            continue
        grid = f"{round(c['latitude'] * 20) / 20:.2f}:{round(c['longitude'] * 20) / 20:.2f}"
        last = datetime.fromisoformat(c["last_seen"])
        out.append(
            {
                "key": f"fire:{grid}",
                "hazard": "fire",
                "severity": c["severity"],
                "title": f"Active fire in {c['district']}: {c['detections']} satellite detections",
                "message": f"{c['detections']} FIRMS detections ({c['high_confidence']} high confidence), total FRP {c['total_frp_mw']} MW, last seen {c['last_seen'][:16].replace('T', ' ')} UTC by {', '.join(c['sensors'])}.",
                "district": c["district"],
                "latitude": c["latitude"],
                "longitude": c["longitude"],
                "source": "NASA FIRMS",
                "observed_value": c["total_frp_mw"],
                "threshold": None,
                "unit": "MW",
                "valid_until": last + timedelta(hours=36),
                "payload": {"cluster_id": c["id"], "points": c["points"][:200]},
            }
        )
    for d in fire.danger_forecast():
        if d["peak_level"] not in {"VERY_HIGH", "EXTREME"}:
            continue
        peak = max(d["days"], key=lambda x: x["ffwi"])
        out.append(
            {
                "key": f"firedanger:{d['id']}",
                "hazard": "fire",
                "severity": "WARNING" if d["peak_level"] == "EXTREME" else "WATCH",
                "title": f"{d['name']}: {d['peak_level'].replace('_', ' ').lower()} fire danger forecast",
                "message": f"Fosberg FWI {peak['ffwi']} on {peak['date']} (max {peak['temp_max_c']}°C, min RH {peak['rh_min_pct']}%, wind {peak['wind_max_kmh']} km/h); {d['active_detections_48h']} detections in 48 h.",
                "district": d["name"],
                "latitude": d["latitude"],
                "longitude": d["longitude"],
                "source": "Open-Meteo + NASA FIRMS",
                "observed_value": peak["ffwi"],
                "threshold": 50.0,
                "unit": "FFWI",
                "valid_until": _end_of(d["days"][-1]["date"]),
                "payload": {"district_id": d["id"]},
            }
        )
    return out


def _gdacs_conditions() -> list[dict[str, Any]]:
    from app.sources import gdacs

    w, s, e, n = KARNATAKA_BBOX
    out = []
    for ev in gdacs.india_events():
        lat, lon = ev["latitude"], ev["longitude"]
        if not ev["is_current"] or lat is None:
            continue
        if not (s - NEAR_KARNATAKA_DEG <= lat <= n + NEAR_KARNATAKA_DEG and w - NEAR_KARNATAKA_DEG <= lon <= e + NEAR_KARNATAKA_DEG):
            continue
        inside = in_karnataka(lat, lon)
        out.append(
            {
                "key": f"gdacs:{ev['id']}",
                "hazard": ev["hazard"],
                "severity": GDACS_LEVEL.get(ev["alert_level"], "INFO"),
                "title": f"GDACS {ev['alert_level']} {ev['hazard']}: {ev['name']}" + ("" if inside else " (near Karnataka)"),
                "message": f"{ev['description'] or ev['name']}. {ev.get('severity') or ''} Active {ev['from_date'][:10]} to {ev['to_date'][:10]}.",
                "district": None,
                "latitude": lat,
                "longitude": lon,
                "source": "GDACS",
                "source_url": ev["report_url"],
                "observed_value": ev.get("alert_score"),
                "threshold": None,
                "unit": None,
                "valid_until": datetime.fromisoformat(ev["to_date"]).replace(tzinfo=timezone.utc) + timedelta(days=2),
                "payload": {"glide": ev.get("glide"), "inside_karnataka": inside},
            }
        )
    return out


FAMILIES = {"water": _water_conditions, "rain": _rain_conditions, "fire": _fire_conditions, "gdacs": _gdacs_conditions}


def _operator_resolved(db: Session, cond: dict[str, Any]) -> bool:
    """An operator closed this exact condition and its validity window has not ended — don't re-raise it."""
    last = db.scalars(select(Alert).where(Alert.key == cond["key"], Alert.status == "RESOLVED").order_by(Alert.updated_at.desc())).first()
    if last is None or not str((last.payload or {}).get("resolved_reason", "")).startswith("Resolved by"):
        return False
    if SEVERITY_RANK[cond["severity"]] > SEVERITY_RANK.get(last.severity, 0):
        return False
    vu = last.valid_until
    if vu is None:
        return False
    vu = vu if vu.tzinfo else vu.replace(tzinfo=timezone.utc)
    return vu > utcnow()


def _upsert(db: Session, cond: dict[str, Any]) -> str:
    existing = db.scalars(select(Alert).where(Alert.key == cond["key"], Alert.status.in_(OPEN))).first()
    fields = {k: v for k, v in cond.items() if k != "key"}
    if existing is None and _operator_resolved(db, cond):
        return "suppressed"
    if existing is None:
        alert = Alert(key=cond["key"], status="ACTIVE", **fields)
        db.add(alert)
        db.flush()
        events.publish({"type": "alert_created", "id": alert.id, "severity": alert.severity, "title": alert.title})
        return "created"
    escalated = SEVERITY_RANK[cond["severity"]] > SEVERITY_RANK[existing.severity]
    for k, v in fields.items():
        setattr(existing, k, v)
    if escalated:
        existing.status = "ACTIVE"
        events.publish({"type": "alert_escalated", "id": existing.id, "severity": existing.severity, "title": existing.title})
    return "updated"


def _record_observations(db: Session) -> None:
    now = utcnow()
    for st in water.stations(include_series=False):
        if not st["current"]:
            continue
        day = datetime.fromisoformat(st["current"]["date"]).replace(tzinfo=timezone.utc)
        seen = db.scalars(select(Observation).where(Observation.kind == "discharge", Observation.entity == st["id"], Observation.observed_at == day)).first()
        if not seen:
            db.add(Observation(kind="discharge", entity=st["id"], observed_at=day, value=st["current"]["discharge"], source="GloFAS", payload={"status": st["status"]}))
    det = fire.detections("24h")
    db.add(Observation(kind="fire_detections_24h", entity="karnataka", observed_at=now, value=det["count"], source="NASA FIRMS"))


def refresh(db: Session) -> dict[str, Any]:
    summary: dict[str, Any] = {"created": 0, "updated": 0, "suppressed": 0, "resolved": 0, "expired": 0, "errors": {}}
    now = utcnow()
    for family, fn in FAMILIES.items():
        try:
            conds = fn()
        except SourceUnavailable as exc:
            summary["errors"][family] = exc.message
            continue
        keys = set()
        for cond in conds:
            keys.add(cond["key"])
            summary[_upsert(db, cond)] += 1
        prefixes = {"water": ("water:",), "rain": ("rain:",), "fire": ("fire:", "firedanger:"), "gdacs": ("gdacs:",)}[family]
        for alert in db.scalars(select(Alert).where(Alert.status.in_(OPEN))):
            if alert.key.startswith(prefixes) and alert.key not in keys:
                alert.status = "RESOLVED"
                alert.payload = {**(alert.payload or {}), "resolved_reason": "Condition no longer present in live data", "resolved_at": now.isoformat()}
                summary["resolved"] += 1
                events.publish({"type": "alert_resolved", "id": alert.id, "title": alert.title})
    for alert in db.scalars(select(Alert).where(Alert.status.in_(OPEN), Alert.valid_until.is_not(None))):
        vu = alert.valid_until if alert.valid_until.tzinfo else alert.valid_until.replace(tzinfo=timezone.utc)
        if vu < now:
            alert.status = "EXPIRED"
            summary["expired"] += 1
    try:
        _record_observations(db)
    except SourceUnavailable as exc:
        summary["errors"]["observations"] = exc.message
    db.commit()
    summary["refreshed_at"] = now.isoformat()
    events.publish({"type": "refresh", **{k: v for k, v in summary.items() if k != "errors"}})
    log.info("alert refresh: %s", summary)
    return summary


def set_status(db: Session, alert_id: str, status: str, actor: str) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise KeyError(alert_id)
    alert.status = status
    if status == "ACKNOWLEDGED":
        alert.acknowledged_by = actor
        alert.acknowledged_at = utcnow()
    else:
        alert.payload = {**(alert.payload or {}), "resolved_reason": f"Resolved by {actor}", "resolved_at": utcnow().isoformat()}
    db.commit()
    events.publish({"type": f"alert_{status.lower()}", "id": alert.id, "title": alert.title})
    return alert
