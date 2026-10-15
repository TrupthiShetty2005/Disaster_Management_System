# VisionGuard — Module Data Provenance Status

**Verified:** 2026-10-05 (local runtime probe)  
**Backend:** `USE_MOCK_PROVIDERS=false` → health `REAL DATA`  
**Frontend:** `VITE_USE_MOCK=false` → calls `/api/v1`  
**Source of truth API:** `GET /api/v1/data-sources/status?probe=true`

## Build / reflection check

| Check | Result |
| --- | --- |
| Backend health LIVE | YES (`data_mode=REAL DATA`, `use_mock_providers=false`) |
| Provenance endpoint | YES — all modules returned |
| OpenWeather live | YES (`provider_live=true`) |
| GIS Overpass | YES — 80 features, `STATIC_EXTERNAL` |
| Provenance unit tests | YES — 3 passed |
| Frontend HTTP | YES — `http://localhost:5173` → 200 |
| UI global mode badge | YES — Header `LIVE DATA MODE` / `DEMO MODE` |
| UI per-module panel | YES — layout `DataSourcePanel` + page `ModuleProvenance` |

**Complete feature build for this live-transparency pass: YES** (live Docker overlay, provenance API, OSM GIS, honest labels). Not a claim that every product gap (IMD, YOLO, auth) is finished.

---

## Module table (LIVE / DERIVED / STATIC / SEEDED / MOCK / …)

| Module | Status | Provider | Real-world? | UI shows it? |
| --- | --- | --- | --- | --- |
| Weather (current/forecast) | **LIVE** | OpenWeather | YES | Header panel + Weather page provenance |
| Weather history | **LIVE** | NASA POWER | YES | Header panel + Weather page |
| Satellite catalogue/previews | **LIVE** | Copernicus CDSE STAC | YES | Header panel + Flood page |
| Flood change analysis | **DERIVED_LIVE** | Sentinel-2 RGB heuristic | Derived from real previews | Flood page + panel |
| Damage analysis | **DERIVED_LIVE** | Sentinel-2 change heuristic | Derived | Panel |
| Risk (flood/cyclone %) | **DERIVED_LIVE** | VisionGuard rules | Derived (not official) | Weather page + panel |
| Alerts (engine) | **DERIVED_LIVE** | VisionGuard (+ IMD if key) | Signals from live weather | Panel; Alerts page banner |
| GIS (OSM Overpass API) | **STATIC_EXTERNAL** | OpenStreetMap Overpass | Reference geo (not live incidents) | Situation page + panel |
| Situation map catalog polygons | **MOCK** | `gisMock.ts` demo GeoJSON | NO | Situation page text + GIS provenance note |
| Resources / rescue inventory | **SEEDED** | DB `seed.py` | NO | Panel |
| Disaster incidents | **SEEDED** | DB `seed.py` | NO | Situation page + panel |
| Analytics KPIs | **DERIVED_LIVE** (mixed) | Live flood/risk + seeded counts | Mixed | Panel; KPI hints on dashboard |
| IMD official warnings | **NOT_CONFIGURED** | IMD (no key) | NO | Weather page + panel |
| Vision / YOLO | **NOT_CONFIGURED** | Local YOLO weights missing | NO | Panel |
| River / gauge level | **UNAVAILABLE** | None wired | NO — not invented | Weather page + panel |
| Notifications (SMS/email/push) | **MOCK** | Unwired adapters | NO | Panel |

### Status legend (also used as UI badge text)

| Badge | Meaning |
| --- | --- |
| LIVE DATA | External API called successfully |
| DERIVED FROM LIVE DATA | Computed from live inputs (heuristic/rules) |
| STATIC EXTERNAL DATA | Authoritative reference dataset (e.g. OSM), not real-time telemetry |
| SEEDED DATA | Application DB demo inventory |
| MOCK DATA | Synthetic / demo provider or FE mock |
| NOT CONFIGURED | Credentials/weights missing |
| UNAVAILABLE | Live path failed or not available |

---

## Where the UI shows live vs mock vs seed

1. **Header** — global `LIVE DATA MODE` or `DEMO MODE` (`DataModeBadge`).
2. **Every page (layout)** — compact safety note + **Data provenance panel** listing each module badge.
3. **Weather / Flood / Situation** — `ModuleProvenance` cards with “Why this data?” (provider, method, limitations).
4. **Settings / Alerts** — fuller `SafetyBanner` + panel.
5. **API** — `GET /api/v1/data-sources/status` drives the badges (not hard-coded LIVE).

---

## How to re-verify

```bash
# Backend
curl http://127.0.0.1:8000/api/v1/health
curl "http://127.0.0.1:8000/api/v1/data-sources/status?probe=true"

# Frontend (VITE_USE_MOCK=false)
# Open http://localhost:5173 — confirm LIVE DATA MODE + module grid
```

Docker LIVE:

```bash
cp .env.live.example .env.live   # set OPENWEATHER_API_KEY
docker compose --env-file .env.live -f docker-compose.yml -f docker-compose.live.yml up --build
```
