# VisionGuard AI — Complete Project Documentation

**Status of this document:** Describes the repository **as it exists in the source code today**.  
**Scope:** Verified from implementation files under `frontend/`, `backend/`, `ai/`, `src/`, `scripts/`, `docker/`, `data/`, and configuration.  
**Rule used:** If something is not present or not wired in code, it is labeled accordingly. Nothing here invents live government feeds, trained neural nets, or production auth.

---

## 1. Project Overview

### Simple explanation

**VisionGuard AI** is a **prototype disaster operations console**. It shows how an officer could watch a flood scenario, look at weather and risk scores, inspect satellite-style imagery, estimate flood and damage, propose a rescue plan, and record alerts — all on one dashboard.

The demo story is a **simulated Kuttanad monsoon flood** in Kerala (Alappuzha district). Headline numbers such as **82% flood risk**, **34.5 km² flooded**, and **42,000 people at risk** are **canonical simulated demo figures**, not live observations.

### Technical summary

| Item | Current answer from code |
| --- | --- |
| Project name | **VisionGuard AI** (`settings.app_name`, FastAPI `title`) |
| Frontend | React 19 + TypeScript + Vite (`frontend/`) |
| Backend | FastAPI app under `backend/app/` exposing `/api/v1` |
| Database | SQLAlchemy ORM; default **SQLite** `sqlite:///./visionguard.db` |
| Demo incident ID | `aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa` |
| Demo location ID | `11111111-1111-4111-8111-111111111111` |
| Product path | `frontend/` + `backend/` (not legacy `src/`, not stub `ai/`) |

### Purpose and problem

- **Purpose:** Decision-support UI and API for disaster operations (flood-focused demo).
- **Problem addressed:** Fragmented situational awareness (weather, maps, imagery, damage, rescue, alerts) needs a single prototype console.
- **Not claimed:** Official IMD/NDMA warnings, live Sentinel granules inside the app, trained U-Net, or real SMS dispatch.

### Main objectives (as implemented)

1. Present a command dashboard and incident view for one seeded flood.
2. Expose weather, risk, satellite, flood, damage, vision, rescue, alert, and analytics APIs.
3. Keep providers swappable (`MockWeatherProvider` vs optional OpenWeather; demo vision vs optional local YOLO).
4. Label prototype / simulated / mock outputs honestly in UI and backend labels.

### Target users (demo)

- Engineering students / reviewers demonstrating the prototype.
- Hypothetical disaster-ops officers (no login/roles enforced in the running API).

### Main use cases (working in the prototype)

1. Open dashboard → see KPIs, map layers, alerts, charts.
2. Inspect weather and flood/cyclone risk scores.
3. List mock satellite scenes → analyze / compare synthetic rasters.
4. Run flood detection (OpenCV water mask on synthetic RGB).
5. Run damage assessment (before/after change heuristics).
6. Upload an image for computer vision (demo boxes or optional YOLO).
7. Generate a rescue plan and Accept / Modify / Reject (audit log).
8. Generate / acknowledge / resolve prototype alerts.
9. View analytics KPIs and CSV exports.

### What the system currently does

- Serves a full React SPA with routes listed in §5.
- Runs FastAPI with ~50+ `/api/v1` endpoints (see §6 / §15).
- Seeds SQLite (or Postgres URL) with demo locations, disasters, zones, resources, etc.
- Computes **rule-based** flood/cyclone risk and rescue scores.
- Generates **synthetic** satellite PNGs and OpenCV masks.
- Stores vision jobs, flood analyses, damage reports, rescue plans, alerts in the DB.

### What the system does NOT currently do

- Does **not** fetch live Copernicus/Sentinel imagery into the app (`get_satellite_provider()` always returns `MockSatelliteProvider`).
- Does **not** use OpenWeather unless `USE_MOCK_PROVIDERS=false` **and** `OPENWEATHER_API_KEY` is set.
- Does **not** load trained U-Net / DeepLab (`NotImplementedError`).
- Does **not** send real email/SMS/push (adapters mock or `refused_unwired`).
- Does **not** implement JWT/session authentication.
- Does **not** generate PDF reports (`pdf_available=False`; `to_pdf` not wired as a real PDF).
- Does **not** use PostGIS geometry types (GeoJSON in JSON columns).
- Does **not** import or run the separate `ai/` stub package from FastAPI.
- Does **not** call legacy `src/` NASA/NOAA/OpenWeather routes from the dashboard.

### Current implementation status

| Area | Status |
| --- | --- |
| Frontend console | **Implemented** (with UI mock mode default) |
| Backend API | **Implemented** |
| DB seed + CRUD-style reads/writes | **Implemented** |
| Weather | **Mock by default**; OpenWeather **configured but inactive** without key |
| Satellite | **Mock / synthetic rasters only** |
| Flood / damage “AI” | **Heuristic OpenCV / rules** (demo) |
| Vision | **Demo model default**; YOLO **optional if local weights file exists** |
| Alerts | **Rule engine + DB**; notifications **mock** |
| Auth | **Not implemented** |
| Alembic migrations | **Not set up** (README under `db/migrations/`) |
| Docker Compose | **Present**; PostGIS image available; app still uses JSON GeoJSON |

### Overall technology stack (high level)

React + Vite + Tailwind + Leaflet + Chart.js → FastAPI + SQLAlchemy + Pydantic + NumPy + OpenCV → SQLite (default) or Postgres URL → mock providers / optional OpenWeather / optional local YOLO.

---

## 2. Complete Project Architecture

### Mermaid — actual runtime architecture

```mermaid
flowchart TB
  USER[Browser user] --> FE[frontend React SPA]
  FE --> LAYOUT[AppLayout Header Sidebar IncidentBar]
  LAYOUT --> PAGES[pages/*]
  PAGES --> SVC_FE[frontend/src/services/*]
  SVC_FE -->|VITE_USE_MOCK not false| MOCK_FE[data/mock.ts]
  SVC_FE -->|VITE_USE_MOCK=false| HTTP[apiClient fetch]
  PAGES --> GIS[gis.ts always returns gisMock.ts]
  GIS --> LEAFLET[Leaflet maps]
  HTTP --> API[FastAPI backend/app/main.py]
  API --> RTR[api/v1/router.py]
  RTR --> SVCB[app/services/*]
  SVCB --> DB[(SQLAlchemy DB SQLite or Postgres URL)]
  SVCB --> MW[MockWeatherProvider]
  SVCB -.->|only if mock off AND key set| OW[OpenWeatherProvider]
  SVCB --> MS[MockSatelliteProvider + generate_demo_raster]
  SVCB --> CV[OpenCV / NumPy heuristics]
  SVCB --> DV[DemoVisionModel]
  SVCB -.->|YOLO_WEIGHTS_PATH file exists| YOLO[YOLOVisionModel]
  SVCB --> RULES[alerts/rules.json + risk formulas]
  SVCB --> FS[storage/vision uploads]
  LEGACY[src/ legacy FastAPI] -.->|not mounted by backend| X1[Unused by dashboard]
  AISTUB[ai/ stub package] -.->|not imported by backend| X2[Unused at runtime]
```

### Architecture in simple words

1. You open the website (Vite, port **5173**).
2. A page calls a function in `frontend/src/services/`.
3. If frontend mock mode is on, data comes from `mock.ts` / `gisMock.ts` and may never hit the API.
4. If mock mode is off, the browser calls `http://127.0.0.1:8000/api/v1/...`.
5. FastAPI routes into a **service** (weather, satellite, flood, vision, rescue, alerts, …).
6. The service reads/writes the database and/or mock providers / OpenCV / demo vision.
7. JSON returns to React and fills KPI cards, tables, charts, and maps.

**Important:** Command-map GIS layers are **always** from `frontend/src/data/gisMock.ts`, even when the API is live.

---

## 3. Complete Folder and File Structure

```text
Disaster_Management_System/
├── README.md
├── .env.example                 # backend env template (no secrets)
├── docker-compose.yml           # postgres/postgis + backend + frontend
├── docker/
│   ├── backend.Dockerfile
│   └── frontend.Dockerfile
├── docs/                        # human documentation (this file lives here)
├── scripts/
│   ├── seed.py
│   └── seed_demo_data.py        # wrappers that seed backend demo data
├── data/mock/satellite/
│   └── kuttanad_demo.txt        # text placeholder, not a real image
├── frontend/                    # ACTIVE product UI
├── backend/                     # ACTIVE product API
├── ai/                          # STUB package — not imported by FastAPI
└── src/                         # LEGACY FastAPI (NASA/NOAA/OpenWeather) — not dashboard backend
```

### `frontend/` (active)

| Path | Purpose | Used? |
| --- | --- | --- |
| `src/main.tsx` | React entry | Yes |
| `src/App.tsx` | Routes | Yes |
| `src/layouts/AppLayout.tsx` | Shell | Yes |
| `src/pages/*.tsx` | Screens | Most routed; `OverviewPage.tsx`, `RiskPage.tsx` **not in router** |
| `src/components/*` | Shared UI | Yes |
| `src/services/*` | HTTP / mock | Yes |
| `src/data/mock.ts`, `gisMock.ts` | Frontend mock / GIS | Yes |
| `src/constants/demo.ts` | Demo IDs & KPIs | Yes |
| `src/hooks/useAsync.ts`, `useAlertStream.ts` | Data / SSE | Yes |

### `backend/` (active)

| Path | Purpose | Used? |
| --- | --- | --- |
| `app/main.py` | FastAPI app, CORS, lifespan seed | Yes |
| `app/api/v1/router.py` | All `/api/v1` routes | Yes |
| `app/core/config.py`, `demo.py`, `errors.py`, `logging.py` | Settings / demo constants / errors | Yes |
| `app/db/session.py`, `init_db.py`, `seed.py` | DB + seed | Yes |
| `app/models/entities.py` | ORM tables | Yes |
| `app/schemas/common.py` | Pydantic I/O | Yes |
| `app/repositories/ops.py` | Thin DB reads | Yes |
| `app/services/**` | Business logic | Yes |
| `tests/**` | pytest | Yes |

### `ai/` (stub / unused by runtime FastAPI)

Contains `inference/runner.py`, stub services, preprocessing stubs, `models/README.md` (“put checkpoints here later”). **No `import` from `backend/app` into `ai/`.**

### `src/` (legacy)

Separate FastAPI app with OpenWeather / NOAA / NASA routes. **Not mounted** in `backend/app/main.py`. Dashboard does not call it.

### Classification

| Kind | Examples |
| --- | --- |
| Active code | `frontend/`, `backend/app/` |
| Legacy | `src/` |
| Unused/stub | `ai/`; `OverviewPage.tsx`, `RiskPage.tsx` (unrouted) |
| Demo / mock | `mock.ts`, `gisMock.ts`, `MockWeatherProvider`, `MockSatelliteProvider`, `DemoVisionModel`, `DemoFloodModel` |
| Config | `.env.example`, `frontend/.env.example`, `docker-compose.yml` |
| Docs | `docs/**` |
| Scripts | `scripts/seed*.py` |

---

## 4. Technology Stack

| Layer | Technology | Version (from manifests) | Purpose | Currently Used? |
| ----- | ---------- | ------------------------ | ------- | --------------- |
| Frontend framework | React | ^19.1.0 | UI | Yes |
| Frontend language | TypeScript | ^5.8.3 | Typing | Yes |
| Build | Vite | ^6.3.5 | Dev/build | Yes |
| Routing | react-router-dom | ^7.6.2 | SPA routes | Yes |
| Maps | leaflet / react-leaflet | ^1.9.4 / ^5.0.0 | GIS maps | Yes |
| Charts | chart.js / react-chartjs-2 | ^4.4.9 / ^5.3.0 | Charts | Yes |
| CSS | Tailwind CSS | ^3.4.17 | Styling | Yes |
| FE test | Vitest + Testing Library | ^3.2.4 / ^16.3.0 | Unit tests | Yes |
| Backend | FastAPI | 0.139.0 | HTTP API | Yes |
| ASGI server | uvicorn | 0.51.0 | Run API | Yes |
| Validation | pydantic / pydantic-settings | 2.13.4 / 2.10.1 | Schemas / settings | Yes |
| ORM | SQLAlchemy | 2.0.51 | DB models | Yes |
| Postgres driver | psycopg2-binary | 2.9.10 | Optional Postgres | Available; used if `DATABASE_URL` is Postgres |
| HTTP client | httpx | 0.28.1 | OpenWeather calls | Yes (when OpenWeather selected) |
| Array/CV | numpy / opencv-python-headless | 2.2.6 / 4.11.0.86 | Urasters / masks | Yes |
| Uploads | python-multipart | 0.0.20 | Vision upload | Yes |
| BE test | pytest | 8.4.1 | Tests | Yes |
| Lint | ruff | 0.12.4 | Lint | Tooling |
| DB default | SQLite | via SQLAlchemy URL | Default store | Yes (default) |
| Compose DB image | postgis/postgis:16-3.4 | compose | Optional container DB | Optional; **PostGIS types not used in ORM** |
| YOLO / Ultralytics | ultralytics | **Not in requirements.txt** | Optional vision | Only if installed separately + local weights |
| PyTorch | — | **Not found in requirements** | — | Not a project dependency |
| Alembic | — | **Not configured** | Migrations | Not active |
| Auth libs (JWT etc.) | — | **Not found** | Auth | Not implemented |

---

## 5. Frontend Architecture

### Stack

- **Framework:** React 19  
- **Language:** TypeScript  
- **Build:** Vite (port **5173**, `host: true`)  
- **Styling:** Tailwind (`styles/index.css`, Tailwind config)  
- **Routing:** `react-router-dom` in `App.tsx`  
- **State:** Local React state + `useAsync` hook (no Redux/Zustand found)  
- **API:** `apiClient.ts` (`apiGet`, `apiPost`, `apiUpload`)  
- **Mock mode:** `isMockMode()` → `import.meta.env.VITE_USE_MOCK !== "false"` (default **true** per `.env.example`)  
- **Maps:** Leaflet components (`DisasterMap`, `SituationMap`, `SatelliteOverlayMap`, `RescuePlanningMap`)  
- **Charts:** Chart.js via `DashboardCharts`, `TrendCharts`, page-local charts  
- **Feedback:** `LoadingState`, `ErrorState`, modals in `Feedback.tsx`  
- **Safety copy:** `SafetyBanner`, `EstimateCallout`, header DEMO MODE  

### Frontend routes

| Route | Page/Component | Purpose | Data Source | Current Status |
| ----- | -------------- | ------- | ----------- | -------------- |
| `/` | Navigate → dashboard | Redirect | — | Active |
| `/dashboard` | `DashboardPage` | KPIs, map, alerts, charts | services + `DEMO_STATS` + **always** gisMock | Active |
| `/risk-intelligence` | `RiskIntelligencePage` | Zones + factors + map | `/risk-zones` or mock; map gisMock | Active |
| `/risk` | Redirect | Alias | — | Active redirect |
| `/situation` | `SituationPage` | Disaster table + situation map | disasters API/mock; map points mock | Active |
| `/live-situation` | Redirect → situation | Alias | — | Active redirect |
| `/flood-detection` | `FloodPage` | Run flood analysis | `POST /flood/analyze` or mock | Active |
| `/flood` | Redirect | Alias | — | Active redirect |
| `/damage-assessment` | `DamagePage` | Before/after damage | `POST /damage/analyze` or mock | Active |
| `/damage` | Redirect | Alias | — | Active redirect |
| `/weather` | `WeatherPage` | Weather + risk charts | weather/risk APIs or mock | Active |
| `/satellite` | `SatellitePage` | Catalog + analyze | satellite APIs or mock | Active |
| `/satellite/compare` | `SatelliteComparePage` | Before/after compare | `POST /satellite/compare` or mock | Active |
| `/computer-vision` | `ComputerVisionPage` | Upload + detections | `POST /vision/analyze` (mock fallback) | Active |
| `/rescue-planning` | `RescuePage` | Priorities, plan, decision | rescue APIs or mock | Active |
| `/rescue` | Redirect | Alias | — | Active redirect |
| `/alerts` | `AlertsPage` | List/generate/ack; optional SSE | alerts APIs; SSE if not mock | Active |
| `/analytics` | `AnalyticsPage` | KPIs + trends | `/analytics/overview` or mock | Active |
| `/disasters/:id` | `DisasterDetailPage` | Incident command picture | `/incidents/{id}` or mock | Active |
| `/settings` | `SettingsPage` | Demo IDs, exports, reports | constants + export URLs | Active |
| `*` | Navigate → dashboard | Fallback | — | Active |
| *(no route)* | `OverviewPage.tsx`, `RiskPage.tsx` | — | — | **Files exist, unused by router** |

### Major pages (what you see / where data comes from)

**Dashboard** — KPIs (often `DEMO_STATS`: 34.5 km², 18 buildings, 42k population), Leaflet `DisasterMap` from gisMock, weather snippet, alerts, Chart.js. APIs when not mock: disasters, alerts, resources, weather/current, analytics/overview. Map: **STATIC gisMock**. KPIs: **SIMULATED**.

**Incident command** — Combined incident JSON (`IncidentCommandService.picture`): narrative, weather, zones, resources, alerts, plan. **SIMULATED** narrative + **seeded DB** when API live.

**Weather** — Current/forecast/history/rainfall + flood/cyclone scores. Default backend: **MOCK** weather; flood often **82% SIMULATED** when `use_mock_providers`.

**Risk Intelligence** — Risk zones from DB/API with `RiskService.explain`. Map still gisMock.

**Satellite / Compare** — Mock catalog; previews are generated PNG; analysis OpenCV color masks. **Not live Sentinel.**

**Flood Detection** — Button runs OpenCV water mask on synthetic raster; stores `flood_analyses`. **HEURISTIC**.

**Damage Assessment** — Before/after synthetic rasters + classification rules. **HEURISTIC / RULE-BASED**. PDF not available.

**Computer Vision** — Upload → `VisionPipeline` → `DemoVisionModel` (or YOLO if weights file). **MOCK detections by default.**

**Rescue Planning** — Weighted priority + if/then recommendations + demo graph routing; Accept writes audit. **RULE-BASED**.

**Alerts** — Engine vs `rules.json`; ack/resolve; SSE in-memory when not FE mock. Notifications **MOCK**.

**Analytics** — Aggregates; with mock providers, KPIs forced to demo constants (`SIMULATED`).

**Settings** — Shows demo IDs; CSV export links to `/api/v1/exports/{dataset}`.

**Live Situation** — Table of disasters; `fetchMapPoints` always returns mock map points (`intel.ts`). Weaker live story.

---

## 6. Backend Architecture

### Entry and startup

- **Entry:** `backend/app/main.py`
- **Lifespan:** `configure_logging()` → `init_db()` → `seed_if_empty()`
- **Prefix:** `settings.api_v1_prefix` = `/api/v1`
- **CORS:** origins from `CORS_ORIGINS` (default Vite ports)
- **Errors:** `register_exception_handlers` (hides stack traces from clients)
- **Root:** `GET /` → `{ service, docs, api }`

### Layers

```
router.py → Service classes → Repository / Provider / OpenCV / SQLAlchemy models → JSON (Pydantic schemas)
```

### API endpoints (complete list from `router.py`)

| Method | Endpoint | File | Purpose | Input | Output | Data Source | Status |
| ------ | -------- | ---- | ------- | ----- | ------ | ----------- | ------ |
| GET | `/api/v1/health` | router.py | Health | — | status, env, mock flag | settings | Active |
| GET | `/api/v1/disasters` | router.py | List disasters | optional `phase` | DisasterList | DB | Active |
| GET | `/api/v1/disasters/{id}` | router.py | One disaster | id | DisasterOut | DB | Active |
| GET | `/api/v1/risk-zones` | router.py | Zones + explain | — | RiskZoneList | DB + RiskService | Active |
| GET | `/api/v1/risk-zones/{id}` | router.py | One zone | id | RiskZoneDetailOut | DB | Active |
| GET | `/api/v1/risk/flood` | router.py | Flood probability | optional location_id | FloodRiskOut | WeatherIntel + formula + overlay | Active |
| GET | `/api/v1/risk/cyclone` | router.py | Cyclone score | optional location_id | CycloneRiskOut | formula | Active |
| GET | `/api/v1/weather/current` | router.py | Current weather | location_id? | WeatherCurrentOut | provider | Active |
| GET | `/api/v1/weather/forecast` | router.py | Forecast | location_id? | WeatherForecastList | provider | Active |
| GET | `/api/v1/weather/history` | router.py | History | location_id? | WeatherHistoryList | provider | Active |
| GET | `/api/v1/weather/rainfall` | router.py | Rainfall analysis | location_id? | RainfallAnalysisOut | analyze_rainfall | Active |
| GET | `/api/v1/weather/alerts` | router.py | Provider + candidates | location_id? | WeatherAlertsOut | provider + engine | Active |
| GET | `/api/v1/alerts` | router.py | Stored alerts | filters | AlertList | DB | Active |
| GET | `/api/v1/alerts/stream` | router.py | SSE | — | event-stream | in-memory queues | Active |
| GET | `/api/v1/alerts/events` | router.py | Poll events | since? | items | in-memory | Active |
| POST | `/api/v1/alerts/generate` | router.py | Run engine | AlertGenerateRequest | AlertList | rules + scores | Active |
| GET | `/api/v1/alerts/{id}` | router.py | One alert | id | AlertOut | DB | Active |
| POST | `/api/v1/alerts/{id}/acknowledge` | router.py | Ack | actor | AlertOut | DB | Active |
| POST | `/api/v1/alerts/{id}/resolve` | router.py | Resolve | actor | AlertOut | DB | Active |
| GET | `/api/v1/resources` | router.py | Rescue units | — | ResourceList | DB | Active |
| POST | `/api/v1/resources/allocate` | router.py | Allocate unit | AllocateRequest | RescueResourceOut | DB | Active |
| GET | `/api/v1/rescue/priorities` | router.py | Priority scores | — | RescuePriorityList | scoring | Active |
| POST | `/api/v1/rescue/plan` | router.py | Build plan | RescuePlanRequest | RescuePlanOut | rules + routing | Active |
| GET | `/api/v1/rescue/plans/{id}` | router.py | Get plan | id | RescuePlanOut | DB | Active |
| POST | `/api/v1/rescue/plans/{id}/decision` | router.py | accept/modify/reject | RescueDecisionRequest | RescuePlanOut | DB + AuditLog | Active |
| GET | `/api/v1/evacuation-centers` | router.py | Shelters | — | EvacuationCenterList | DB | Active |
| GET | `/api/v1/satellite/images` | router.py | Catalog | — | SatelliteImageList | mock sync → DB | Active |
| GET | `/api/v1/satellite/images/{id}` | router.py | One scene | id | SatelliteImageOut | DB | Active |
| GET | `/api/v1/satellite/images/{id}/preview` | router.py | PNG bytes | id | image/png | generate_demo_raster | Active |
| POST | `/api/v1/satellite/analyze` | router.py | Color-mask analysis | AnalyzeRequest | SatelliteAnalysisOut | OpenCV heuristics | Active |
| GET | `/api/v1/satellite/analysis/{id}` | router.py | Saved analysis | id | SatelliteAnalysisOut | DB | Active |
| POST | `/api/v1/satellite/compare` | router.py | Before/after | CompareRequest | SatelliteAnalysisOut | compare_scenes | Active |
| GET | `/api/v1/vision/health` | router.py | Model health | — | dict | get_vision_model | Active |
| POST | `/api/v1/vision/detect` | router.py | Detect upload | multipart file | VisionResultOut | VisionPipeline | Active |
| POST | `/api/v1/vision/analyze` | router.py | Analyze upload | multipart file | VisionResultOut | VisionPipeline | Active |
| GET | `/api/v1/vision/jobs/{id}/annotated` | router.py | Annotated JPEG | id | FileResponse | disk storage | Active |
| POST | `/api/v1/flood/analyze` | router.py | Flood pipeline | FloodAnalyzeRequest | FloodEventOut | DemoFloodModel | Active |
| GET | `/api/v1/flood/events` | router.py | List analyses | — | FloodEventList | DB | Active |
| GET | `/api/v1/flood/events/{id}` | router.py | One analysis | id | FloodEventOut | DB | Active |
| POST | `/api/v1/damage/analyze` | router.py | Damage pipeline | DamageAnalyzeRequest | DamageAssessmentOut | change detect | Active |
| GET | `/api/v1/damage/assessments` | router.py | List | — | DamageAssessmentList | DB | Active |
| GET | `/api/v1/damage/assessments/{id}` | router.py | One | id | DamageAssessmentOut | DB | Active |
| GET | `/api/v1/analytics/overview` | router.py | KPIs | filters | dict | DB + demo overlay | Active |
| GET | `/api/v1/analytics/disasters` | router.py | Disaster analytics | filters | dict | DB | Active |
| GET | `/api/v1/analytics/damage` | router.py | Damage series | dates | dict | DB | Active |
| GET | `/api/v1/analytics/resources` | router.py | Resource analytics | — | dict | DB | Active |
| GET | `/api/v1/analytics/risks` | router.py | Risk analytics | — | dict | DB | Active |
| GET | `/api/v1/analytics/alerts` | router.py | Alert analytics | dates | dict | DB | Active |
| GET | `/api/v1/incidents/{id}` | router.py | Incident picture | id | dict | IncidentCommandService | Active |
| POST | `/api/v1/reports/generate` | router.py | JSON report | ReportRequest | dict | ReportService | Active (JSON only) |
| GET | `/api/v1/audit-logs` | router.py | Recent audits | — | AuditLogList | DB (limit 100) | Active |
| GET | `/api/v1/exports/{dataset}` | router.py | CSV export | dataset name | text/csv | Analytics/DB | Active |

**Endpoint count (router):** **52** under `/api/v1` (plus `GET /` root).

### Internal flow example

`POST /api/v1/flood/analyze`  
→ `FloodDetectionService.analyze`  
→ `generate_demo_raster` → `DemoFloodModel.segment` (`detect_water`)  
→ polygons / area / affected assets  
→ insert `flood_analyses`  
→ `FloodEventOut` JSON  

---

## 7. Database Documentation

### Connection

| Item | Value from code |
| --- | --- |
| ORM | SQLAlchemy 2.x DeclarativeBase |
| Default URL | `sqlite:///./visionguard.db` |
| Engine | `create_engine(settings.database_url)` |
| SQLite args | `check_same_thread=False` when URL starts with `sqlite` |
| Postgres | Supported via `DATABASE_URL` (Compose example: `postgresql://visionguard:visionguard@postgres:5432/visionguard`) |
| PostGIS | Compose image is `postgis/postgis:16-3.4`, but models store geometry as **JSON GeoJSON**, not PostGIS types |
| MongoDB | **Not found in the current codebase** |
| Alembic | **Not set up** (`db/migrations/README.md`) |
| Init | `init_db()` creates tables (`create_all` + SQLite ALTER helpers) |
| Seed | `seed_if_empty()` if no disasters |

### Models / tables (from `entities.py`)

| Table | Model | Key fields (summary) |
| --- | --- | --- |
| `locations` | Location | id, name, district, state, country, lat/lon, geojson JSON |
| `disasters` | Disaster | id, title, type, phase, severity, status, people_at_risk, location_id FK, geojson, summary, started_at |
| `risk_zones` | RiskZone | name, hazard_type, risk_score, risk_level, location_id, geojson |
| `weather_observations` | WeatherObservation | location_id, source, temp, humidity, rainfall, wind, pressure, conditions, observed_at |
| `weather_forecasts` | WeatherForecast | location_id, periods, temp, rainfall, wind, conditions |
| `satellite_images` | SatelliteImage | location_id, captured_at, provider, source, storage_path, bbox, lat/lon, resolution, cloud_cover, urls, metadata |
| `image_analysis_results` | ImageAnalysisResult | satellite_image_id FK, model_name, analysis_type, summary, confidence, result_geojson, metrics |
| `detected_objects` | DetectedObject | analysis_id FK, label, confidence, bbox_geojson |
| `flood_events` | FloodEvent | disaster_id FK, water_depth_m, extent_km2, geojson, detected_at |
| `damage_assessments` | DamageAssessment | disaster_id FK, target_type, damage_class, confidence, notes, geojson |
| `infrastructure` | Infrastructure | name, category, status, location_id, geojson |
| `roads` | Road | name, accessibility, location_id, geojson |
| `buildings` | Building | name, occupancy, damage_class, location_id, geojson |
| `rescue_resources` | RescueResource | name, type, status, personnel, capacity, lat/lon, assigned_incident, location_id, geojson |
| `evacuation_centers` | EvacuationCenter | name, capacity, occupied, status, location_id, geojson |
| `rescue_priorities` | RescuePriority | disaster_id, title, priority, people_affected, status, score, level, factors JSON |
| `rescue_plans` | RescuePlan | disaster_id, priority_id, decision, override_notes, payload JSON |
| `alerts` | Alert | title, severity, category, message, location, lat/lon, risk_score, status, actions, signals JSON |
| `users` | User | name, email unique, role |
| `audit_logs` | AuditLog | actor_id FK?, action, entity_type, entity_id, details |
| `vision_jobs` | VisionJob | filename, paths, model_name, backend, severity, detections JSON, incident JSON |
| `flood_analyses` | FloodAnalysis | model_name, scene_kind, area, %, severity, affected_*, geojsons, notes |
| `damage_reports` | DamageReport | model_name, before/after kind, report JSON, overlay_geojson |

**Model count exported in `models/__init__.py`:** **24** entity classes.

### Field-level excerpt (canonical demo)

| Table/Model | Field | Type | Required? | Default | Description |
| ----------- | ----- | ---- | --------- | ------- | ----------- |
| Location | id | String(36) PK | Yes | uuid | Demo Kuttanad id fixed in seed |
| Location | latitude | Float | Yes | — | 9.517 for Kuttanad |
| Location | longitude | Float | Yes | — | 76.522 for Kuttanad |
| Disaster | people_at_risk | Integer | Yes | 0 | 42000 for flood demo |
| Disaster | phase | String | Yes | — | precaution \| response \| recovery |
| SatelliteImage | source | String | Yes | mock-sentinel2 | Provider label |
| SatelliteImage | cloud_cover | Float | Yes | 8.0 | Demo cloud % |
| Alert | status | String | Yes | ACTIVE | ACTIVE / ACKNOWLEDGED / RESOLVED (via service) |
| RescuePlan | decision | String | Yes | PENDING | PENDING / accept / modify / reject path |
| VisionJob | backend | String | Yes | demo | demo or yolo |
| FloodAnalysis | confidence | Float | Yes | 0.55 | Heuristic confidence |
| DamageReport | model_name | String | Yes | demo-change-v0 | Change detection label |

Geometry is **JSON**, not native PostGIS.

### Seed data (high level)

From `backend/app/db/seed.py`:

- Locations: Kuttanad (`1111…`), Guwahati (`2222…`), Puri (`3333…`)
- Disasters: flood `aaaa…`, landslide `bbbb…`, cyclone `cccc…`
- Fixed NOW timestamp in seed: `2026-07-14 06:00:00`
- Also seeds risk zones, weather rows, satellite image rows, roads/buildings, resources, centers, priorities, alerts, users, etc.

---

## 8. Data Used by the Project

### A. Real external data

| API | Provider | Endpoint in code | Key | Active by default? |
| --- | --- | --- | --- | --- |
| OpenWeather Current/Forecast | OpenWeatherMap | `https://api.openweathermap.org/data/2.5/weather` (query `Alappuzha,IN`), forecast similarly | `OPENWEATHER_API_KEY` | **No** — needs `USE_MOCK_PROVIDERS=false` and key |
| Public basemap tiles | Carto/OSM via Leaflet | Browser tile URLs in map components | None | Yes (map background only) |

**Not found as active app integrations:** Copernicus Dataspace API inside backend, GEE, IMD official feeds, NASA POWER in `backend/` product path, NOAA in `backend/` product path.

Legacy `src/` has NASA/NOAA/OpenWeather route modules — **not used by the VisionGuard dashboard backend**.

OpenWeather note: even when live, `river_level_m` is taken from the **mock** snapshot in `OpenWeatherProvider.current`.

### B. Mock data

| File / provider | Location | Format | Purpose | Consumers |
| --- | --- | --- | --- | --- |
| `frontend/src/data/mock.ts` | frontend | TS objects | Offline UI | Most services when `isMockMode()` |
| `frontend/src/data/gisMock.ts` | frontend | GeoJSON FeatureCollections | Command map layers | `gis.ts`, maps — **always** |
| `MockWeatherProvider` | `backend/.../weather/mock_provider.py` | dataclasses | Fixed Kuttanad weather | WeatherIntel / WeatherService |
| `MockSatelliteProvider` | `backend/.../satellite/mock_provider.py` | SatelliteScene list | Fake catalog | SatelliteService |
| `DemoVisionModel` | `backend/.../vision/demo_model.py` | deterministic boxes | Fake detections | VisionPipeline default |
| `data/mock/satellite/kuttanad_demo.txt` | data/ | text | Placeholder note | Not a raster pipeline input |
| Notification adapters | `notifications.py` | log receipts | Fake email/SMS/push | Alert dispatch |

### C. Hardcoded / canonical demo values

| Name | Value | Where |
| --- | --- | --- |
| DEMO_INCIDENT_ID / DIS_FLOOD | `aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa` | demo.ts / seed.py / demo.py |
| DEMO_LOCATION_ID / LOC_KUTTANAD | `11111111-1111-4111-8111-111111111111` | same |
| Flood risk % | **82.0** | DEMO_STATS / DEMO_FLOOD_RISK_PCT / overlay_demo_flood |
| Flooded km² | **34.5** | DEMO_STATS / analytics overlay |
| Affected population | **42000** | seed Disaster + DEMO_STATS |
| Damaged buildings | **18** | DEMO_STATS |
| Blocked roads | **3** | DEMO_STATS |
| Data class label | `SIMULATED` | demo constants |
| Kuttanad coords | lat **9.517**, lon **76.522** | seed, mocks, defaults |
| Mock weather NOW | 2026-07-14 06:00 UTC | MockWeatherProvider |
| Mock temp / rain / river | 27.4°C, 48.2 mm, 3.1 m | MockWeatherProvider |
| Alert bands | watch 30 / warning 50 / critical 75 (flood) | `alerts/rules.json` |
| Max upload | 8 MB | `MAX_UPLOAD_MB` |
| Available rescue units KPI (frontend gis helper) | 4 | `gis.ts` dashboardKpis |

### D. Generated / simulated algorithmically

| Generator | Input | Output | Why |
| --- | --- | --- | --- |
| `generate_demo_raster(kind)` | scene kind string | 48×48 or 64×64 RGB | Stand-in for satellite |
| `detect_water` etc. | RGB | binary mask | Color thresholds |
| `BaselineFloodRiskModel` | rain, river, hist, terrain, soil | 0–100 probability | Transparent heuristic |
| `overlay_demo_flood` | model result | forced 82% when mock providers | Consistent demo story |
| `evaluate_cyclone` | wind, pressure, storm p, trend | cyclone score | Rule-based |
| `analyze_rainfall` | daily mm series | cumulative, intensity, anomaly, short_term_risk | Rule-based |
| `DemoVisionModel` | image size hash | fixed-position boxes | Demo CV without weights |
| `classify_building` / `classify_road` | change fractions | damage classes | Thresholds |
| `RescuePriorityService` | population, risk, roads, flood, … | 0–100 score + band | Decision support |
| `recommend_resources` | flood/pop/medical/roads | resource list | If/then rules |
| `routing.shortest_path` | demo graph | path nodes | No Google Maps |
| AlertEngine | fused scores vs rules.json | Alert rows | Prototype EW |

---

## 9. AI / Machine Learning Components

### Runtime (used by FastAPI)

| Component | File | Type | Loaded? | Used? | Real trained model? |
| --- | --- | --- | --- | --- | --- |
| `DemoVisionModel` | `vision/demo_model.py` | Deterministic fake boxes | Yes (default) | Yes | **No** |
| `YOLOVisionModel` | `vision/yolo_model.py` | Ultralytics YOLO if local file | Only if `YOLO_WEIGHTS_PATH` is a real file | Optional | Only if you supply weights; **ultralytics not in requirements.txt** |
| `DemoFloodModel` | `flood/models.py` | OpenCV water heuristic | Yes | Yes | **No** |
| `UNetModel` | `flood/models.py` | Placeholder | Instantiable | Raises `NotImplementedError` | **No** |
| `DeepLabModel` | `flood/models.py` | Placeholder | Instantiable | Raises `NotImplementedError` | **No** |
| Satellite color detectors | `satellite/processing.py` | Threshold masks | Yes | Yes | **No** |
| `BaselineFloodRiskModel` | `risk/flood.py` | Weighted formula | Yes | Yes | **No** (not ML) |
| Damage classify | `damage/classify.py` | Thresholds | Yes | Yes | **No** |

### Vision pipeline

1. Validate upload (type/size/magic) — `vision/validation.py`  
2. Decode image  
3. `get_vision_model()` → Demo or YOLO  
4. Detect → severity rules (`severity.py`) → incident suggestions (`incident.py`)  
5. Annotate JPEG → save under `VISION_STORAGE_DIR` → `vision_jobs` row  

**Demo classes include:** person, vehicle, bus, truck, building, damaged_building, road, blocked_road, bridge, flooded_vehicle, fire, rescue_person.

### Stub package `ai/`

- `ai/inference/runner.py` runs `StubFloodDetector` / `StubDamageClassifier`  
- **Not imported** by `backend/app`  
- No checkpoints bundled (`ai/models/README.md` says put them later)

**Explicit statement:** No trained disaster neural network weights are bundled or loaded by default.

---

## 10. Disaster / Risk / Flood Detection Logic

### Flood risk (probability)

**Input:** rainfall_mm, rainfall_intensity, river_level_m, historical_flood_frequency, terrain_elevation_m, soil_saturation  

**Processing (`BaselineFloodRiskModel`):** normalize each factor to 0–100, then:

```
probability =
  0.25*rain + 0.20*intensity + 0.20*river + 0.15*history + 0.10*terrain + 0.10*soil
```

**Levels:** ≥76 critical, ≥51 high, ≥26 moderate, else low.  

**When `use_mock_providers`:** `overlay_demo_flood` forces **82%** and `DEMO_FLOOD_FACTORS`.

### Cyclone risk

```
score = 0.35*wind_s + 0.25*pressure_s + 0.25*storm_s + 0.15*trend_s
```

### Rainfall analysis

cumulative sum; intensity = latest/hours; anomaly vs climatology 12 mm;  
`short_term_risk = clamp(latest*1.2 + intensity*40 + max(0,anomaly)*25)`.

### Flood detection (imagery)

**Input:** scene_kind (default `flood`), population (default 42000)  
→ synthetic RGB → `detect_water`: `(b > r+40) & (b > g+25) & (b > 100)`  
→ polygons / heatmap / `flooded_area_km2` / `affected_assets`  
→ severity from flood % (`classify_flood_risk`)  
→ store `FloodAnalysis`

### Damage assessment

Compare before/after synthetic rasters → change fractions → `classify_building` / `classify_road` thresholds → JSON report (`pdf_available=False`).

### Computer vision

Hash of `WxH` selects subset of template boxes → severity mapping → suggested actions. **Does not auto-call rescue planning.**

### Rescue planning

Priority score = sum of capped terms (population/800, stranded/200, risk weight×0.18, infra×10, road×0.12, flood×0.15, distance, medical×12), banded LOW/MEDIUM/HIGH/CRITICAL.  

Recommendations: boats if high flood + pop≥2000; helicopter if roads blocked; etc.  

Routing: hard-coded Kuttanad demo graph + cost `distance*(1+risk)*(1+3*blockage)`.

### Alerts

Fuse scores; compare to `rules.json` bands; persist `Alert`; `dispatch()` to dashboard + mock channels. Disclaimer: not official warnings.

### Satellite analysis

Select detector by analysis_type (flood/water/vegetation/burn/urban/landslide→urban) → mask → GeoJSON metrics.

### Situation monitoring

Frontend situation page + seeded disasters; map points from frontend mock helper — not a separate live feed service.

---

## 11. Satellite Imagery

| Question | Answer from code |
| --- | --- |
| Image source in app | **Synthetic NumPy RGB** via `generate_demo_raster` |
| Provider | `MockSatelliteProvider` (`name=mock-sentinel2`, `live=False`) |
| Factory | `get_satellite_provider()` **always** returns mock |
| `SentinelLandsatProvider` | Exists but still delegates to mock; **not returned** by factory |
| Live Copernicus/GEE in app | **Not connected** |
| IMD satellite | **Not found** |
| Preview format | PNG bytes from `encode_png` |
| Resolution field | Default string `"10m"` (metadata label, not real EO product) |
| Coordinates | ~9.517 N, 76.522 E (Kuttanad demo) |
| Catalog IDs | e.g. `sat-normal-001`, `sat-flood-before-001`, `sat-flood-after-001`, … |
| Cloud cover in catalog | Demo floats (e.g. 6.2, 9.4, 11.0) |
| Compare | `POST /satellite/compare` on two synthetic scenes |
| Metadata note | Explicitly: “Synthetic raster. Not Copernicus imagery.” |

**For a presentation of real Sentinel-2**, use the official Copernicus Browser externally — that is **outside** this application and **not wired** into VisionGuard.

---

## 12. Weather Data

| Item | Detail |
| --- | --- |
| Default provider | `MockWeatherProvider` (`live=False`) |
| Selection | `get_weather_provider()`: mock if `use_mock_providers` **or** no API key |
| Real provider | `OpenWeatherProvider` → OpenWeatherMap 2.5 API |
| Query place | `Alappuzha,IN` |
| Units | metric |
| Mock snapshot | 27.4°C, humidity 94%, rain 48.2 mm, wind 6.1 m/s, pressure 1004 hPa, river 3.1 m, storm_p 0.34, “Heavy rain” |
| Update frequency | **Not found** as a scheduler; on-demand request |
| Effect on risk | Feeds `WeatherIntelService.flood()` / cyclone / rainfall |
| Frontend | Weather page + dashboard weather card |

**Live vs mock:** Default demo = **mock**. Live OpenWeather only with env changes above; river level still mock-backed even then.

---

## 13. GIS / Maps

| Item | Detail |
| --- | --- |
| Library | Leaflet + react-leaflet |
| Primary data | `frontend/src/data/gisMock.ts` FeatureCollections |
| Layers (gisMock) | disasters, floodCurrent, floodPredicted, risk, roads, buildings, resources, evacuation, etc. |
| Demo geography | Kuttanad / Alappuzha ~ **76.52 E, 9.52 N** |
| Backend GeoJSON | Stored on many tables as JSON; **not** streamed as the command map source |
| Interactions | Layer toggles, feature select → `SelectedAreaPanel` |
| Rescue map | Uses plan/resources geometry + demo routing nodes |
| PostGIS spatial queries | **Not found** |

---

## 14. Complete Data Flow

### Workflow 1 — User opens dashboard

```mermaid
sequenceDiagram
  participant U as User
  participant D as DashboardPage
  participant S as services/*
  participant A as FastAPI /api/v1
  participant DB as Database / providers
  U->>D: open /dashboard
  D->>S: fetchDisasters, alerts, resources, weather, analytics, gis
  alt VITE_USE_MOCK true
    S-->>D: mock.ts + gisMock
  else mock false
    S->>A: GET multiple endpoints
    A->>DB: services + SQL / mock weather
    DB-->>A: data
    A-->>S: JSON
  end
  Note over D: Map always gisMock
  D-->>U: KPIs, map, charts
```

### Workflow 2 — Risk analysis

Weather snapshot → `BaselineFloodRiskModel.evaluate` → optional `overlay_demo_flood` (82%) → `FloodRiskOut` → Weather / Risk pages.

### Workflow 3 — Flood detection

`FloodPage` → `POST /flood/analyze` → synthetic raster → OpenCV water mask → GeoJSON + stats → `flood_analyses` → map overlay.

### Workflow 4 — Satellite analysis

`SatellitePage` → list images (mock sync) → preview PNG → `POST /satellite/analyze` → color detector → `image_analysis_results` → UI metrics/overlay.

---

## 15. API Documentation

Base URL (default): `http://127.0.0.1:8000`  
Interactive docs: `http://127.0.0.1:8000/docs`  

All product routes are under `/api/v1` as listed in §6.

### Representative request/response shapes (from schemas / services)

**Health**

```json
{ "status": "ok", "service": "VisionGuard AI", "environment": "development", "use_mock_providers": true }
```

**Flood analyze body**

```json
{ "scene_kind": "flood", "population": 42000 }
```

**Rescue decision body**

```json
{ "action": "accept", "notes": "" }
```

**Vision:** `multipart/form-data` field `file`.

**Errors:** FastAPI/`ApiError` style; validation failures return 422; missing entities 404 (e.g. rescue plan, flood event).

**Mock/live behavior:** Backend mock flag affects weather provider and demo flood overlay / analytics KPI forcing. Satellite remains mock regardless. Frontend mock flag can bypass HTTP entirely.

Full field-level Pydantic models live in `backend/app/schemas/common.py` — use `/docs` for live schema expansion.

---

## 16. Configuration

| Variable | Location | Current Value/Default | Purpose | Effect |
| -------- | -------- | --------------------- | ------- | ------ |
| `ENVIRONMENT` | `.env.example` / Settings | `development` | Env label | Shown in health |
| `DATABASE_URL` | same | `sqlite:///./visionguard.db` | DB | SQLite vs Postgres |
| `CORS_ORIGINS` | same | Vite localhost URLs | CORS | Allowed browser origins |
| `USE_MOCK_PROVIDERS` | same | `true` | Weather/analytics demo | Mock weather + 82% overlay |
| `OPENWEATHER_API_KEY` | same | empty | OpenWeather | `[API KEY REQUIRED]` for live |
| `LOG_LEVEL` | same | `INFO` | Logging | Log verbosity |
| `VISION_STORAGE_DIR` | same | `./storage/vision` | Upload storage | Vision files on disk |
| `YOLO_WEIGHTS_PATH` | same | empty | Local YOLO | Empty → DemoVisionModel |
| `MAX_UPLOAD_MB` | same | `8` | Upload limit | Reject large files |
| `ENABLE_REAL_EMAIL` | same | `false` | Email flag | Still unwired if true |
| `ENABLE_REAL_SMS` | same | `false` | SMS flag | Still unwired if true |
| `ENABLE_REAL_PUSH` | same | `false` | Push flag | Still unwired if true |
| `SMTP_HOST` | same | empty | SMTP | Needed for email attempt (still refused) |
| `SMS_API_KEY` | same | empty | SMS | `[API KEY REQUIRED]` if used |
| `PUSH_API_KEY` | same | empty | Push | `[API KEY REQUIRED]` if used |
| `VITE_API_BASE_URL` | `frontend/.env.example` | `http://127.0.0.1:8000` | API base | Fetch target |
| `VITE_USE_MOCK` | frontend | `true` | FE mock | Not `"false"` → mock.ts |

Do not commit real secrets. If a secret is present locally, treat as `[SECRET CONFIGURED]`.

---

## 17. Current Run Configuration

### Backend

```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --app-dir .
```

- Port: **8000**  
- URL: http://127.0.0.1:8000  
- Docs: http://127.0.0.1:8000/docs  

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

- Port: **5173**  
- URL: http://127.0.0.1:5173/dashboard  

### Database

- Default: SQLite file `visionguard.db` under backend working directory  
- Optional Compose: Postgres/PostGIS container  

### AI

- Default: no weights required (`DemoVisionModel`, `DemoFloodModel`)  
- Optional: set `YOLO_WEIGHTS_PATH` to an existing local file; install ultralytics yourself (not in requirements)

### Mock / live switches

| Switch | Default | When changed |
| --- | --- | --- |
| `VITE_USE_MOCK` | true | `"false"` → browser hits API |
| `USE_MOCK_PROVIDERS` | true | false + OpenWeather key → live weather (partial) |
| Satellite | always mock | No env switch in factory |

### Docker

```text
docker compose up
```

Compose sets mock providers true and FE mock true. Requires Docker engine running.

---

## 18. End-to-End Example

**Action:** User opens Flood Detection and clicks Run.

1. Route `/flood-detection` → lazy `FloodPage.tsx`  
2. Click handler calls `analyzeFlood` in `frontend/src/services/flood.ts`  
3. If not FE mock: `POST /api/v1/flood/analyze` with `{ scene_kind, population: 42000 }`  
4. `router.flood_analyze` → `FloodDetectionService.analyze`  
5. `generate_demo_raster("flood", size=64)`  
6. `DemoFloodModel.segment` → `detect_water`  
7. `flooded_area_km2`, `extract_polygons`, `affected_assets`, `classify_flood_risk`  
8. Row saved to `flood_analyses`  
9. JSON returned → page shows area, %, severity, notes (“not a trained semantic segmentation model”)  
10. Overlay drawn with `SatelliteOverlayMap`  

Same pattern applies to rescue Accept → `POST /rescue/plans/{id}/decision` → `RescuePlanningService.decide` → `AuditLog`.

---

## 19. Current Features vs Future Features

| Feature | Implemented? | Real Data? | Mock? | Notes |
| ------- | ------------ | ---------- | ----- | ----- |
| React ops console | Yes | Partial | Yes (default FE) | Full routes |
| FastAPI `/api/v1` | Yes | DB real for seed | Providers mock | Active |
| SQLite seed | Yes | Demo | Simulated scenario | Active |
| Weather display | Yes | Optional OW | Default mock | River often mock |
| Flood risk formula | Yes | Calculated | 82% overlay in mock | Rule-based |
| Satellite catalog/preview | Yes | No | Synthetic | Always mock provider |
| Flood detection UI | Yes | No | Heuristic | OpenCV |
| Damage assessment | Yes | No | Heuristic | No PDF |
| Computer vision upload | Yes | No | Demo boxes | YOLO optional |
| Rescue plan + decision | Yes | DB writes | Rules + demo graph | Human-in-loop |
| Alerts engine | Yes | DB | Rule-based | Not official |
| Analytics + CSV | Yes | Aggregates | Demo KPI force | Active |
| SSE alerts | Yes | In-memory | — | FE skips in mock |
| OpenWeather | Code yes | If configured | — | **Inactive by default** |
| Live Sentinel | No | — | — | Factory always mock |
| U-Net / DeepLab | Stub only | — | — | NotImplementedError |
| Real SMS/email | No | — | Mock/refuse | Unwired |
| Auth / RBAC | No | — | — | User table exists; unused for login |
| Alembic | No | — | — | Documented future |
| PDF reports | No | — | — | `pdf_available=false` |
| `ai/` package | Stub | — | — | Not wired |
| Legacy `src/` APIs | Separate | Possible if run alone | — | Not dashboard |

### Currently implemented
Full FE+BE prototype path for the Kuttanad demo story.

### Partially implemented
OpenWeather adapter; YOLO path; notification flags; PostGIS Docker image without PostGIS ORM usage; User model without auth.

### Demo/simulated
KPIs 82 / 34.5 / 42000 / 18 / 3; synthetic satellite; demo vision; gisMock; mock weather.

### Planned / future (from stubs & docs in code, not delivered)
Real Sentinel/GEE, trained flood models, wired SMTP/SMS, Alembic, auth, PDF, replace `ai/` stubs.

---

## 20. Limitations

1. Default data path is mock / simulated — not operational EO or IMD.  
2. Satellite provider factory never returns a live client.  
3. Flood/damage “AI” is OpenCV/heuristics, not trained segmentation.  
4. U-Net/DeepLab raise `NotImplementedError`.  
5. Demo vision invents boxes from image dimensions.  
6. YOLO not a declared dependency; no auto-download of weights.  
7. Email/SMS/push never actually send.  
8. No authentication/authorization on API.  
9. Command GIS is static frontend GeoJSON, not live DB geometry.  
10. SQLite default; no Alembic migrations.  
11. PDF generation not implemented.  
12. Analytics may force demo KPIs when mock providers on.  
13. Legacy `src/` and stub `ai/` can confuse reviewers if mistaken for the product path.  
14. SSE alert stream is process-local memory, not a durable message bus.  
15. Rescue routing is a tiny hand-built graph.

---

## 21. Security

| Topic | Current state |
| --- | --- |
| Authentication | **Not implemented** (no JWT/session middleware found) |
| Authorization | **Not implemented** (User.role unused for gating) |
| API keys | OpenWeather/SMS/Push via env; not exposed in FE |
| CORS | Restricted to configured origins |
| Input validation | Pydantic models; vision file validation (type/size/magic) |
| Upload limits | `MAX_UPLOAD_MB` default 8 |
| Secrets in repo | `.env.example` empty keys; do not commit real `.env` |
| DB security | Local SQLite file / Compose password in compose file (demo only) |
| Exception leakage | Handlers avoid returning stack traces to clients |
| Limitations | Open API surface; anyone who can reach port 8000 can call endpoints |

---

## 22. Testing

### Backend (`backend/tests/`)

| File | Focus |
| --- | --- |
| `test_api.py` | API basics |
| `test_weather_risk.py` | Weather / risk |
| `test_satellite.py` | Satellite |
| `test_flood_damage.py` | Flood / damage |
| `test_vision.py` | Vision |
| `test_rescue.py` | Rescue |
| `test_alerts.py` | Alerts |
| `test_analytics.py` | Analytics |
| `test_journey.py` | End-to-end journey |
| `conftest.py` | Fixtures |

Command (from project docs/README pattern):

```powershell
cd backend
pytest
```

### Frontend

Vitest tests under `frontend/src/**/*.test.ts(x)` (utils + `KpiCard.test.tsx`).

```powershell
cd frontend
npm test
```

### AI stubs

`ai/tests/test_stubs.py` — stub package only.

### Coverage percentage

**Not found as a committed coverage report** in the repository.

---

## 23. Deployment

| Artifact | Status |
| --- | --- |
| `docker-compose.yml` | Present: postgis, backend, frontend |
| `docker/backend.Dockerfile` | Python 3.12-slim, uvicorn :8000 |
| `docker/frontend.Dockerfile` | Present |
| Production hardening | **Not found** (no reverse proxy config, no HTTPS setup in repo) |
| Cloud IaC | **Not found** |
| Build scripts | `npm run build` (frontend); pip requirements (backend) |

**Ready for:** local demo and Compose-based lab deployment.  
**Not ready for:** production emergency operations (auth, live EO, real notifications, hardened secrets).

---

## 24. Important Code-Level Components

| Component | File | Class/Function | Purpose |
| --------- | ---- | -------------- | ------- |
| FastAPI app | `backend/app/main.py` | `app`, `lifespan` | Boot, CORS, router |
| Settings | `backend/app/core/config.py` | `Settings` | Env config |
| Demo constants | `backend/app/core/demo.py` | `DEMO_*` | Canonical KPIs |
| API router | `backend/app/api/v1/router.py` | route functions | HTTP surface |
| Seed | `backend/app/db/seed.py` | `seed`, `seed_if_empty` | Demo DB |
| Weather factory | `weather/factory.py` | `get_weather_provider` | Mock vs OW |
| Weather intel | `weather_intel.py` | `WeatherIntelService` | Risk/weather facade |
| Flood risk model | `risk/flood.py` | `BaselineFloodRiskModel`, `overlay_demo_flood` | Probability |
| Cyclone | `risk/cyclone.py` | `evaluate_cyclone` | Score |
| Satellite service | `satellite/service.py` | `SatelliteService` | Catalog/analyze |
| Raster ops | `satellite/processing.py` | `generate_demo_raster`, `detect_*` | Synthetic EO |
| Flood service | `flood/service.py` | `FloodDetectionService` | Flood pipeline |
| Damage service | `damage/service.py` | `DamageAssessmentService` | Damage pipeline |
| Vision factory | `vision/factory.py` | `get_vision_model` | Demo/YOLO |
| Vision pipeline | `vision/pipeline.py` | `VisionPipeline.run` | Upload→detect |
| Rescue | `rescue/service.py` | `RescuePlanningService` | Plan/decision |
| Priority | `rescue/priority.py` | `RescuePriorityService` | Scoring |
| Recommend | `rescue/recommend.py` | `recommend_resources` | Resource rules |
| Routing | `rescue/routing.py` | `shortest_path` | Demo graph |
| Alerts | `alerts/service.py` | `EarlyWarningService` | Generate/ack |
| Notifications | `alerts/notifications.py` | `dispatch` | Mock channels |
| Analytics | `analytics/service.py` | `AnalyticsService` | KPIs/CSV |
| Incident | `incident/service.py` | `IncidentCommandService.picture` | Combined view |
| FE api client | `frontend/src/services/apiClient.ts` | `apiGet/Post/Upload`, `isMockMode` | HTTP |
| FE routes | `frontend/src/App.tsx` | `App` | Router |
| GIS | `frontend/src/services/gis.ts` | `fetchGisCatalog` | Always gisMock |
| Demo IDs FE | `frontend/src/constants/demo.ts` | `DEMO_*` | Align with backend |

---

## 25. Complete Project Explanation in Simple Language

### What is the project?
VisionGuard AI is a **student/prototype disaster command dashboard** for a **demo flood in Kuttanad, Kerala**.

### Why did we build it?
To show an end-to-end decision-support workflow: weather → risk → imagery → flood/damage estimates → rescue proposal → alerts → analytics — with honest labels that it is a prototype.

### How does it work?
A React website talks to a FastAPI backend. The backend stores demo incidents in a database and runs formulas, OpenCV tricks, and demo detectors. The UI draws maps and charts.

### What technologies did we use?
React, TypeScript, Vite, Tailwind, Leaflet, Chart.js, FastAPI, SQLAlchemy, SQLite (or Postgres), NumPy, OpenCV.

### Where does the data come from?
Mostly **seeded demo data**, **mock weather**, **synthetic satellite images**, and **static GeoJSON** on the frontend. Optional OpenWeather if configured.

### Where is AI used?
“AI-looking” outputs are mostly **rules and heuristics**. Default computer vision is a **demo model**, not a trained disaster network. Optional YOLO only with a local weights file.

### Where is computer vision used?
Satellite color masks, flood water masks, damage change heuristics, and the Computer Vision upload page.

### Where is GIS used?
Leaflet maps with demo layers for flood, risk, roads, buildings, resources around Kuttanad coordinates.

### Where is the database used?
Disasters, zones, resources, alerts, vision jobs, flood analyses, damage reports, rescue plans, audits, etc.

### What is currently real?
Real running web app + API + database of demo rows; optional real OpenWeather; real file upload handling; real PNG generation from arrays.

### What is currently simulated?
82% risk, 34.5 km², population 42k, synthetic satellites, demo detections, mock notifications, gisMock map.

### What will be added in the future?
Live satellite access, trained models, real notification clients, authentication, migrations, production deployment hardening — behind the same service interfaces.

---

## 26. Viva Questions and Answers

**Q: Why this architecture?**  
**A:** Separation of React UI and FastAPI services lets us swap mock providers for real APIs later without rewriting every page. Pages call `services/*`, which call `/api/v1`.

**Q: Why React + Vite?**  
**A:** Fast SPA for maps/charts; TypeScript for safer API types; Vite is the configured build tool in `package.json`.

**Q: Why FastAPI?**  
**A:** Typed Python APIs with Pydantic schemas, automatic `/docs`, and easy service modules for weather/risk/vision.

**Q: Why this database?**  
**A:** SQLAlchemy with SQLite by default for zero-setup demos; Compose can point at Postgres. Geometry is JSON for SQLite compatibility — PostGIS types are not used in models.

**Q: Where is AI used?**  
**A:** Risk formulas, OpenCV flood/satellite heuristics, demo vision boxes, optional YOLO. No bundled trained U-Net.

**Q: What data is used?**  
**A:** Seeded Kuttanad flood scenario, mock weather numbers, synthetic rasters, frontend gisMock, optional OpenWeather.

**Q: Where does satellite data come from?**  
**A:** Inside the app: `MockSatelliteProvider` + `generate_demo_raster`. Not Copernicus live API.

**Q: Is satellite data live?**  
**A:** **No.** Metadata even says synthetic / not Copernicus.

**Q: Is weather data live?**  
**A:** **Not by default.** Only if mock providers are off and an OpenWeather key is set.

**Q: What is mock data?**  
**A:** Hard-coded or generated stand-ins used so the UI works without external keys — `mock.ts`, mock providers, demo rasters.

**Q: How is flood risk calculated?**  
**A:** Weighted sum of rainfall, intensity, river, history, terrain, soil; then in mock mode overlaid to **82%**.

**Q: What model is used for flood imagery?**  
**A:** `DemoFloodModel` — blue-channel OpenCV threshold. U-Net/DeepLab exist only as stubs that raise errors.

**Q: What if the vision model is unavailable?**  
**A:** Default is always DemoVisionModel. YOLO is used only when a local weights path exists; otherwise demo.

**Q: How do frontend and backend communicate?**  
**A:** `fetch` via `apiClient.ts` to `VITE_API_BASE_URL` + `/api/v1/...`, unless `VITE_USE_MOCK` keeps the UI on local mock JSON.

**Q: Why GIS?**  
**A:** Officers need spatial context — inundation, risk polygons, resources — shown with Leaflet.

**Q: Limitations?**  
**A:** Mock EO/weather by default, no auth, no real SMS, no trained flood net, static gisMock, prototype alerts only.

**Q: What for real-world deployment?**  
**A:** Live weather keys, real satellite provider, trained models, auth, PostGIS if needed, real notification providers, hardened hosting — without changing the operator workflow screens.

---

## 27. Final "Truth Table" of the Project

| Component | Current Implementation | Real/Mock/Simulated | Source/File | Status |
| --------- | ---------------------- | ------------------- | ----------- | ------ |
| Frontend | React SPA | UI real; data often mock | `frontend/` | Active |
| Backend | FastAPI `/api/v1` | Real HTTP server | `backend/app/` | Active |
| Database | SQLAlchemy SQLite default | Real DB of demo rows | `session.py`, `entities.py` | Active |
| Weather | MockWeatherProvider default | Mock (OW optional) | `weather/*` | Default mock |
| Satellite | MockSatelliteProvider + synthetic PNG | Mock/simulated | `satellite/*` | Always mock |
| AI (risk) | Weighted formulas | Rule-based / simulated overlay | `risk/flood.py` | Active |
| Computer Vision | DemoVisionModel (+ optional YOLO) | Mock (YOLO optional) | `vision/*` | Default mock |
| Flood detection | OpenCV water mask | Heuristic | `flood/*` | Active demo |
| Risk calculation | BaselineFloodRiskModel + overlay | Rule-based / SIMULATED 82% | `risk/*` | Active |
| GIS | Leaflet + gisMock | Static demo GeoJSON | `gisMock.ts` | Active |
| Alerts | AlertEngine + rules.json | Rule-based prototype | `alerts/*` | Active |
| Rescue planning | Scores + rules + demo graph | Rule-based / simulated inventory | `rescue/*` | Active |
| External APIs | OpenWeather optional | Inactive by default | `openweather_provider.py` | Configured, inactive |
| Government data | — | Not connected | — | Not found |
| Authentication | — | Not implemented | — | Missing |
| Notifications | Dashboard + mock email/SMS/push | Mock / refused_unwired | `notifications.py` | Non-sending |
| `ai/` package | Stubs | Unused at runtime | `ai/` | Stub |
| Legacy `src/` | Separate FastAPI | Unused by dashboard | `src/` | Legacy |
| Deployment | Docker Compose present | Lab/demo | `docker-compose.yml` | Optional |

---

*End of complete project documentation. Generated from repository inspection; only this file was added under `docs/`.*
