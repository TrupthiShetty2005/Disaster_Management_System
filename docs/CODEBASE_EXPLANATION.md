# VisionGuard AI — Codebase explanation (what exists today)

This file explains the **current code** in simple language. Real API keys and live satellite/government feeds are **not** wired in this project. If something is mock, simulated, rule-based, or not connected, this document says so.

**How to read this:** start at the end (“Study order”) if you are new. Skip details until you need them.

---

## 0. What this project is

VisionGuard AI is a **demo / prototype** disaster operations console.

- A **React website** (`frontend/`) shows maps, charts, and pages.
- A **FastAPI server** (`backend/`) answers `/api/v1/...` HTTP requests.
- A **database** stores seeded demo disasters (SQLite by default).
- **AI-looking outputs** come from demo models, OpenCV color tricks, or weighted formulas — **not** from trained disaster neural networks in this repo.

The UI header can show **DEMO MODE**. Many screens also say outputs are simulated or prototype estimates.

There is an older Python API under `src/`. The new dashboard does **not** call it. The product path is `frontend/` + `backend/`.

---

## 1. Complete folder and file structure

Top level (the pieces that matter):

```
Disaster_Management_System/
├── README.md
├── prompts                          # written Cursor prompts (not executed code)
├── docker-compose.yml
├── .env.example                     # example backend env (no secrets)
├── docker/
│   ├── backend.Dockerfile
│   └── frontend.Dockerfile
├── docs/                            # this file plus architecture/API notes
├── scripts/
│   ├── seed.py
│   └── seed_demo_data.py
├── data/mock/satellite/
│   └── kuttanad_demo.txt            # text placeholder, not a real image
├── frontend/                        # React + Vite UI
├── backend/                         # FastAPI app the UI is meant to use
├── ai/                              # separate stub package (not imported by backend)
└── src/                             # legacy FastAPI (NASA/NOAA/OpenWeather routes)
```

`venv/`, `node_modules/`, `__pycache__/`, `.pytest_cache/`, and SQLite `*.db` files may exist on disk after you run the app. They are generated, not “source design.”

### `frontend/`

```
frontend/
├── index.html
├── package.json                     # npm scripts: dev, build, lint, test
├── vite.config.ts                   # Vite + Vitest; port 5173
├── eslint.config.js, tailwind.config.js, postcss.config.js
├── .env.example                     # VITE_API_BASE_URL, VITE_USE_MOCK
└── src/
    ├── main.tsx                     # starts React
    ├── App.tsx                      # all page routes
    ├── styles/index.css
    ├── constants/demo.ts            # shared demo incident IDs and KPI numbers
    ├── types/api.ts, types/gis.ts
    ├── data/mock.ts, data/gisMock.ts
    ├── hooks/useAsync.ts, useAlertStream.ts
    ├── layouts/AppLayout.tsx
    ├── maps/index.ts, charts/index.ts   # re-exports
    ├── services/                    # ALL HTTP / mock data for pages
    ├── components/                  # shared UI (map, table, badges, …)
    ├── pages/                       # one screen per route
    └── utils/*.test.ts              # small unit tests
```

### `backend/`

```
backend/
├── requirements.txt
├── pytest.ini, ruff.toml
├── app/
│   ├── main.py                      # FastAPI app, CORS, startup
│   ├── core/config.py, errors.py, logging.py, demo.py
│   ├── db/session.py, init_db.py, seed.py
│   ├── db/migrations/README.md      # says Alembic is not set up yet
│   ├── models/entities.py           # SQLAlchemy tables
│   ├── schemas/common.py            # request/response shapes
│   ├── repositories/ops.py          # simple DB reads
│   ├── api/v1/router.py             # every /api/v1 route
│   └── services/                    # weather, risk, satellite, vision, flood, …
└── tests/                           # pytest
```

### `ai/`

```
ai/
├── inference/runner.py
├── services/flood.py, damage.py, vision.py
├── preprocessing/raster.py, normalize.py
├── postprocessing/geojson.py
├── models/README.md                 # “put checkpoints here later”
└── tests/test_stubs.py
```

The running FastAPI app does **not** `import` this `ai/` package. Flood/vision/damage at runtime live in `backend/app/services/`.

### `src/` (legacy)

```
src/main.py
src/app/routes/openweather.py, noaa.py, nasa.py
src/app/services/openweather_services.py, noaa_services.py, nasa_services.py
src/app/config/settings.py
```

This is a **different** FastAPI app. It is not mounted in `backend/app/main.py`.

---

## 2. Purpose of each folder and important file

| Place | Purpose |
| --- | --- |
| `frontend/src/pages/` | Screens you navigate to |
| `frontend/src/components/` | Reusable bits (map, KPI card, sidebar) |
| `frontend/src/services/` | Fetch data. Pages should not call `fetch` themselves |
| `frontend/src/data/` | Hard-coded mock JSON / GeoJSON when mock mode is on |
| `backend/app/main.py` | Starts the API, creates tables, seeds if empty |
| `backend/app/api/v1/router.py` | HTTP endpoints |
| `backend/app/services/` | Business logic |
| `backend/app/models/entities.py` | Database tables |
| `backend/app/db/seed.py` | Demo Kuttanad flood + extra demo disasters |
| `backend/app/core/demo.py` | Same IDs/numbers as the frontend demo constants |
| `docs/` | Human docs (architecture, API, this explanation) |
| `scripts/` | Seed wrappers that `chdir` into `backend/` |
| `docker-compose.yml` | Optional Postgres + backend + frontend containers |

---

## 3. How files are connected (big picture)

```
Browser
  → frontend/src/main.tsx
  → App.tsx routes
  → a Page
  → services/*.ts  (mock OR fetch)
  → http://127.0.0.1:8000/api/v1/...
  → backend/app/api/v1/router.py
  → a Service class
  → SQLAlchemy models / mock providers / OpenCV / demo “AI”
  → JSON back to the page
```

**Two switches (both exist in code):**

1. **Frontend** `VITE_USE_MOCK`  
   - If it is **not** the string `"false"`, `isMockMode()` is true.  
   - Services return objects from `frontend/src/data/mock.ts` and never need the backend.  
   - Many services still `try` the API and fall back to mock on error.

2. **Backend** `USE_MOCK_PROVIDERS` (default **true** in settings)  
   - Weather factory returns `MockWeatherProvider` if this is true **or** if there is no OpenWeather key.  
   - Flood risk then also applies `overlay_demo_flood()` so demo flood probability is **82%** and labeled SIMULATED.

GIS map layers are special: `frontend/src/services/gis.ts` **always** returns `gisCatalog` from `gisMock.ts`. It does not load GeoJSON from the API.

The `ai/` folder is a **parallel stub**. Runtime flood/vision is **backend** code.

---

## 4. Actual data flow: Frontend → API → Backend → Services/AI → Database → Frontend

### Step A — You open a page

Example: `/dashboard`.

1. `App.tsx` renders `DashboardPage`.
2. `useAsync(...)` runs several service functions at once (`fetchDisasters`, `fetchAlerts`, `fetchResources`, `fetchWeatherCurrent`, `fetchAnalytics`, `fetchGisCatalog`).
3. If mock mode: data comes from `mock.ts` / `gisMock.ts`. Stop here. Nothing hits FastAPI.
4. If mock mode is off: `apiGet("/api/v1/...")` in `apiClient.ts` uses `VITE_API_BASE_URL` (default `http://127.0.0.1:8000`).

### Step B — FastAPI receives the request

1. `backend/app/main.py` included the router with prefix `/api/v1`.
2. `get_db()` opens a SQLAlchemy session (SQLite URL from settings, or Postgres if you set `DATABASE_URL`).
3. The matching function in `router.py` runs.

### Step C — Services

Examples:

- `GET /disasters` → `DisasterService` → `DisasterRepository` → table `disasters`.
- `GET /weather/current` → `WeatherService` / `WeatherIntelService` → **weather provider** (mock unless OpenWeather is actually selected).
- `GET /risk/flood` → `WeatherIntelService.flood()` → `BaselineFloodRiskModel` (math) → optional `overlay_demo_flood()`.
- `POST /vision/analyze` → `VisionPipeline` → `DemoVisionModel` (or YOLO if a **local** weights file exists) → save files + `vision_jobs` row.
- `POST /flood/analyze` → `FloodDetectionService` → `DemoFloodModel` (OpenCV water mask) → `flood_analyses` row.
- `POST /alerts/generate` → `EarlyWarningService` + `AlertEngine` + `rules.json` → `alerts` rows. SMS/email adapters **log mock / refuse**; they do not send.

### Step D — Database

On startup: `init_db()` (`create_all` + a few SQLite `ALTER TABLE` helpers) then `seed_if_empty()`.

There is **no Alembic migration runner** in this repo. `backend/app/db/migrations/README.md` says Alembic can be added later.

Geometry is stored as **JSON GeoJSON**, not PostGIS types, so SQLite works.

### Step E — JSON returns to React

Pydantic schemas in `schemas/common.py` shape the JSON. The page puts numbers into `KpiCard`, tables, Leaflet, or Chart.js.

---

## 5. Frontend: important functions, components, routes

### Entry and layout

- `main.tsx` — mounts `<App />` and CSS.
- `App.tsx` — React Router. `/` goes to `/dashboard`. Extra redirects: `/risk` → `/risk-intelligence`, `/flood` → `/flood-detection`, `/damage` → `/damage-assessment`, `/rescue` → `/rescue-planning`, `/live-situation` → `/situation`. Most pages are **lazy-loaded**. Unknown URLs go to dashboard.
- `AppLayout` — sidebar, header, incident bar, `<Outlet />` for the page. Loads alert count via `fetchAlerts`.
- `Sidebar` — nav links, including incident command using `DEMO_INCIDENT_ID`.
- `Header` — title, DEMO MODE text, alert button.
- `IncidentBar` — always shows the Kuttanad demo incident link.

**Pages that exist as files but are not routed in `App.tsx`:** `OverviewPage.tsx`, `RiskPage.tsx`. They are unused by the router.

### Pages (what each screen does)

| Route | File | What it does |
| --- | --- | --- |
| `/dashboard` | `DashboardPage.tsx` | KPIs, `DisasterMap`, weather snippet, alerts, charts |
| `/weather` | `WeatherPage.tsx` | Current weather, rainfall, flood/cyclone scores, Chart.js lines |
| `/risk-intelligence` | `RiskIntelligencePage.tsx` | Map + zone list + contributing factors |
| `/situation` | `SituationPage.tsx` | Disaster table + `SituationMap` |
| `/satellite` | `SatellitePage.tsx` | Image list, analyze, overlay map |
| `/satellite/compare` | `SatelliteComparePage.tsx` | Before/after compare |
| `/computer-vision` | `ComputerVisionPage.tsx` | File upload → `analyzeVision` |
| `/flood-detection` | `FloodPage.tsx` | Run flood analysis, show GeoJSON on map |
| `/damage-assessment` | `DamagePage.tsx` | Before/after, doughnut charts, report JSON |
| `/rescue-planning` | `RescuePage.tsx` | Priorities, generate plan, accept/modify/reject |
| `/alerts` | `AlertsPage.tsx` | List, generate, ack, resolve, optional SSE |
| `/analytics` | `AnalyticsPage.tsx` | KPI cards + trend charts |
| `/disasters/:id` | `DisasterDetailPage.tsx` | One incident “command” picture |
| `/settings` | `SettingsPage.tsx` | Demo IDs, CSV/report buttons |

### Shared components (short)

- `KpiCard` — number + label.
- `StatusBadge` — colored chip from a string (high, blocked, …).
- `DataTable` — HTML table.
- `Feedback.tsx` — loading / error / empty / modal / drawer.
- `SafetyBanner` / `EstimateCallout` — prototype disclaimer and “SIMULATED vs RULE-BASED” labels.
- `DisasterMap` — Leaflet map of `gisMock` layers (risk, flood, roads, buildings, resources, …).
- `SatelliteOverlayMap`, `SituationMap`, `RescuePlanningMap` — other Leaflet maps.
- `DashboardCharts` / `TrendCharts` — Chart.js (`react-chartjs-2`).
- `AlertPanel` — alert list + filters.

### Services (the only HTTP layer)

`apiClient.ts`: `apiGet`, `apiPost`, `apiUpload`, `apiBase`, `isMockMode`, `ApiError`.

Each domain file (`disasters.ts`, `weather.ts`, `alerts.ts`, `satellite.ts`, `vision.ts`, `flood.ts`, `damage.ts`, `rescue.ts`, `analytics.ts`, `incident.ts`, `ops.ts`, `risk.ts`, `reports.ts`) either returns mock data or calls `/api/v1/...`.

`intel.ts` — leftover stubs for satellite/flood/damage **notes** (hard-coded strings). `fetchAnalytics` is re-exported from `analytics.ts`. `fetchMapPoints` always returns `mockMapPoints`.

`gis.ts` — always `gisCatalog` from `gisMock.ts`. `dashboardKpis` copies `DEMO_STATS`.

### Hooks

- `useAsync` — run a promise; expose `{ data, error, loading }`.
- `useAlertStream` — if **not** mock mode, `EventSource` to `/api/v1/alerts/stream`, else skip; also polls `/alerts/events`.

### Constants

`constants/demo.ts` matches backend `app/core/demo.py`:

- Incident ID `aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa`
- Location ID `11111111-1111-4111-8111-111111111111`
- Simulated stats: flood risk 82%, flooded 34.5 km², population 42,000, 18 buildings, 3 roads

### Libraries actually used on the frontend

From `package.json` and imports in `src/`:

| Library | Where |
| --- | --- |
| React, react-dom | whole UI |
| react-router-dom | `App.tsx`, `Link`, `NavLink`, `useParams` |
| leaflet, react-leaflet | map components |
| chart.js, react-chartjs-2 | weather, dashboard, damage, analytics charts |
| Tailwind (via PostCSS) | styling |
| Vite, TypeScript, ESLint, Vitest, Testing Library | build/test only |

---

## 6. Backend: important classes, functions, and API routes

### Startup (`app/main.py`)

On boot: logging → `init_db()` → `seed_if_empty()`. CORS origins come from `Settings.cors_origins`. Exception handlers hide stack traces from clients (`errors.py`).

`GET /` returns service name, `/docs`, `/api/v1`.

### Config (`app/core/config.py`)

Reads `.env`. Defaults include SQLite, `use_mock_providers=true`, empty OpenWeather key, `yolo_weights_path` empty, real email/SMS/push flags **false**.

`app/core/demo.py` — canonical demo IDs, 82 / 34.5 / 42000 / 18 / 3, factor list, story `DEMO_NARRATIVE`.

### Database models (`models/entities.py`)

Tables (all IDs are strings): `locations`, `disasters`, `risk_zones`, `weather_observations`, `weather_forecasts`, `satellite_images`, `image_analysis_results`, `detected_objects`, `flood_events`, `damage_assessments`, `infrastructure`, `roads`, `buildings`, `rescue_resources`, `evacuation_centers`, `rescue_priorities`, `rescue_plans`, `alerts`, `users`, `audit_logs`, `vision_jobs`, `flood_analyses`, `damage_reports`.

Foreign keys: disasters/risk/weather/satellite/resources/centers → `locations`; many operational rows → `disasters`.

### Repositories (`repositories/ops.py`)

Thin wrappers: list/get disasters, risk zones, weather rows, alerts, resources, evacuation centers.

### API routes (`/api/v1` from `router.py`)

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/health` | `{ status, service, environment, use_mock_providers }` |
| GET | `/disasters` | List (optional `phase`) |
| GET | `/disasters/{id}` | One disaster |
| GET | `/risk-zones` | Zones + `RiskService.explain()` (scores/factors) |
| GET | `/risk-zones/{id}` | One zone explained |
| GET | `/risk/flood` | Flood probability from weather intel |
| GET | `/risk/cyclone` | Cyclone score from wind/pressure formula |
| GET | `/weather/current` | Snapshot from weather provider |
| GET | `/weather/forecast` | Forecast list |
| GET | `/weather/history` | History points |
| GET | `/weather/rainfall` | `analyze_rainfall` on history |
| GET | `/weather/alerts` | Provider alerts + maybe persist risk candidates |
| GET | `/alerts` | Stored alerts |
| GET | `/alerts/stream` | SSE of in-memory events |
| GET | `/alerts/events` | Poll same events |
| POST | `/alerts/generate` | Run alert engine |
| GET | `/alerts/{id}` | One alert |
| POST | `/alerts/{id}/acknowledge` | Status ACKNOWLEDGED |
| POST | `/alerts/{id}/resolve` | Status RESOLVED |
| GET | `/resources` | Rescue units |
| POST | `/resources/allocate` | Mark unit deployed to an incident |
| GET | `/rescue/priorities` | Priority list (scored) |
| POST | `/rescue/plan` | Build JSON plan, save `rescue_plans` |
| GET | `/rescue/plans/{id}` | Fetch plan |
| POST | `/rescue/plans/{id}/decision` | `accept` / `modify` / `reject` + audit log |
| GET | `/evacuation-centers` | Shelters |
| GET | `/satellite/images` | Catalog (DB + mock provider sync) |
| GET | `/satellite/images/{id}` | One scene |
| GET | `/satellite/images/{id}/preview` | PNG bytes from generated raster |
| POST | `/satellite/analyze` | Color-mask “segmentation” on synthetic raster |
| GET | `/satellite/analysis/{id}` | Saved analysis |
| POST | `/satellite/compare` | Before/after rasters |
| GET | `/vision/health` | Demo vs YOLO health dict |
| POST | `/vision/detect` | Upload image, detect |
| POST | `/vision/analyze` | Same pipeline, analyze mode |
| GET | `/vision/jobs/{id}/annotated` | JPEG with boxes |
| POST | `/flood/analyze` | Demo flood mask → GeoJSON + stats |
| GET | `/flood/events` | Saved flood analyses |
| GET | `/flood/events/{id}` | One flood analysis |
| POST | `/damage/analyze` | Before/after change detection JSON |
| GET | `/damage/assessments` | List |
| GET | `/damage/assessments/{id}` | One |
| GET | `/analytics/overview` (and `/disasters`, `/damage`, `/resources`, `/risks`, `/alerts`) | Aggregates; demo KPIs forced when mock providers on |
| GET | `/incidents/{id}` | Combined incident picture |
| POST | `/reports/generate` | JSON report; `pdf_available` is false |
| GET | `/audit-logs` | Recent audits |
| GET | `/exports/{dataset}` | CSV |

### Services (what each module does)

**Weather**

- `MockWeatherProvider` — fixed Kuttanad-like numbers (rain, river, etc.).
- `OpenWeatherProvider` — **code exists**; used only if mock is off **and** a key is set. Calls `api.openweathermap.org`. River level still taken from the mock snapshot. On failure it falls back to mock.
- `get_weather_provider()` — chooses mock vs OpenWeather as above.
- `WeatherIntelService` — current/forecast/history/rainfall/flood/cyclone/weather_alerts.

**Risk (rule-based math)**

- `BaselineFloodRiskModel` — weighted mix of rainfall, intensity, river, history, terrain, soil. Not a neural net.
- `overlay_demo_flood` — when mock providers on, sets probability **82** and HIGH/MEDIUM factors.
- `evaluate_cyclone` — formula on wind, pressure, storm probability, wind trend.
- `analyze_rainfall` — cumulative / intensity / anomaly / short-term risk 0–100.
- `pipeline.py` — thresholds from `alerts/rules.json`; may insert an `Alert` row.

**Satellite**

- `get_satellite_provider()` **always** returns `MockSatelliteProvider` (synthetic scenes, including before/after IDs).
- `SentinelLandsatProvider` class exists but still **delegates to mock**; `get_satellite_provider` does not return it.
- `processing.py` — `generate_demo_raster` paints numpy RGB; `detect_water` etc. are **color thresholds** (OpenCV/NumPy). Not a trained Sentinel model.
- `SatelliteService` — list/analyze/compare, store `ImageAnalysisResult`.

**Vision**

- `DemoVisionModel` — **deterministic fake boxes** from image size hash. Classes include person, fire, damaged_building, etc.
- `YOLOVisionModel` — loads **local** Ultralytics weights if `YOLO_WEIGHTS_PATH` points to a file. Maps a few COCO names. Never downloads. Falls back to demo if ultralytics missing. `ultralytics` is **not** in `backend/requirements.txt`.
- `get_vision_model()` — YOLO file present → YOLO, else demo.
- `VisionPipeline` — validate upload (type/size/magic bytes) → decode → detect → annotate JPEG → save JSON job.
- `severity.py`, `incident.py` — rules that turn labels into severity text and suggested actions.

**Flood**

- `DemoFloodModel` — preprocess + `detect_water`.
- `UNetModel` / `DeepLabModel` — `raise NotImplementedError`.
- `FloodDetectionService.analyze` — synthetic raster → mask → polygons, heatmap, area, population/roads/buildings estimates (`affected_assets` is a formula).

**Damage**

- Compare two generated rasters (`flood_before` vs `flood`).
- `classify_building` / `classify_road` — thresholds on change fractions.
- JSON report via `damage/report.py`. PDF function returns **not implemented**.

**Rescue**

- `RescuePriorityService` — weighted score → LOW/MEDIUM/HIGH/CRITICAL.
- `recommend_resources` — if/then rules (boats if flood+population, helicopter if roads blocked, …).
- `routing.py` — **hard-coded graph** of named nodes; Dijkstra-like `shortest_path`. Not Google Maps.
- `RescuePlanningService` — assemble plan JSON, allocate, `decide()` writes `AuditLog`.

**Alerts**

- `rules.json` — watch/warning/critical cutoffs.
- `AlertEngine` — fuses flood/rain/river/cyclone/damage-like scores.
- `EarlyWarningService` — generate/list/ack/resolve.
- `notifications.py` — dashboard “delivered”; email/SMS/push **mock** or **refused_unwired** even if flags are true (no SMTP/SMS client in code).
- `stream.py` — in-memory queues for SSE.

**Analytics / incident / reports**

- `AnalyticsService.overview` — counts from DB; with mock providers, flooded area / buildings / roads / population use `DEMO_*` constants and `data_class: SIMULATED`.
- `IncidentCommandService.picture` — one JSON blob: incident, weather, zones, flood, roads, buildings, resources, alerts, plan, audit, narrative.
- `ReportService` — JSON; `to_pdf` returns `None`.

**Ops**

- `DisasterService`, `RiskService`, `WeatherService`, `ResourceService`, `EvacuationService` — glue for list/get/explain.

### Libraries actually used on the backend

From `requirements.txt` and imports:

| Library | Where |
| --- | --- |
| FastAPI, uvicorn | HTTP server |
| pydantic, pydantic-settings | schemas + `.env` |
| SQLAlchemy | ORM |
| psycopg2-binary | Postgres driver **if** you use Postgres URL |
| httpx | OpenWeather HTTP; tests |
| numpy, opencv-python-headless | rasters, masks, vision decode/annotate |
| python-multipart | file uploads |
| python-dotenv | settings |
| pytest, ruff | test/lint |

`greenlet` is listed for SQLAlchemy async/greenlet support.

---

## 7. Major features (from current code only)

1. **Command dashboard** — mixes disasters, alerts, resources, weather, analytics KPIs, GIS mock map.
2. **Weather intelligence** — mock weather by default; optional OpenWeather path in code, unused unless configured.
3. **Risk intelligence** — rule-based flood/cyclone + demo overlay 82% for the polder story.
4. **Satellite analysis** — synthetic rasters labeled mock-sentinel2; previews are generated PNGs.
5. **Flood detection** — OpenCV water pixels + GeoJSON, stored in `flood_analyses`.
6. **Damage assessment** — same synthetic rasters, change fractions → building/road class counts.
7. **Computer vision** — upload → DemoVisionModel (or local YOLO if you add weights yourself).
8. **Rescue planning** — rules + demo graph routes + human accept/modify/reject + audit rows.
9. **Alerts** — engine + DB + dashboard; not official warnings; no real SMS/email.
10. **Analytics / exports / incident page** — aggregates and CSV; PDF not generated.
11. **Demo seed** — one main flood incident plus landslide and cyclone **extra** demo rows so lists are not empty.

---

## 8. Mock vs static vs simulated vs rule-based vs not-yet-connected

### Mock (code returns canned or in-memory fake providers)

- `frontend/src/data/mock.ts` when `VITE_USE_MOCK` is not `"false"`.
- `frontend/src/data/gisMock.ts` (maps **always**).
- `MockWeatherProvider`.
- `MockSatelliteProvider` / `get_satellite_provider()`.
- Notification email/SMS/push `mode: "mock"`.
- `intel.ts` summary notes and `fetchMapPoints`.

### Static (fixed files or constants)

- `constants/demo.ts` / `app/core/demo.py` numbers.
- `alerts/rules.json`.
- `data/mock/satellite/kuttanad_demo.txt` (text, not imagery).
- Rescue `routing.py` node graph.
- `ai/` stub return values (34.5 km², moderate damage).

### Simulated / DEMO labeled

- `overlay_demo_flood` → 82% and `SIMULATED DATA · Prototype AI Risk Estimate`.
- Analytics KPIs with `data_class: "SIMULATED"` when mock providers are on.
- Seed titles/messages that say “(demo)” / “not an IMD product”.
- `DemoVisionModel` fake detections.

### Rule-based (formulas / if-then, not trained nets)

- Flood/cyclone/rainfall risk models.
- Rescue recommend + priority scoring.
- Alert severity bands.
- Building/road damage classes from change fractions.
- Vision severity from class lists.
- OpenCV blue-channel water / vegetation / burn / urban masks.

### Not-yet-connected or not implemented (code says so)

- No OpenWeather key required; default path never calls OpenWeather.
- NASA / NOAA: only in **legacy** `src/`, not in `backend` router.
- Google Earth Engine / live Sentinel: `SentinelLandsatProvider` still uses mock; never selected.
- U-Net / DeepLab flood: `NotImplementedError`.
- YOLO: no weights in repo; factory uses demo; `ultralytics` not in requirements.
- Real SMS/email/push: flags exist; **no client is wired**; send is refused or mocked.
- PDF reports: `to_pdf` returns `None`.
- Alembic migrations: README only.
- PostGIS geometry types: not used; JSON GeoJSON instead.
- `ai/` package: not imported by FastAPI.
- `src/` legacy app: not the dashboard backend.
- `OverviewPage` / `RiskPage`: not in the router.

---

## 9. How the `ai/` package relates (so you are not confused)

`ai/inference/runner.py` runs `StubFloodDetector` + `StubDamageClassifier` and returns a dict. Tests call that.

The **website** never calls this. The website’s flood button hits `POST /api/v1/flood/analyze` → `backend/.../flood/service.py`.

Think of `ai/` as a sketch of “where a future model package could live.”

---

## 10. Legacy `src/` (do not mix this up with VisionGuard)

`src/main.py` is another FastAPI titled “Disaster Management System API”. It mounts OpenWeather, NOAA, and NASA routers. Settings mention OpenWeather, NOAA user-agent, and **MySQL** env vars.

The React app’s `apiClient` talks to **`backend`** `/api/v1`, not these routes.

---

## 11. Docker and seed scripts (as written)

- `docker-compose.yml` — services `postgres` (PostGIS image), `backend`, `frontend`. Backend env sets mock providers true. Frontend compose env sets `VITE_USE_MOCK: "true"`.
- `scripts/seed_demo_data.py` / `scripts/seed.py` — add `backend` to `sys.path`, `chdir` there, `init_db()` + `seed_if_empty()`.
- Seed is **skipped** if any `Disaster` row already exists.

---

## 12. Tests (what they cover)

**Backend** (`backend/tests/`): health, disasters, weather/risk, satellite, flood/damage, vision validation, rescue plan decisions, alerts, analytics, end-to-end `test_journey.py`.

**Frontend**: small Vitest files under `src/utils/` plus `KpiCard.test.tsx`. They do not start a browser against every page.

**AI**: `ai/tests/test_stubs.py` checks the stub pipeline dict.

---

## 13. Study order (easiest → hardest)

Read in this order. Do not jump to vision/flood first.

1. `README.md` — what the authors claim the demo is.
2. `frontend/src/constants/demo.ts` — one incident ID, one set of numbers.
3. `frontend/src/main.tsx` then `App.tsx` — how pages are named.
4. `frontend/src/services/apiClient.ts` — mock switch + `fetch`.
5. `frontend/src/data/mock.ts` — what the UI shows with mock on.
6. `frontend/src/pages/DashboardPage.tsx` — how a page pulls many services.
7. `frontend/src/layouts/AppLayout.tsx`, `Sidebar.tsx`, `Header.tsx`.
8. `backend/app/main.py` — startup.
9. `backend/app/core/config.py` and `core/demo.py`.
10. `backend/app/db/session.py`, `init_db.py`, start of `db/seed.py`.
11. `backend/app/models/entities.py` — tables only; skim column names.
12. `backend/app/api/v1/router.py` — match each GET/POST to a page button.
13. `backend/app/services/ops.py` — simplest services.
14. `backend/app/services/weather/factory.py` + `mock_provider.py`.
15. `backend/app/services/risk/flood.py` + `overlay_demo_flood`.
16. `frontend/src/pages/WeatherPage.tsx` and `RiskIntelligencePage.tsx`.
17. `backend/app/services/alerts/` (`rules.json` first, then `engine.py`, `service.py`, `notifications.py`).
18. `frontend/src/pages/AlertsPage.tsx`.
19. `backend/app/services/satellite/mock_provider.py` then `processing.py` then `service.py`.
20. `frontend/src/pages/SatellitePage.tsx`.
21. `backend/app/services/flood/` (`models.py` then `geo.py` then `service.py`).
22. `frontend/src/pages/FloodPage.tsx`.
23. `backend/app/services/damage/` then `DamagePage.tsx`.
24. `backend/app/services/vision/demo_model.py` → `pipeline.py` → `factory.py` (YOLO last).
25. `ComputerVisionPage.tsx`.
26. `backend/app/services/rescue/` (`recommend.py`, `priority.py`, `routing.py`, `service.py`) then `RescuePage.tsx`.
27. `analytics/service.py`, `incident/service.py`, `DisasterDetailPage.tsx`, `AnalyticsPage.tsx`.
28. `frontend/src/components/DisasterMap.tsx` + `data/gisMock.ts` (maps are denser).
29. `backend/app/schemas/common.py` only when you need exact JSON fields.
30. `src/` and `ai/` **last**, and only to see what is **not** on the live dashboard path.

---

## 14. One-sentence memory aid

**The website is a disaster demo console: React pages call `/api/v1`, FastAPI uses SQLite plus mock weather/satellite and OpenCV/demo “AI”, and anything that looks like live Earth observation or government alerting is either mocked, formula-based, or explicitly not implemented.**
