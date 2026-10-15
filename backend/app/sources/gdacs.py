"""GDACS (Global Disaster Alert and Coordination System) events for India."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.core import http

URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
TYPES = {"FL": "flood", "TC": "cyclone", "EQ": "earthquake", "DR": "drought", "WF": "wildfire", "VO": "volcano", "TS": "tsunami"}


@http.ttl_cache(1800)
def india_events(days: int = 90) -> list[dict[str, Any]]:
    today = date.today()
    data = http.get_json(
        "gdacs",
        URL,
        params={"country": "India", "fromDate": (today - timedelta(days=days)).isoformat(), "toDate": today.isoformat()},
    )
    events = []
    for f in (data or {}).get("features", []):
        p = f.get("properties") or {}
        coords = (f.get("geometry") or {}).get("coordinates") or [None, None]
        events.append(
            {
                "id": f"gdacs-{p.get('eventtype')}-{p.get('eventid')}",
                "hazard": TYPES.get(p.get("eventtype"), str(p.get("eventtype")).lower()),
                "name": p.get("name"),
                "description": p.get("description"),
                "alert_level": p.get("alertlevel"),
                "alert_score": p.get("alertscore"),
                "is_current": str(p.get("iscurrent")).lower() == "true",
                "from_date": p.get("fromdate"),
                "to_date": p.get("todate"),
                "longitude": coords[0],
                "latitude": coords[1],
                "severity": (p.get("severitydata") or {}).get("severitytext"),
                "countries": p.get("affectedcountries"),
                "glide": p.get("glide"),
                "report_url": (p.get("url") or {}).get("report"),
                "source": "GDACS",
            }
        )
    return events
