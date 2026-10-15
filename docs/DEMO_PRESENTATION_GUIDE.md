# VisionGuard AI — live demo & presentation guide

Use this while you **show the website**. It matches the current code and `docs/CODEBASE_EXPLANATION.md`. Do not claim live satellites, trained U-Net, or government SMS.

**Before you start (2 minutes)**

1. Backend (from `backend/`):  
   `uvicorn app.main:app --reload --app-dir .`  
   → http://127.0.0.1:8000/docs
2. Frontend (from `frontend/`):  
   `npm run dev`  
   → http://127.0.0.1:5173/dashboard

**Which data path you are on**

- `frontend/.env` `VITE_USE_MOCK` is **not** the word `false` → UI uses `frontend/src/data/mock.ts`. Pages often **do not** call FastAPI. The UI still works. Say: “This is frontend demo mode.”
- `VITE_USE_MOCK=false` **and** backend running → `apiClient.ts` calls `/api/v1/...`. Backend still uses **mock weather** and **mock satellite** by default (`USE_MOCK_PROVIDERS=true`).

The **command map** always uses `frontend/src/data/gisMock.ts` (see `services/gis.ts`). That is true in both modes.

Suggested for a teacher demo: **backend on + `VITE_USE_MOCK=false`**, so you can open `/docs` if asked. If the API is down, the UI may fall back to mock on many screens.

Target time: **8–12 minutes** for the click path below. Keep Computer Vision short unless they ask.

---

## 1. How to start the presentation (say this)

“Good morning. This is **VisionGuard AI**, a **prototype operations console** for disaster management.

We built a full **base system**: a React dashboard, a FastAPI backend, a database of one demo flood in **Kuttanad**, Kerala, maps, risk scores, flood and damage pipelines, rescue planning with human approval, and alerts.

An officer would use this to see weather and risk, inspect imagery, estimate flood and damage, propose a rescue plan, and record alerts — as **decision support**, not as an official warning system.”

Point at the header: **DEMO MODE · simulated data · live APIs optional**.

---

## 2. What to say about “base / prototype” vs live keys later

Say this **once**, then keep repeating the same honesty on each screen:

“The **architecture is complete**: pages, APIs, services, database tables, and plug-in points for providers.

What is **not** connected yet:

- No OpenWeather API key in normal demo (`MockWeatherProvider`).
- No live Sentinel / Google Earth Engine (`get_satellite_provider()` always returns `MockSatelliteProvider`).
- No government SMS/email (notification adapters are mock or refused).
- Flood ‘AI’ is OpenCV color detection, **not** a trained U-Net.
- Computer vision defaults to `DemoVisionModel`, not a disaster-trained YOLO unless we add local weights later.

So today I will demonstrate the **working prototype with simulated and rule-based data**. The same routes can later call real APIs by swapping providers — we did not fake a live feed.”

If they open http://127.0.0.1:8000/docs: “This is the real API contract. The UI is a client of these endpoints.”

---

## 3. Exact demo order (click this sequence)

Stay on **one incident**: Kuttanad flood  
ID `aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa` (sidebar **Incident command**, also `IncidentBar`).

| Step | Sidebar click | Route |
| --- | --- | --- |
| 0 | Open the site | `/dashboard` |
| 1 | **Incident command** | `/disasters/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa` |
| 2 | **Weather** | `/weather` |
| 3 | **Risk Intelligence** | `/risk-intelligence` |
| 4 | **Satellite Analysis** | `/satellite` |
| 5 | (optional 20s) **Satellite Compare** | `/satellite/compare` |
| 6 | **Flood Detection** | `/flood-detection` — click **Run flood analysis** |
| 7 | **Damage Assessment** | `/damage-assessment` — run analysis |
| 8 | **Rescue Planning** | `/rescue-planning` — generate plan, click **Accept** once |
| 9 | **Alerts** | `/alerts` — generate if needed, **Acknowledge** one |
| 10 | **Analytics** | `/analytics` |
| 11 | Stop, or 15s on **Settings** / **Computer Vision** | `/settings` or `/computer-vision` |

Do **not** wander through Live Situation unless you have spare time.

---

## 4. Screen-by-screen: click, say, code, data class

Legend: **MOCK** canned UI/API adapters · **STATIC** files/constants · **SIMULATED** labeled demo KPIs (82%, 34.5 km², …) · **RULE-BASED** formulas / if-then · **HEURISTIC** OpenCV · **REAL** = real HTTP/DB in *this* process, not “live Earth observation.”

---

### Layout (every page)

**Show:** Header “VISIONGUARD AI”, DEMO MODE, **Incident bar** (Kuttanad title + ID).

**Say:** “Every page shares this shell. The bar pins one demo incident so weather, risk, flood, and rescue stay on the same flood.”

| | |
| --- | --- |
| Frontend | `AppLayout.tsx` wraps routes. `Header.tsx`, `Sidebar.tsx`, `IncidentBar.tsx`. `App.tsx` maps URLs to pages. |
| API | Layout also `fetchAlerts` for the header badge → `GET /api/v1/alerts` (or `mock.ts` in UI mock mode). |
| Backend | `EarlyWarningService.list` |
| Data | Seeded + generated **prototype** alerts; UI mock if `isMockMode()`. |
| Class | **SIMULATED** incident IDs (`constants/demo.ts` = `core/demo.py`). |

---

### 0) Dashboard `/dashboard`

**Click:** Leave it open. Toggle a map layer if you want. Click a polygon → right panel.

**Say:** “This is the command dashboard. Active flood, population at risk **42,000**, flooded **34.5 km²**, damaged buildings **18** — those headline numbers are our **canonical simulated** Kuttanad scenario. The map is Leaflet with demo GeoJSON layers: flood, risk, roads, boats. The disclaimer says this does not replace official decisions.”

| | |
| --- | --- |
| Frontend | `DashboardPage.tsx` + `useAsync`: `fetchDisasters`, `fetchAlerts`, `fetchResources`, `fetchWeatherCurrent`, `fetchAnalytics`, `fetchGisCatalog`. `DisasterMap`, `KpiCard`, `SafetyBanner`, `AlertPanel`, `DashboardCharts`. Population/flood/buildings KPIs use `DEMO_STATS` in the page. |
| API (mock off) | `GET /api/v1/disasters`, `/alerts`, `/resources`, `/weather/current`, `/analytics/overview` |
| Backend | `DisasterService`, `EarlyWarningService`, resource list, `WeatherIntelService` / `WeatherService`, `AnalyticsService` |
| Map data | **Always** `gisMock.ts` via `gis.ts` (even if API is live). |
| Class | KPIs **SIMULATED**. Map **STATIC** GeoJSON. Weather **MOCK** provider. Disasters/alerts **REAL DB rows** of demo seed if API is on. Basemap tiles = public Carto map, **not** live disaster satellite. |

**Code link:** Page → `services/disasters.ts` etc. → `apiClient.ts` → `router.py`. Map → `DisasterMap.tsx` ← `gisMock.ts`.

---

### 1) Incident command `/disasters/:id`

**Click:** Sidebar **Incident command**.

**Say:** “This is one JSON ‘picture’ of the same incident: narrative steps, people at risk, links into flood and rescue. The ID in the URL is the same UUID as seed and `demo.ts`.”

| | |
| --- | --- |
| Frontend | `DisasterDetailPage.tsx` → `fetchIncidentPicture` (`services/incident.ts`) |
| API | `GET /api/v1/incidents/{id}` |
| Backend | `IncidentCommandService.picture` |
| Data | Database + `DEMO_NARRATIVE` in `core/demo.py` |
| Class | **SIMULATED** story; **REAL** SQLite/Postgres rows of demo data |

---

### 2) Weather `/weather`

**Click:** Weather. Point at temp, rain, humidity, wind, river, forecast chart, **Flood probability**.

**Say:** “Weather intelligence. Default backend is `MockWeatherProvider` — fixed demo observations for Kuttanad, not OpenWeather, unless we add a key and turn mock providers off. Flood probability here is our prototype estimator; in demo it is overlaid to **82%** and labeled simulated.”

| | |
| --- | --- |
| Frontend | `WeatherPage.tsx` → `services/weather.ts` (`fetchWeatherCurrent`, forecast, history, rainfall, flood/cyclone risk) |
| API | `GET /api/v1/weather/current`, `/forecast`, `/history`, `/rainfall`, `/risk/flood`, `/risk/cyclone` |
| Backend | `WeatherIntelService`; `get_weather_provider()`; `BaselineFloodRiskModel` + `overlay_demo_flood`; `evaluate_cyclone`; `analyze_rainfall` |
| Data | Mock provider numbers (e.g. ~27°C, ~48 mm rain in the mock). Overlay **82%**. |
| Class | Weather **MOCK**. Risk math **RULE-BASED**. 82% **SIMULATED**. OpenWeather **not used** in the default demo. |

---

### 3) Risk Intelligence `/risk-intelligence`

**Click:** **Polder A** button. Point at score, factors (Rainfall HIGH, River HIGH, …).

**Say:** “Risk zones from the database, then a service **explains** the score with contributing factors. This is transparent weighted logic, not a hidden neural net. Polder A is aligned to the 82% simulated flood story.”

| | |
| --- | --- |
| Frontend | `RiskIntelligencePage.tsx` → `fetchRiskZones`; map still `DisasterMap` + **gisMock** |
| API | `GET /api/v1/risk-zones` |
| Backend | `RiskService.list` + `explain` (`ops.py`) |
| Data | `risk_zones` table + weather + overlay for Polder A |
| Class | Factors **RULE-BASED** / **SIMULATED** overlay. Map polygons **STATIC** gisMock (may not be the same geometry as the DB polygon). |

---

### 4) Satellite `/satellite`

**Click:** Open the page. Show a scene. Run **analyze** if the button is there.

**Say:** “Satellite module: catalog, preview, analysis. The provider in code is always `MockSatelliteProvider`. Previews are **generated PNG rasters**, not a downloaded Sentinel granule. Analysis uses OpenCV color masks, labeled prototype, not a trained Earth-observation model.”

| | |
| --- | --- |
| Frontend | `SatellitePage.tsx` → `services/satellite.ts` |
| API | `GET /api/v1/satellite/images`; `GET .../preview`; `POST /api/v1/satellite/analyze` |
| Backend | `SatelliteService`; `processing.generate_demo_raster`, `detect_water`, etc. |
| Data | Synthetic RGB + mock catalog (plus any seed image row) |
| Class | **MOCK** / **HEURISTIC** / **SIMULATED** stand-in for Sentinel |

**Satellite Compare (optional):** `POST /api/v1/satellite/compare` — two fake rasters, change fractions. Same honesty.

---

### 5) Flood Detection `/flood-detection`

**Click:** **Run flood analysis**. Wait. Show flooded km², map overlay, notes text.

**Say:** “This is the flood pipeline: synthetic image → water mask → polygons → area. The note on screen says it is **not** a trained U-Net. U-Net and DeepLab classes in code raise NotImplementedError. The number here can differ from the dashboard 34.5 km² — that 34.5 is the **canonical simulated KPI**; this button shows the OpenCV run.”

| | |
| --- | --- |
| Frontend | `FloodPage.tsx` → `analyzeFlood` / `fetchFloodEvents`; `SatelliteOverlayMap` |
| API | `POST /api/v1/flood/analyze`; `GET /api/v1/flood/events` |
| Backend | `FloodDetectionService` + `DemoFloodModel` + `flood/geo.py` → table `flood_analyses` |
| Data | `generate_demo_raster` then OpenCV |
| Class | **HEURISTIC**. Canonical 34.5 km² elsewhere is **SIMULATED**. |

---

### 6) Damage Assessment `/damage-assessment`

**Click:** Run analysis. Show building doughnut and road classes. Mention PDF is not generated.

**Say:** “Before/after change detection on two demo rasters, then rules that label buildings and roads. JSON report only — PDF is not implemented.”

| | |
| --- | --- |
| Frontend | `DamagePage.tsx` → `services/damage.ts` |
| API | `POST /api/v1/damage/analyze`; `GET /damage/assessments` |
| Backend | `DamageAssessmentService`, `compare_scenes`, `classify_building` / `classify_road` → `damage_reports` |
| Class | **HEURISTIC** + **RULE-BASED**. Dashboard “18 buildings” is **SIMULATED** KPI, not necessarily this run’s counts. |

---

### 7) Rescue Planning `/rescue-planning`

**Click:** Generate plan. Point at boats, medical, allocation, route. Click **Accept** once. Say audit is stored.

**Say:** “Decision support: if flood is high and population is large, recommend boats; if roads blocked, helicopter, and so on. Routing is a **small demo graph**, not Google Maps. The officer must Accept, Modify, or Reject — the system does not dispatch units by itself.”

| | |
| --- | --- |
| Frontend | `RescuePage.tsx` → `services/rescue.ts` |
| API | `GET /api/v1/rescue/priorities`; `POST /rescue/plan`; `POST /rescue/plans/{id}/decision` |
| Backend | `RescuePlanningService`, `RescuePriorityService`, `recommend_resources`, `routing.shortest_path`; `AuditLog` |
| Data | Seeded resources + rules |
| Class | **RULE-BASED** / **SIMULATED** inventory. **REAL** DB write for the plan and audit. |

Do **not** say computer vision automatically filled this plan. That link is **not** in the code.

---

### 8) Alerts `/alerts`

**Click:** List. **Generate** if you want a fresh one. **Acknowledge** one row. Read the message: not IMD/NDMA.

**Say:** “Early-warning **engine**: scores versus `rules.json` thresholds, then a dashboard alert. Email and SMS adapters only log mock or refuse — nothing is sent to phones.”

| | |
| --- | --- |
| Frontend | `AlertsPage.tsx` → `services/alerts.ts`; SSE only if not UI mock (`useAlertStream`) |
| API | `GET /api/v1/alerts`; `POST /alerts/generate`; `POST /alerts/{id}/acknowledge` |
| Backend | `EarlyWarningService`, `AlertEngine`, `notifications.py` |
| Class | **RULE-BASED** prototype alerts. Notifications **MOCK**. |

---

### 9) Analytics `/analytics`

**Click:** Show KPIs 34.5 / 18 / 3 / 82% and charts.

**Say:** “Analytics aggregates the demo incident. With mock providers on, key KPIs are forced to the simulated Kuttanad figures so the story stays consistent.”

| | |
| --- | --- |
| Frontend | `AnalyticsPage.tsx` → `fetchAnalytics` |
| API | `GET /api/v1/analytics/overview` |
| Backend | `AnalyticsService.overview` (`data_class: SIMULATED` when mock providers on) |
| Class | **SIMULATED** KPIs |

---

### Optional: Computer Vision `/computer-vision` (30–45 seconds)

**Click:** Upload any small JPEG/PNG. Run analysis. Point at model name `demo-vision-v0`.

**Say:** “Upload goes through validation, then `DemoVisionModel` draws **deterministic demo boxes** from image size — it is not a trained disaster detector. YOLO is only if we later put a **local** weights file on disk; the project does not download weights.”

| | |
| --- | --- |
| Frontend | `ComputerVisionPage.tsx` → `analyzeVision` (`apiUpload`) |
| API | `POST /api/v1/vision/analyze`; `GET /vision/jobs/{id}/annotated` |
| Backend | `VisionPipeline`, `get_vision_model()` → `DemoVisionModel` |
| Class | **MOCK** detections. YOLO **not in the default demo**. |

---

### Optional: Settings `/settings`

**Show:** Same incident ID, CSV links (`/api/v1/exports/...`). Do not dwell on JSON report buttons.

---

### Skip or 10 seconds only

| Screen | Why not spend time |
| --- | --- |
| Live Situation `/situation` | Table + `fetchMapPoints` is **always** `mockMapPoints` (`intel.ts`). Weak story. |
| OverviewPage / RiskPage files | **Not in the router.** Don’t open them. |
| `/docs` U-Net | Don’t click a U-Net path — it is **NotImplementedError**. |
| `src/` NASA/NOAA | Different app; not this UI. |
| `ai/` folder | FastAPI does **not** import it. |

---

## 5. Screen ↔ code (one picture to remember)

```
I click a sidebar link
  → App.tsx route
  → pages/SomethingPage.tsx
  → services/*.ts  (mock.ts OR fetch)
  → GET/POST http://127.0.0.1:8000/api/v1/...
  → backend/app/api/v1/router.py
  → a Service (WeatherIntel, FloodDetection, RescuePlanning, …)
  → mock provider / OpenCV / rules / SQLAlchemy
  → JSON back into KpiCard / Leaflet / Chart.js
```

If they ask “where is the 82%?”: `backend/app/services/risk/flood.py` function `overlay_demo_flood`, constants in `app/core/demo.py` and `frontend/src/constants/demo.ts`.

If they ask “where is the map?”: `DisasterMap.tsx` + `data/gisMock.ts` — **not** PostGIS.

---

## 6. Best features vs don’t overstay

**Best (show these well)**

1. Dashboard + DEMO MODE + SafetyBanner  
2. Same incident ID everywhere  
3. Weather + 82% with factors (honesty about mock + rules)  
4. Flood **Run** (visible pipeline, read the “not U-Net” note)  
5. Rescue **Accept** (human in the loop + audit)  
6. Alerts **not official** + no SMS  

**Good if time:** satellite analyze, damage doughnuts, analytics KPIs.

**Short or skip:** Live Situation, Settings exports, Computer Vision (unless they ask about YOLO), Satellite Compare, opening `src/`.

---

## 7. Limitations now / what later (simple)

**Now**

- Prototype UI + APIs + SQLite seed.  
- Mock weather, mock satellite, demo CV, OpenCV flood/damage, rule-based risk/rescue/alerts.  
- Command GIS is static `gisMock`, not live DB geometry.  
- No login. No PDF. No trained U-Net. No GEE. No real SMS.

**Later (the code already has empty sockets)**

- Set `OPENWEATHER_API_KEY` and `USE_MOCK_PROVIDERS=false` → `OpenWeatherProvider` (river level still partly mock in that file).  
- Put **local** YOLO weights in `YOLO_WEIGHTS_PATH` (never auto-download).  
- Replace `DemoFloodModel` with real weights; U-Net class exists only as a stub.  
- Point `SentinelLandsatProvider` at real GEE (today it still delegates to mock; factory always returns mock).  
- Wire SMTP/SMS only after a real client exists (`notifications.py` currently refuses).  
- PostGIS types, Alembic, auth — documented as not implemented.

---

## 8. Ending statement (future scope)

“This project delivers a **working base** of a disaster command system: end-to-end screens, APIs, a seeded incident, and replaceable services.

What you saw today is **simulated and rule-based decision support**. The next phase is to plug in **real weather keys**, **real satellite access**, and **trained models** behind the same interfaces — without changing the operator workflow we just demonstrated.

VisionGuard AI is a **prototype**. It does not replace authorized emergency-management decisions.”

Stop. Thank the teacher. Offer `/docs` or the GitHub docs folder if they want to inspect routes.
