# VisionGuard AI — Complete Code Architecture

This document is the **single map of how the project is built**: folders, layers, data modes, APIs, models, and request flow. It matches the code as of this repository (product API = `backend/`, UI = `frontend/`).

**Product name:** VisionGuard AI  
**Purpose:** Disaster operations **decision-support** console (precaution → response → recovery). **REAL DATA default AOI is Karnataka / Bengaluru, India.** A **Kuttanad / Alappuzha, Kerala** flood case file exists only in explicitly enabled **Demo Mode**.  
**Not:** official IMD/NDMA warning system, trained U-Net flood product, live government SMS, live rescue vehicles, or river gauges.

---

## 1. What is built (system in one picture)

```
 External APIs                          Product stack
 ┌─────────────────────┐
 │ OpenWeather         │── current/forecast
 │ NASA POWER          │── daily history
 │ Copernicus CDSE STAC│── Sentinel-2 catalogue + RGB previews
 │ OSM Overpass        │── reference GIS (roads, amenities)
 │ IMD (optional)      │── official warnings if key set
 └──────────┬──────────┘
            │ HTTP (httpx)
            ▼
 ┌──────────────────────────────────────────────────────────┐
 │ FastAPI  backend/app  prefix /api/v1                     │
 │  main.py → router.py → services → providers / OpenCV     │
 │  SQLAlchemy  SQLite (dev) or PostGIS Postgres (Docker)   │
 │  seed.py  demo incident + boats + centers                │
 └────────────────────────────┬─────────────────────────────┘
                              │ REST JSON + SSE
                              ▼
 ┌──────────────────────────────────────────────────────────┐
 │ React SPA  frontend/  Vite + TS + Tailwind + Leaflet     │
 │  App.tsx routes → pages → services/*.ts → apiClient.ts   │
 │  DataModeBadge / provenance from /data-sources/status    │
 └──────────────────────────────────────────────────────────┘
```

**Live AOI (REAL DATA — default)**

| Constant | Value | Files |
| --- | --- | --- |
| AOI name | Karnataka / Bengaluru (India) | `backend/app/core/config.py` `aoi_name` / `AOI_NAME` |
| Center | lat **12.9716**, lon **77.5946** | `demo_latitude` / `demo_longitude` (legacy env names) |
| Weather query | **Bengaluru,IN** | `OPENWEATHER_QUERY` |
| Map center | same | `frontend/src/constants/demo.ts` `LIVE_MAP_CENTER` |

**Canonical demo incident (Demo Mode only — `USE_MOCK_PROVIDERS=true`)**

| Constant | Value | Files |
| --- | --- | --- |
| Incident ID | `aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa` | `frontend/src/constants/demo.ts`, `backend/app/core/demo.py`, `backend/app/db/seed.py` |
| Location ID | `11111111-1111-4111-8111-111111111111` | same |
| AOI | lat **9.517**, lon **76.522** (Kuttanad) | seed + mock satellite/GIS only |
| Weather city (demo) | Alappuzha in mock weather fixtures | `frontend/src/data/mock.ts` |

---

## 2. Repository tree (what each top folder is for)

```
Disaster_Management_System/
├── frontend/                 # Officer UI (Vite React TypeScript)
├── backend/                  # Product API (FastAPI) — THIS is the live system
├── ai/                       # Optional CV interfaces / stubs (runtime flood/vision is in backend)
├── src/                      # LEGACY weather/NASA/NOAA experiments — NOT the product API
├── data/mock/                # Tiny demo satellite placeholder files
├── docker/                   # Dockerfiles
├── docker-compose.yml        # Stack env (current file defaults USE_MOCK_PROVIDERS=false)
├── docker-compose.live.yml   # Extra live-data overlay
├── docs/                     # Architecture, provenance, presentation
├── scripts/                  # Extra seed helpers
├── .env.example / .env.live.example
└── README.md
```

**Use `backend/` + `frontend/` only for the product.** `src/` is leftover and must not be presented as the running architecture.

---

## 3. Two operating modes (how the build switches data)

| Mode | Backend | Frontend | Behaviour |
| --- | --- | --- | --- |
| **LIVE DATA MODE** | `USE_MOCK_PROVIDERS=false` | `VITE_USE_MOCK=false` | Real HTTP to providers. Failures → 503 / UNAVAILABLE. **No silent mock.** |
| **DEMO MODE** | `USE_MOCK_PROVIDERS=true` | `VITE_USE_MOCK=true` | Mock providers + `frontend/src/data/mock.ts`. Allowed and labeled. |

| Switch | File |
| --- | --- |
| Backend flag | `backend/app/core/config.py` → `use_mock_providers` |
| Frontend flag | `frontend/src/services/apiClient.ts` → `isMockMode()` is **true only when** `VITE_USE_MOCK === "true"` |
| Docker | `docker-compose.yml`; live overlay `docker-compose.live.yml` |

Honesty labels: `GET /api/v1/data-sources/status` → `backend/app/services/provenance.py` → UI `DataModeBadge.tsx`.

| Status | Meaning |
| --- | --- |
| LIVE | External API succeeded |
| DERIVED_LIVE | Computed from live inputs (OpenCV / rules) |
| STATIC_EXTERNAL | OSM Overpass reference map (not flood telemetry) |
| SEEDED | SQLite/Postgres rows from `seed.py` |
| MOCK | Synthetic adapters |
| NOT_CONFIGURED | Missing key / YOLO weights |
| UNAVAILABLE | Live path failed or not wired (e.g. river gauge) |

---

## 4. Backend architecture (how FastAPI is layered)

Startup (`backend/app/main.py`):

1. `configure_logging()`
2. `init_db()` — create tables
3. `seed_if_empty()` — **Demo Mode only**; REAL DATA does not load the Kuttanad case file
4. `log_live_startup_banner()` — LIVE vs DEMO
5. CORS + exception handlers
6. Mount router at `/api/v1`

```
HTTP
  backend/app/api/v1/router.py          # all REST endpoints
        ↓
  app/schemas/common.py                 # Pydantic request/response
        ↓
  app/services/*                        # business logic (orchestration)
        ↓
  providers (weather, satellite, GIS)   # live HTTP or mock
  OpenCV processing                     # flood/damage/satellite
  app/repositories/ops.py               # extra persistence helpers
        ↓
  app/models/entities.py                # SQLAlchemy tables
  app/db/session.py                     # engine / SessionLocal
```

### 4.1 Backend folder map

| Path | Role |
| --- | --- |
| `backend/app/main.py` | FastAPI app |
| `backend/app/core/config.py` | Env settings |
| `backend/app/core/demo.py` | Shared incident IDs / narrative |
| `backend/app/core/errors.py` | HTTP error mapping (`ProviderUnavailableError` → 503) |
| `backend/app/core/logging.py` | Logging |
| `backend/app/core/providers.py` | Provider error type |
| `backend/app/api/v1/router.py` | **All HTTP routes** |
| `backend/app/schemas/common.py` | API contracts |
| `backend/app/models/entities.py` | ORM |
| `backend/app/db/session.py` | DB engine |
| `backend/app/db/init_db.py` | Create schema |
| `backend/app/db/seed.py` | Demo inventory |
| `backend/app/services/provenance.py` | Data-source status |
| `backend/app/services/weather/` | OpenWeather, NASA, IMD, mock, factory, live composite |
| `backend/app/services/weather_intel.py` | Weather + rainfall + flood/cyclone risk |
| `backend/app/services/risk/` | Flood/cyclone/rainfall formulas + alert pipeline |
| `backend/app/services/satellite/` | Copernicus STAC, mock, processing, service |
| `backend/app/services/flood/` | Flood analyze orchestration, geo, model wrappers |
| `backend/app/services/damage/` | Damage analyze, classify, report |
| `backend/app/services/gis/overpass.py` | OSM Overpass cache/proxy |
| `backend/app/services/alerts/` | Engine, rules.json, notifications, SSE |
| `backend/app/services/rescue/` | Priorities, recommend, routing, plans |
| `backend/app/services/vision/` | DemoVision, YOLO, factory, pipeline, storage |
| `backend/app/services/incident/` | Incident command aggregate |
| `backend/app/services/analytics/` | KPI rollups |
| `backend/app/services/reports/` | JSON reports |
| `backend/app/services/ops.py` | Resources / extra ops |
| `backend/tests/` | Pytest |

### 4.2 API surface (`/api/v1`)

| Area | Methods (representative) |
| --- | --- |
| Health / provenance | `GET /health`, `GET /data-sources/status` |
| GIS | `GET /gis/features` |
| Disasters | `GET /disasters`, `GET /disasters/{id}` |
| Risk | `GET /risk-zones`, `/risk/flood`, `/risk/cyclone` |
| Weather | `/weather/current`, `/forecast`, `/history`, `/rainfall`, `/alerts` |
| Alerts | list, generate, ack, resolve, SSE `/alerts/stream` |
| Rescue | resources, allocate, priorities, plan, decision, centers |
| Satellite | images, preview, analyze, compare |
| Vision | health, detect, analyze, annotated image |
| Flood | `POST /flood/analyze`, events |
| Damage | `POST /damage/analyze`, assessments |
| Analytics | overview, disasters, damage, resources, risks, alerts |
| Incident | `GET /incidents/{id}` |
| Reports / audit / exports | generate, audit-logs, exports |

---

## 5. Database architecture

**Dev default:** SQLite `sqlite:///./visionguard.db` (`DATABASE_URL`).  
**Docker:** PostgreSQL + PostGIS (`postgis/postgis:16-3.4`).

Geometry in v1 is **GeoJSON JSON columns** so SQLite tests work; types are PostGIS-compatible later.

### Tables (`backend/app/models/entities.py`)

| Entity | Used for |
| --- | --- |
| `Location` | Seeded Kuttanad/Guwahati/Puri rows (Demo Mode); live AOI is in-memory `geo/aoi.py` |
| `Disaster` | Seeded flood incident (hidden in REAL DATA lists) |
| `User` | Placeholder |
| `WeatherObservation`, `WeatherForecast` | Seeded weather rows (incident page reads these — not live OpenWeather cache) |
| `SatelliteImage`, `ImageAnalysisResult`, `DetectedObject` | Catalogue / analysis rows |
| `FloodEvent` | Seeded flood extent (incident command) |
| `FloodAnalysis` | Rows from **Flood Detection → Run** |
| `DamageAssessment`, `DamageReport` | Seeded + Run damage |
| `RiskZone` | Seeded zones |
| `Road`, `Building`, `Infrastructure` | Seeded accessibility/damage story |
| `RescueResource`, `EvacuationCenter`, `RescuePriority`, `RescuePlan` | Ops inventory + plans |
| `Alert` | Seeded + generated |
| `VisionJob` | Upload CV jobs |
| `AuditLog` | Acknowledge / allocate / seed |

**Seed:** `backend/app/db/seed.py` — Demo Mode boats, centers, Kuttanad incident, stub weather, stub flood 34.5 km², demo alerts. Not presented as current Karnataka operations in REAL DATA mode.

---

## 6. Frontend architecture

**Stack:** Vite, React 18, TypeScript, Tailwind, React Router, Leaflet, Chart.js.

```
main.tsx → App.tsx (BrowserRouter)
           AppLayout.tsx
             Header, Sidebar, IncidentBar
             SafetyBanner + DataSourcePanel
             <Outlet> pages
```

**Rule:** pages do not call `fetch` directly. They use `hooks/useAsync` + `services/*.ts` + `apiClient.ts`.

### 6.1 Routes (`frontend/src/App.tsx`)

| URL | Page file | Function |
| --- | --- | --- |
| `/dashboard` | `DashboardPage.tsx` | KPIs, map, charts, alerts |
| `/disasters/:id` | `DisasterDetailPage.tsx` | Incident command (DB aggregate) |
| `/risk-intelligence` | `RiskIntelligencePage.tsx` | Risk zones + map |
| `/situation` | `SituationPage.tsx` | OSM + catalog + incidents |
| `/flood-detection` | `FloodPage.tsx` | Run flood change |
| `/damage-assessment` | `DamagePage.tsx` | Run damage heuristic |
| `/weather` | `WeatherPage.tsx` | Live weather + derived risk |
| `/satellite` | `SatellitePage.tsx` | Scene list + analyze |
| `/satellite/compare` | `SatelliteComparePage.tsx` | Before/after |
| `/computer-vision` | `ComputerVisionPage.tsx` | Upload detect |
| `/rescue-planning` | `RescuePage.tsx` | Plan + Accept |
| `/alerts` | `AlertsPage.tsx` | Generate / ack |
| `/analytics` | `AnalyticsPage.tsx` | Rollups |
| `/settings` | `SettingsPage.tsx` | Mode + IDs |

### 6.2 Frontend folder map

| Path | Role |
| --- | --- |
| `src/layouts/AppLayout.tsx` | Shell |
| `src/components/*` | Map, badges, KPI, charts, banners |
| `src/pages/*` | Screens |
| `src/services/apiClient.ts` | Base URL + mock switch |
| `src/services/*.ts` | One module per API area |
| `src/data/mock.ts` | Full UI mock when `VITE_USE_MOCK` |
| `src/data/gisMock.ts` | Demo Mode GIS catalog only (`isMockMode()`). Live maps use Overpass. |
| `src/constants/demo.ts` | IDs + DEMO_STATS |
| `src/hooks/useAsync.ts`, `useAlertStream.ts` | Data / SSE |
| `src/maps/`, `src/charts/` | Leaflet / Chart.js helpers |
| `src/types/api.ts`, `gis.ts` | Types |

### 6.3 UI vs data (honest mix)

| Screen | Live | Derived | Seeded | Demo/mock-shaped |
| --- | --- | --- | --- | --- |
| Dashboard | OpenWeather, STAC, Overpass, AOI | flood water-change if a live analysis exists | hidden in REAL DATA | `gisMock` + DEMO_STATS **only if Demo Mode** |
| Incident command | — | — | Demo Mode case file | live mode: no sidebar link unless a real incident exists |
| Weather | OpenWeather, NASA POWER | risk index from available terms | — | IMD / river UNAVAILABLE unless configured |
| Satellite | Copernicus STAC from 1 May 2026 | OpenCV analyze on genuine previews | mock scenes Demo Mode only | catalogue-only scenes have no fake preview |
| Flood Run | Sentinel pair | `compare_water_change` heuristic | DEMO_STATS strip Demo Mode only | not U-Net |
| Damage Run | Sentinel pair | change heuristic; live building counts UNAVAILABLE | simulated mix Demo Mode only | — |
| Situation | Overpass features + AOI boundary | — | incidents hidden live | empty OSM ≠ confirmed absence |
| Rescue | — | — | boats/centers Demo Mode only | live inventory UNAVAILABLE |
| Alerts generate | weather inputs | rules engine | initial alerts Demo Mode | not official IMD unless IMD returns data |
| CV | YOLO if local `.pt` | — | — | DemoVision in Demo Mode only |

---

## 7. Data providers (how live inputs enter)

| Provider | Factory / class | Config | Used by |
| --- | --- | --- | --- |
| OpenWeather | `weather/openweather_provider.py` | `OPENWEATHER_API_KEY`, `OPENWEATHER_QUERY` | current, forecast |
| NASA POWER | `weather/nasa_power.py` | `NASA_POWER_*`, selected AOI lat/lon | history |
| IMD | `weather/imd_client.py` | `IMD_API_KEY` | official warnings if set |
| Live composite | `weather/live_provider.py` | — | LIVE weather path |
| Mock weather | `weather/mock_provider.py` | Demo Mode | canned weather |
| Weather factory | `weather/factory.py` | `USE_MOCK_PROVIDERS` | picks live vs mock |
| Copernicus STAC | `satellite/copernicus_provider.py` | STAC URL, optional OAuth | scenes + thumbnails |
| Mock satellite | `satellite/mock_provider.py` | Demo Mode | synthetic rasters |
| OSM Overpass | `gis/overpass.py` | `GIS_OVERPASS_*` | dashboard + situation GIS (live) |
| Notifications | `alerts/notifications.py` | `ENABLE_REAL_*` | unwired = MOCK |

---

## 8. Processing / “AI” architecture (what actually runs)

Runtime CV and risk live in **`backend/app/services`**, not in `ai/` (that package is stubs/interfaces).

```
Copernicus RGB preview bytes
        ↓
satellite/processing.py
  detect_water / detect_water_sentinel_rgb
  compare_water_change  (after AND NOT before)
  compare_scenes        (flood expand, veg, urban)
        ↓
flood/service.py        FloodAnalysis row
damage/service.py + classify.py
satellite/service.py    analyze / compare
        ↓
JSON + GeoJSON to UI
```

| “Model” | Real weights? | File | Used on |
| --- | --- | --- | --- |
| Sentinel RGB water heuristic | No | `flood/models.py`, `processing.py` | LIVE flood/satellite |
| DemoFloodModel (blue channel) | No | `flood/models.py` | Demo Mode |
| U-Net / DeepLab classes | **Not implemented** | `flood/models.py` | never |
| Damage classifiers | Thresholds | `damage/classify.py` | Damage page |
| Flood/cyclone risk | Weighted formulas | `risk/flood.py`, `risk/cyclone.py` | Weather |
| Rainfall anomaly | Formulas | `risk/rainfall.py` | Weather |
| Alerts | `rules.json` + fusion | `alerts/engine.py` | Alerts |
| Rescue priority | Weighted 0–100 | `rescue/priority.py` | Rescue |
| DemoVisionModel | Simulated boxes | `vision/demo_model.py` | Demo CV |
| YOLOVisionModel | Optional local `.pt` | `vision/yolo_model.py` | CV if `YOLO_WEIGHTS_PATH` |
| `ai/` FloodDetector etc. | Stubs | `ai/services/*` | not the FastAPI path |

**YOLO:** set `YOLO_WEIGHTS_PATH` to an existing local file; install `ultralytics` yourself (not in `requirements.txt`). Never auto-download.

---

## 9. End-to-end flows (how results are generated)

### 9.1 Weather intelligence

UI Weather → `services/weather.ts` → `/weather/*` → `WeatherIntelService` → live/mock provider → `risk/*` formulas → JSON.

### 9.2 Flood change (LIVE)

UI Flood **Run** → `POST /flood/analyze` → `FloodDetectionService._analyze_real_change` → Copernicus two previews → `compare_water_change` → persist `FloodAnalysis` → Flood page.

### 9.3 Damage

UI Damage **Run** → `POST /damage/analyze` → load Sentinel pair (live) or demo rasters (Demo Mode) → `compare_scenes`. Live mode does **not** invent building/road inventories. Demo Mode uses `classify_building` / `classify_road` mix.

### 9.4 Alerts

UI Generate → `AlertEngine.gather_signals` (live weather + risk) → `composite_score` + `rules.json` → insert `Alert`. SMS/email remain MOCK unless flags + clients exist.

### 9.5 Rescue

**Demo Mode:** seeded resources → `RescuePriorityService` → `POST /rescue/plan` → officer **Accept/Modify/Reject**.  
**REAL DATA:** no live vehicle/shelter feed; plan generation must not fabricate units.

### 9.6 Incident command

`GET /incidents/{id}` → `IncidentCommandService.picture` reads **DB** (seeded disaster, `FloodEvent`, `WeatherObservation`, alerts, resources). It does **not** call OpenWeather or Copernicus. Links jump to the live/heuristic pages.

### 9.7 GIS

- **REAL DATA:** `GET /gis/features` → OSM Overpass for the selected Karnataka AOI (`STATIC_EXTERNAL`). Empty layer = not mapped in OSM, not confirmed absence. Timeouts/429 → 503, no `gisMock`.
- **Demo Mode:** `frontend/src/data/gisMock.ts` via `isMockMode()`.
- AOI: `GET/PUT /gis/aoi` (`geo/aoi.py`); Kerala demo bbox is rejected for live analysis.

---

## 10. Docker / run

| Piece | How |
| --- | --- |
| Local backend | `uvicorn app.main:app --reload` from `backend/` → `:8000` |
| Local frontend | `npm run dev` in `frontend/` → `:5173` |
| Compose | `docker compose up --build` (see compose env for `USE_MOCK_PROVIDERS`) |
| Compose live | `--env-file .env.live -f docker-compose.yml -f docker-compose.live.yml up --build` |
| Health | `GET /api/v1/health`, `GET /api/v1/data-sources/status?probe=true` |

Images: `docker/backend.Dockerfile`, `docker/frontend.Dockerfile`.

---

## 11. Tests

| Area | Location |
| --- | --- |
| Backend | `backend/tests/test_*.py` (API, flood, satellite, provenance, alerts, vision, journey, …) |
| Frontend unit | `frontend/src/**/*.test.ts(x)` |
| AI stubs | `ai/tests/test_stubs.py` |

---

## 12. How layers relate (build principle)

1. **UI** is a command console. Demo Mode ties modules to the seeded Kuttanad incident; live mode uses the selected Karnataka AOI and does not invent an incident.  
2. **API** is a thin router over **services**.  
3. **Providers** isolate live HTTP; factories choose mock vs live. Live failures are 503 / UNAVAILABLE — no silent mock.  
4. **Heuristics** sit between live imagery/weather and officer KPIs and are labeled **DERIVED_LIVE**.  
5. **Seed** supplies Demo Mode ops objects (boats, Kuttanad case file). Hidden in REAL DATA list APIs.  
6. **Provenance** is first-class so LIVE weather is never confused with seeded flood extents.

That is the complete structure of this codebase: a React ops UI on a FastAPI service layer, with pluggable live providers (Copernicus STAC, OSM Overpass, OpenWeather, NASA POWER, optional IMD), OpenCV/rule pipelines, an explicit Demo Mode Kuttanad scenario, and LIVE / DERIVED_LIVE / SEEDED / MOCK / STATIC_EXTERNAL / NOT_CONFIGURED / UNAVAILABLE labeling.
