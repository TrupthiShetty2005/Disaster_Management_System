# LIVE API / REAL DATA / WORKFLOW AUDIT

**Audit date:** 2026-10-04 (baseline) · **Updated:** 2026-10-05 after live-architecture hardening  
**Method:** Code-level inspection + runtime probes. Secrets never printed.  
**Companion doc:** [LIVE-DATA-ARCHITECTURE.md](./LIVE-DATA-ARCHITECTURE.md)

**Primary runtime:** `backend/app` + `frontend/`. Legacy `src/` and `ai/` stubs remain unwired.

---

## BEFORE → AFTER (2026-10-05)

| Module | Before | After | Evidence |
| --- | --- | --- | --- |
| Weather | LIVE | **LIVE** (kept) | OpenWeather probe via `/data-sources/status` |
| NASA history | LIVE | **LIVE** (kept) | NASA POWER probe |
| Sentinel / Copernicus | LIVE | **LIVE** (kept) | STAC + thumbnails |
| Flood analysis | DERIVED (poorly labeled) | **DERIVED_LIVE** + UI “REAL SENTINEL — HEURISTIC” | `provenance.py`, FloodPage |
| Damage | DERIVED | **DERIVED_LIVE** (labeled) | provenance module |
| GIS | MOCK always (silent) | **STATIC_EXTERNAL** via Overpass when LIVE; map catalog still demo-labeled; Overpass failure → 503 (no fake polygons) | `gis/overpass.py`, SituationPage |
| IMD | NOT_CONFIGURED | **NOT_CONFIGURED** (honest; no fake warnings) | provenance |
| River level | Fake 0.0 | **UNAVAILABLE** (`river_level_available=false`) | `live_provider.py`, WeatherCurrentOut |
| Resources / incidents | Seed (unlabeled) | **SEEDED** (labeled in UI panel) | provenance + SafetyBanner panel |
| Analytics | Mixed/seed | **DERIVED_LIVE** + per-KPI provenance notes | `analytics/service.py` |
| Vision | Demo / fail | **NOT_CONFIGURED** without weights (LIVE); MOCK in Demo | provenance |
| Notifications | Mock | **MOCK** (still unwired — correctly labeled) | notifications.py |
| Provenance API | Partial `/data-sources` | **`/data-sources/status`** module matrix | `provenance.py` |
| Docker LIVE | Demo defaults only | **`docker-compose.live.yml` + `.env.live.example`** | compose overlay |
| UI transparency | Global DEMO/REAL only | **Per-module badges + Why this data?** | `DataModeBadge.tsx` |

Verified runtime (local LIVE, 2026-10-05): `weather=LIVE`, `weather_history=LIVE`, `satellite=LIVE`, `gis features=80 STATIC_EXTERNAL`, `imd=NOT_CONFIGURED`, `flood_analysis=DERIVED_LIVE`, `river_level=UNAVAILABLE`.

---

## 1. Executive Summary

VisionGuard AI is a **decision-support prototype** for a Kuttanad (Alappuzha, Kerala) demo AOI. With `USE_MOCK_PROVIDERS=false` and keys present, it **does** call:

| Live integration | Used today? |
| --- | --- |
| OpenWeatherMap current + forecast | **YES** (key required) |
| NASA POWER daily history | **YES** (no key) |
| Copernicus CDSE STAC catalogue + Sentinel preview thumbnails | **YES** (OAuth optional; public STAC search works) |
| Esri public map tiles (browser) | **YES** (basemap only) |

Everything else that looks like a product feature is mostly **seeded SQLite/Postgres rows**, **rule-based scores**, **OpenCV heuristics on Sentinel *previews***, or **explicit Demo Mode mocks**.

There is **no authentication**, **no background workers/cron**, **no Redis/queue**, **no real SMS/email/push delivery**, **no trained flood U-Net**, and **no official IMD warnings** unless `IMD_API_KEY` is set (currently not).

**Local env observed during audit** (`backend/.env` + `frontend/.env`, values redacted):

| Flag / secret | Configured? |
| --- | --- |
| `USE_MOCK_PROVIDERS` | `false` (REAL DATA path) |
| `OPENWEATHER_API_KEY` | **YES** |
| `IMD_API_KEY` | **NO** |
| `COPERNICUS_CLIENT_ID` / `SECRET` | **NO** |
| `YOLO_WEIGHTS_PATH` | **NO** |
| `ENABLE_REAL_EMAIL/SMS/PUSH` | **false** |
| `VITE_USE_MOCK` | `false` |
| `DATABASE_URL` | SQLite file `visionguard.db` |

Docker Compose **defaults to Demo Mode** (`USE_MOCK_PROVIDERS=true`, `VITE_USE_MOCK=true`) — different from local `.env` defaults in `.env.example`.

---

## 2. Project Architecture (from code)

```
                         ┌──────────── USER ────────────┐
                         └──────────────┬───────────────┘
                                        ↓
                         ┌──────────────────────────────┐
                         │ frontend/ (Vite React SPA)   │
                         │ App.tsx routes → pages       │
                         │ apiClient fetch → /api/v1/*  │
                         │ Esri tile URLs (basemap)     │
                         │ gisMock.ts ALWAYS for GIS    │
                         └──────────────┬───────────────┘
                                        ↓ HTTP
                         ┌──────────────────────────────┐
                         │ backend/app/main.py FastAPI  │
                         │ CORS only (NO AUTH)          │
                         │ lifespan: init_db+seed       │
                         │ /api/v1 ← router.py          │
                         └──────────────┬───────────────┘
                ┌───────────────────────┼───────────────────────┐
                ↓                       ↓                       ↓
        SQLAlchemy DB            Weather factory          Satellite factory
     (SQLite/Postgres)         mock | LiveWeather       mock | Copernicus
        seed.py                    ↓                       ↓
     disasters,zones,         OpenWeather httpx       STAC search httpx
     resources,alerts…        NASA POWER httpx        Thumbnail httpx
                              IMD httpx (opt)         optional OAuth
                ↓                       ↓                       ↓
        Analytics/Rescue/         Risk rules             Flood/Damage
        Incident (mostly          (rule-based)           OpenCV change
        seeded + some live)                              heuristics
                ↓
        JSON responses → frontend pages
```

**Not in the running VisionGuard process:**

| Path | Role | Wired to `backend/app/main.py`? |
| --- | --- | --- |
| `src/main.py` | Legacy FastAPI: `/openweather`, `/noaa`, `/nasa` | **NO** |
| `ai/` | Stub flood/damage/vision helpers | **NO** |
| Redis / Celery / cron | — | **Absent** |
| Alembic migrations | `db/migrations/README.md` only | **create_all + sqlite ALTER** in `init_db.py` |

---

## 3. Complete Product Workflow (user perspective)

### Mode switch (controls almost everything)

| Layer | Flag | Effect |
| --- | --- | --- |
| Backend | `USE_MOCK_PROVIDERS` (`app/core/config.py`) | `true` → `MockWeatherProvider` + synthetic satellite rasters + demo KPIs. `false` → live providers; failures raise `ProviderUnavailableError` → HTTP **503** (`app/core/errors.py`). |
| Frontend | `VITE_USE_MOCK` (`frontend/src/services/apiClient.ts` `isMockMode()`) | `true` → returns `frontend/src/data/mock.ts` without calling API. `false` → `fetch` backend. |

### Startup

1. Uvicorn loads `app.main:app`.
2. `lifespan` → `init_db()` (`create_all` + light SQLite column patches) → `seed_if_empty()` if no `Disaster` rows (`app/db/seed.py`).
3. Frontend Vite serves SPA; pages call `/api/v1/...` when not in mock mode.

### Major workflows that **exist in code**

#### W1 — Weather & risk (REAL path)

```
User → /weather
  → fetchWeatherCurrent/Forecast/History/Rainfall/FloodRisk/Cyclone
  → GET /api/v1/weather/* | /risk/*
  → WeatherService / WeatherIntelService
  → get_weather_provider() → LiveWeatherProvider
       → OpenWeatherProvider.current_live / forecast_live  (httpx)
       → NasaPowerClient.history_for_demo_aoi             (httpx)
       → ImdClient.district_warnings (only if IMD_API_KEY)
  → BaselineFloodRiskModel / cyclone rules (local math)
  → JSON → WeatherPage KPIs/charts
```

Evidence: `backend/app/services/weather/factory.py`, `live_provider.py`, `openweather_provider.py`, `nasa_power.py`, `weather_intel.py`, `frontend/src/pages/WeatherPage.tsx`.

#### W2 — Satellite catalogue + preview

```
User → /satellite
  → GET /api/v1/satellite/images
  → SatelliteService.list_images → sync_catalog
  → CopernicusStacProvider.refresh (STAC POST /search)
  → upsert SatelliteImage rows
  → GET .../preview → fetch_thumbnail_bytes → CDSE/Creodias asset URL
```

Evidence: `satellite/service.py`, `copernicus_provider.py`.

#### W3 — Flood before/after change (REAL path)

```
User → /flood-detection → Run analysis
  → POST /api/v1/flood/analyze
  → FloodDetectionService._analyze_real_change
  → list Sentinel-2 scenes (STAC) → download 2 thumbnails
  → compare_water_change (OpenCV/NumPy) → newly = after & ~before
  → persist FloodAnalysis (+ visionguard_change payload in boundary_geojson)
  → FloodEventOut with change KPIs → map overlays + before/after imgs
```

Evidence: `flood/service.py`, `satellite/processing.py` `compare_water_change`, `FloodPage.tsx`.

#### W4 — Satellite compare

Same detectors via `POST /api/v1/satellite/compare` → `SatelliteService.compare` → `compare_scenes(..., use_sentinel_heuristic=live)`.

#### W5 — Damage assessment

```
POST /api/v1/damage/analyze
  → DamageAssessmentService
  → REAL: two Sentinel thumbnails + compare_scenes
  → DEMO: generate_demo_raster pair
  → heuristic building/road class counts → DamageReport JSON
```

Evidence: `damage/service.py`.

#### W6 — Alerts

```
POST /api/v1/alerts/generate
  → EarlyWarningService / AlertEngine.gather_signals
  → pulls WeatherIntel flood/cyclone (live weather when REAL)
  → rule thresholds (alerts/rules.json)
  → insert Alert rows + in-process pub/sub
  → notifications.dispatch → dashboard “delivered”; email/SMS/push mock/refused
SSE: GET /api/v1/alerts/stream (in-memory queue, not Redis)
```

Evidence: `alerts/engine.py`, `notifications.py`, `stream.py`, `useAlertStream.ts`.

#### W7 — Computer vision upload

```
User uploads image → POST /api/v1/vision/analyze
  → VisionPipeline → get_vision_model()
  → YOLO if YOLO_WEIGHTS_PATH file exists
  → else DemoVisionModel ONLY when USE_MOCK_PROVIDERS=true
  → else ProviderUnavailableError (REAL mode without weights)
  → local disk annotated JPEG under VISION_STORAGE_DIR
```

Evidence: `vision/factory.py`, `pipeline.py`, `yolo_model.py`.

#### W8 — Dashboard / analytics / incident / rescue / GIS

- **Analytics:** mixes DB seed inventory + latest `FloodAnalysis` + live flood risk when REAL (`analytics/service.py`).
- **Disasters / resources / centers / risk zones:** SQLAlchemy queries of **seeded** tables (`seed.py`).
- **Rescue plan:** scoring/recommend heuristics on seed resources (`rescue/service.py`).
- **GIS layers:** `frontend/src/services/gis.ts` **always** returns `gisMock` — even when `VITE_USE_MOCK=false`.
- **Reports:** JSON payload generator; `pdf_available=False` (`reports/service.py`, router).

#### W9 — Auth / registration / payments / webhooks

**Do not exist** in `backend/app` or `frontend` routes.

---

## 4. All External APIs / Integrations

### Live API matrix (VisionGuard `backend/app`)

| API / Service | Purpose | Provider | Endpoint/SDK | Called from | Classification | Credentials configured? (local) | Actually executed when REAL? | Data type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OpenWeather current | Temp/humidity/wind/rain/conditions | OpenWeatherMap | `api.openweathermap.org/data/2.5/weather` | `openweather_provider.py` ← `LiveWeatherProvider` | **A LIVE** (if key) | YES | YES | Real observations for `OPENWEATHER_QUERY` |
| OpenWeather forecast | 3h forecast slices | OpenWeatherMap | `/data/2.5/forecast` | same | **A LIVE** | YES | YES | Real forecast |
| NASA POWER | Daily history / rainfall anomaly | NASA | `power.larc.nasa.gov/.../daily/point` | `nasa_power.py` | **A LIVE** | N/A (no key) | YES if `NASA_POWER_ENABLED` | Real reanalysis/meteo |
| Copernicus STAC search | Sentinel-1/2 catalogue | CDSE | `POST {COPERNICUS_STAC_URL}/search` | `copernicus_provider.py` | **A LIVE** | OAuth NO (optional) | YES | Real catalogue metadata |
| Copernicus / Creodias thumbnail | Preview JPEG bytes | CDSE asset href | `httpx.get(thumbnail_href)` | `fetch_thumbnail_bytes` | **A LIVE** | Often public redirect | YES when scenes have thumbnails | Real preview imagery |
| Copernicus OAuth | Token for protected assets | CDSE identity | `COPERNICUS_TOKEN_URL` | `_oauth_token` | **B CONFIGURED BUT NOT USED** locally (no client id/secret) | NO | Only if credentials set | — |
| IMD district warnings | Official alerts | api.imd.gov.in | Bearer JWT | `imd_client.py` ← `LiveWeatherProvider.alerts` | **C IMPLEMENTED BUT DISABLED** without key | NO | NO (empty list / unavailable status) | Would be real if key |
| Esri World Dark Gray / Imagery tiles | Map basemap | ArcGIS Online | tile URLs in browser | `frontend/src/maps/basemap.ts` | **A LIVE** (public tiles) | NO key | YES (browser) | Basemap only — **not** disaster EO product |
| SMTP email | Alert email | — | **Not implemented** | `notifications.py` | **D MOCKED** / refused_unwired | NO | NO | Fake log |
| SMS | Alert SMS | — | **Not implemented** | `notifications.py` | **D MOCKED** / refused_unwired | NO | NO | Fake log |
| Mobile push | FCM/APNs | — | **Not implemented** | `notifications.py` | **D MOCKED** / refused_unwired | NO | NO | Fake log |
| Ultralytics YOLO | CV detections | Local weights file | `ultralytics.YOLO` | `yolo_model.py` | Local model (**not** cloud API); **disabled** without path | NO | NO → DemoVision only in Demo Mode | User image + model |
| LLM / OpenAI / etc. | — | — | — | — | **Absent** | — | — | — |
| Redis / S3 / Stripe / KYC / GST | — | — | — | — | **Absent** | — | — | — |

### Legacy `src/` app (separate process)

| API | File | Mounted in VisionGuard? |
| --- | --- | --- |
| OpenWeather (`requests`) | `src/app/services/openweather_services.py` | **NO** |
| NOAA (`requests`) | `src/app/services/noaa_services.py` | **NO** |
| NASA POWER (`requests`) | `src/app/services/nasa_services.py` | **NO** |

These are **parallel/legacy** (`src/main.py`). They do **not** participate in the React SPA’s `/api/v1` workflow unless someone runs `src/main.py` separately.

### `ai/` package

Stub detectors (`ai/services/flood.py`, `damage.py`, `vision.py`, `inference/runner.py`). **No import path from `backend/app`.** Classification: **implemented stubs / unused**.

---

## 5. Real-World Data Matrix (by functionality)

| Functionality | Data source | Real-world data? | Live/Batch/Static | Refresh | Origin / evidence |
| --- | --- | --- | --- | --- | --- |
| Weather current/forecast UI | OpenWeather | **YES** (REAL mode + key) | Live per request | On page load | `openweather_provider.py` |
| Weather history / rainfall anomaly | NASA POWER | **YES** | Live per request | On page load | `nasa_power.py` (`demo_latitude/longitude`) |
| Flood/cyclone **risk %** | Rule engine on live weather + history | **Derived** (not official warning) | Live compute | Per request | `risk/flood.py`, `weather_intel.py` |
| IMD official alerts | IMD API | **NO** today | Disabled | — | `imd_client.py` needs key |
| Sentinel catalogue titles/dates/cloud | Copernicus STAC | **YES** | Live search (+ DB upsert) | On list/sync | `copernicus_provider.py` |
| Sentinel preview pixels | Thumbnail download | **YES** (preview, not full SAFE) | Live fetch | On preview/analyze | `fetch_thumbnail_bytes` |
| Flood **newly water-covered** km² | OpenCV on 2 previews | **Derived from real previews** | Live compute | On analyze | `flood/service.py` — **not** validated flood product |
| Damage assessment classes | Heuristic change on previews | **Derived** | Live compute | On analyze | `damage/service.py` |
| Map basemap | Esri tiles | YES (cartographic) | Live tiles | Pan/zoom | `basemap.ts` |
| Disaster incidents table | SQLite/PG | **NO** (seeded demo) | Seeded | App start if empty | `seed.py` |
| Risk zones inventory | DB | **NO** (seed) | Seeded | Start | `seed.py` |
| Rescue resources / centers | DB | **NO** (seed) | Seeded | Start | `seed.py` |
| GIS situation layers | `gisMock.ts` | **NO** | Static FE | Never | `gis.ts` always returns mock |
| Dashboard DEMO KPI strip | `constants/demo.ts` | **NO** | Static | — | Shown only when Demo Mode UI |
| Analytics population/buildings | Seed + optional live flood row | **Mixed** | Seed + live flood analysis | Request | `analytics/service.py` |
| Vision detections | User upload + DemoVision/YOLO | User image **YES**; labels **demo/YOLO-COCO** | Per upload | — | `vision/*` |
| Alert records | Engine + seed alerts | Signals may use live weather; rows are app-generated | On generate | — | `alerts/engine.py` |
| Email/SMS/push | Logs | **NO** | Mock | — | `notifications.py` |
| U-Net/DeepLab flood | Placeholders raise `NotImplementedError` | **NO** | — | — | `flood/models.py` |

---

## 6. Data Lineage (important live paths)

### OpenWeather → UI

```
OpenWeather API (Alappuzha,IN)
  → httpx in OpenWeatherProvider.current_live / forecast_live
  → WeatherSnapshot / ForecastPeriod pydantic models
  → WeatherIntelService / WeatherService
  → GET /api/v1/weather/current|forecast
  → frontend weather.ts → WeatherPage
```

**Stops being “official product data” at:** rule-based flood/cyclone scores (local formulas). River level forced to `0.0` in `LiveWeatherProvider.current`.

### NASA POWER → rainfall anomaly

```
NASA POWER point API (lat=9.517, lon=76.522)
  → NasaPowerClient.fetch_daily
  → HistoryPoint list
  → rainfall analysis in weather_intel
  → GET /api/v1/weather/history|rainfall
  → WeatherPage chart
```

### Copernicus → flood change KPI

```
CDSE STAC search (bbox around demo AOI, lookback days)
  → SatelliteScene metadata (+ DB SatelliteImage)
  → thumbnail_href GET (Creodias zipper redirect common)
  → OpenCV decode RGB preview
  → detect_water_sentinel_rgb × 2 dates
  → newly = after & ~before
  → area ≈ AOI km² × pixel fraction
  → FloodAnalysis row (SQLite/PG)
  → FloodEventOut → FloodPage map/KPIs
```

**Stops being scientifically validated flood mapping at:** RGB preview heuristic + AOI approximation (explicitly labeled in `notes` / `estimate_label`).

### Seeded incident data

```
seed.py (hardcoded demo Locations/Disasters/Resources/…)
  → SQLAlchemy insert once
  → /disasters /resources /evacuation-centers /risk-zones /incidents
  → Situation/Dashboard/Rescue UI
```

**Never live.** Refresh = wipe DB or reseed.

---

## 7. API Endpoint Workflow Notes

**Auth on all `/api/v1/*`:** none (no Depends auth, no JWT, no API keys on requests).

Representative endpoints:

| Method | Path | External? | DB | Notes |
| --- | --- | --- | --- | --- |
| GET | `/health` | No | No | Reports `data_mode` |
| GET | `/data-sources` | Probes NASA/IMD/Copernicus when REAL | No | Status JSON |
| GET | `/weather/current` | OpenWeather | No (pass-through) | 503 if key missing (REAL) |
| GET | `/weather/history` | NASA POWER | No | |
| GET | `/risk/flood` | OpenWeather+NASA then rules | No | Not IMD |
| GET | `/satellite/images` | STAC sync | Yes upsert | |
| GET | `/satellite/images/{id}/preview` | Thumbnail | Yes | |
| POST | `/satellite/compare` | Thumbnails | Yes analysis row | Change indication |
| POST | `/flood/analyze` | 2× thumbnails | Yes `flood_analyses` | Change KPIs |
| POST | `/damage/analyze` | 2× thumbnails (REAL) | Yes | |
| POST | `/vision/analyze` | No cloud; local model | Yes job + files | |
| GET | `/disasters` | No | Seed | |
| POST | `/alerts/generate` | Via weather intel | Yes alerts | Notifications mock |
| GET | `/alerts/stream` | No | In-memory SSE | Multi-worker unsafe |
| GET | `/analytics/overview` | Optional live risk | Seed + flood rows | Mixed |
| POST | `/reports/generate` | No | Read seed/live mix | No PDF |

Full route list: `backend/app/api/v1/router.py`.

---

## 8. Mock / Static / Seeded Inventory

| Mechanism | Location | When used |
| --- | --- | --- |
| `MockWeatherProvider` | `weather/mock_provider.py` | `USE_MOCK_PROVIDERS=true` |
| `generate_demo_raster` | `satellite/processing.py` | Demo Mode rasters; flood/damage demo path |
| `MockSatelliteProvider` | `satellite/mock_provider.py` | Demo Mode catalogue |
| `DemoVisionModel` | `vision/demo_model.py` | Demo Mode / missing YOLO |
| `overlay_demo_flood` → 82% | `risk/flood.py` | Demo Mode only (`use_mock_providers` guard) |
| `DEMO_*` constants | `core/demo.py`, FE `constants/demo.ts` | Demo KPIs / incident IDs |
| `seed.py` | DB bootstrap | Empty DB |
| `frontend/src/data/mock.ts` | FE adapters | `VITE_USE_MOCK=true` |
| `frontend/src/data/gisMock.ts` | GIS | **Always** (even REAL FE) |
| Notification mock | `alerts/notifications.py` | Always (no SMTP/SMS client) |
| Hardcoded series in analytics Demo | `analytics/service.py` | Demo Mode trends |
| UNet/DeepLab placeholders | `flood/models.py` | Raise NotImplementedError |

**REAL-mode failure policy (important):** live weather/satellite/flood paths raise `ProviderUnavailableError` → **503**; they do **not** silently return 34.5 km² / 82% (removed from FE catch-fallback paths in weather/flood/satellite services). GIS still static.

---

## 9. Environment Variables

| Variable | Purpose | Required for live? | Configured locally? | Used by code? | Notes |
| --- | --- | --- | --- | --- | --- |
| `USE_MOCK_PROVIDERS` | Demo vs Real | Sets mode | YES (`false`) | YES | Default in Settings class: `false` |
| `OPENWEATHER_API_KEY` | Current/forecast | **YES** for weather | YES | YES | |
| `OPENWEATHER_QUERY` | City query | Optional (default Alappuzha,IN) | default | YES | |
| `NASA_POWER_ENABLED` | Toggle history | Optional | true | YES | |
| `NASA_POWER_BASE_URL` | Endpoint | Optional | default | YES | |
| `IMD_API_KEY` | IMD JWT | Optional | NO | YES (skipped empty) | |
| `IMD_API_BASE_URL` | IMD host | Optional | default | YES | |
| `COPERNICUS_CLIENT_ID/SECRET` | OAuth | Optional | NO | YES if set | STAC works without |
| `COPERNICUS_STAC_URL` | STAC | Optional | default | YES | |
| `COPERNICUS_MAX_CLOUD` / `LOOKBACK_DAYS` | Search filters | Optional | defaults | YES | |
| `DEMO_LATITUDE/LONGITUDE` | AOI | Optional | defaults | YES | NASA + STAC bbox |
| `DATABASE_URL` | DB | YES | sqlite | YES | |
| `CORS_ORIGINS` | CORS | YES for FE | YES | YES | |
| `YOLO_WEIGHTS_PATH` | Local weights | For real CV | NO | YES | |
| `VISION_STORAGE_DIR` | Uploads | For CV | default | YES | |
| `ENABLE_REAL_EMAIL/SMS/PUSH` | Flags | N/A (unwired) | false | YES | Still no client |
| `SMTP_HOST` / `SMS_API_KEY` / `PUSH_API_KEY` | Notify | Unused effectively | NO | Checked then refused | |
| `VITE_API_BASE_URL` | FE→BE | YES | YES | YES | |
| `VITE_USE_MOCK` | FE mock | Mode | `false` | YES | |

Docker Compose overrides mock flags to **true** — production-like docker-compose as checked in is **Demo Mode**.

---

## 10. Failure / Fallback Behavior (from code)

| Condition | OpenWeather | NASA POWER | Copernicus STAC/thumb | IMD | YOLO |
| --- | --- | --- | --- | --- | --- |
| Credentials missing | 503 `ProviderUnavailableError` | N/A | Search still attempted | Empty alerts / status unavailable | Demo only if mock; else 503 |
| Timeout / HTTP error | 503 | 503 | 503 | Caught → empty list in `LiveWeatherProvider.alerts` | Runtime error → Demo only if mock |
| Invalid/empty payload | 503 | 503 | 503 | 503 or unavailable | 400 bad image |
| REAL mode silent mock fallback | **No** (removed from OpenWeather legacy) | **No** | **No** synthetic raster | Does not invent IMD | **No** DemoVision in REAL |

Notifications: always non-delivery except dashboard channel `{delivered: True, mode: dashboard}`.

---

## 11. Background Jobs / Webhooks / AI-ML

| Capability | Present? | Evidence |
| --- | --- | --- |
| Cron / APScheduler / Celery | **NO** | No matches in backend app |
| Redis / queue | **NO** | — |
| Inbound webhooks | **NO** | No webhook routes |
| SSE alert stream | **YES** (in-process) | `alerts/stream.py` |
| Trained flood segmentation | **NO** | Heuristics + NotImplemented UNet/DeepLab |
| YOLO | Optional local file | `yolo_model.py` |
| `ai/` stubs | Unused by API | No imports |

---

## 12. Live vs Demo Functionality Matrix

| Feature | Implemented (UI+API) | Live API | Real data reaches UI | Mock/seed | Production-ready? |
| --- | --- | --- | --- | --- | --- |
| Weather current/forecast | YES | YES | YES (REAL+key) | Demo mock | **Partial** (single city, no auth, no SLA) |
| Weather history (NASA) | YES | YES | YES | Demo mock | Partial |
| IMD alerts | YES (client) | NO locally | NO | N/A | **NO** |
| Sentinel catalogue/preview | YES | YES | YES | Demo synthetic | Partial (preview only) |
| Flood change detection | YES | YES (imagery) | YES (heuristic) | Demo synthetic change | **NO** as flood authority product |
| Damage assessment | YES | YES (imagery) | Derived | Demo rasters | **NO** |
| Risk scores | YES | Inputs live | Derived rules | Demo overlay 82% | **NO** as official warning |
| Alerts engine | YES | Inputs may be live | App-generated | Seed alerts exist | **NO** (no dispatch, no auth) |
| CV upload | YES | No cloud | User file | DemoVision default | **NO** without weights/ops |
| Disasters/resources/rescue | YES | NO | Seed | Seed | **NO** (demo inventory) |
| GIS overlays | YES UI | NO | Static mock | Always | **NO** |
| Analytics | YES | Mixed | Mixed | Demo series | **NO** |
| Reports PDF | Stub | NO | NO | JSON only | **NO** |
| Auth / multi-tenant | NO | — | — | — | **NO** |
| Notifications SMS/email | Stub | NO | NO | Mock | **NO** |

---

## 13. Real-World Data Score (strict)

### Live integration coverage

**Actually used live integrations in VisionGuard path:** OpenWeather, NASA POWER, Copernicus STAC, Copernicus thumbnails, Esri tiles ≈ **5**  
**Coded external integrations including unwired/disabled:** +IMD, +OAuth, +SMTP/SMS/Push stubs, +YOLO-local ≈ **10+**  

**Coverage ≈ 5 / 10 ≈ 50%** of coded external surfaces are live today; of **product-critical** EO/weather surfaces, weather+Sentinel are live when configured.

### Real data coverage (product features)

Count major UI features ~14 (weather, history, risk, satellite, compare, flood, damage, alerts, CV, disasters, rescue, GIS, analytics, reports).  
Clearly backed by external real inputs in REAL mode: weather, history, satellite, compare, flood change, damage (~6).  
Rest seeded/static/mock.  

**≈ 6/14 ≈ 43%** features touch real external inputs (and several of those are **heuristic derivatives**, not authoritative products).

### Production readiness (honest)

| Dimension | Rating |
| --- | --- |
| Live APIs | Partial |
| Real data | Partial (AOI demo) |
| Authentication / authorization | **None** |
| Persistence | SQLite/optional Postgres; seed-heavy |
| Error handling | Good for provider 503; weak globally |
| Retries / rate limits | Minimal (thumbnail timeout 90s; little retry) |
| Monitoring | Basic logging only |
| Security | CORS open to configured origins; no auth; secrets in `.env` |
| Deployment | Docker Compose defaults to **Demo Mode** |
| Tests | Pytest suite forces `USE_MOCK_PROVIDERS=true` in `conftest.py` |
| Fallback honesty | REAL mode mostly honest 503; GIS still fake |

**Overall production readiness for “live disaster management system”: LOW (~2/10).**  
**Readiness as “demo + partial live weather/EO lab”: MODERATE (~5/10).**

---

## 14. Recommended Next Steps (gaps only)

1. Wire or remove legacy `src/` and unused `ai/` stubs to avoid false “integrated” claims.  
2. Make GIS come from API/DB or clearly badge “STATIC DEMO LAYERS” in UI always.  
3. Add auth before any multi-user deployment.  
4. IMD credentials + product mapping if official warnings are required.  
5. Full Sentinel SAFE / NIR NDWI (or trained model) before calling flood maps operational.  
6. Implement or delete email/SMS/push flags.  
7. Align Docker Compose with REAL defaults only if that is the intended deploy mode.  
8. Add provider retries, caching policy, and observability.

---

## FINAL TRUTH

### What live APIs are actually being called today?

With current local REAL config: **OpenWeatherMap**, **NASA POWER**, **Copernicus STAC search**, **Sentinel preview thumbnail HTTP fetches**, and **Esri public basemap tiles** (browser). **Not** IMD, **not** SMTP/SMS/push, **not** cloud YOLO, **not** the legacy `src/` NOAA app (unless run separately).

### What functionality currently uses real-world data?

Weather current/forecast/history; Sentinel catalogue + preview-based flood **change** and damage **heuristics**; map basemap tiles; alert **signals** derived from live weather when generated. User-uploaded images for CV.

### What is still mocked / static / seeded?

Disasters, locations, risk-zone inventory, rescue resources/centers, GIS layers (`gisMock`), notification delivery, DemoVision (without weights), U-Net/DeepLab, PDF reports, analytics population/building inventory, Docker-default Demo Mode, FE `mock.ts` when `VITE_USE_MOCK=true`.

### Complete real workflow of the product?

Operator opens SPA → unauthenticated `/api/v1` calls → services either hit live weather/EO providers (REAL) or mocks (DEMO) → results + seeded operational entities rendered on dashboards/maps → alerts optionally generated from weather-derived scores into DB + in-memory SSE → no external citizen notification.

### Where does real-world data enter?

HTTP egress from `httpx` clients in `openweather_provider.py`, `nasa_power.py`, `copernicus_provider.py` (+ browser tile requests).

### Where is it stored?

- Weather: mostly **ephemeral response objects** (not a durable weather warehouse).  
- Satellite metadata + flood/damage/vision analyses: **SQLAlchemy DB** (`visionguard.db` or Postgres).  
- Vision binaries: **local filesystem** `VISION_STORAGE_DIR`.

### Where is it transformed?

Provider → pydantic/dataclasses → rule models / OpenCV masks → API schemas → React pages.

### Where does data reach the user?

React pages under `/weather`, `/satellite`, `/satellite/compare`, `/flood-detection`, `/damage-assessment`, `/dashboard`, `/alerts`, etc. (`frontend/src/App.tsx`).

### Which APIs are configured but not actually used?

Locally: **IMD** (no key), **Copernicus OAuth** (no client), **SMTP/SMS/Push** (flags false and clients unwired), **YOLO path** empty. Legacy NOAA in `src/` unused by VisionGuard.

### Which advertised-looking features are not backed by live data?

GIS situational layers; disaster/resource inventories; rescue optimality; official IMD warnings; trained segmentation; real multi-channel alerting; PDF reporting; multi-user auth.

### What is genuinely production-ready today?

**Nothing** as a sovereign/production disaster-management platform.  
**Usable as a lab prototype:** live weather for one query city + latest-available Sentinel preview change indication + seeded ops UI.

### Exact remaining gaps before “real-world/live system”?

Auth/RBAC; durable ops data (not only seed); official warning feeds (IMD); analysis-grade EO (not RGB thumbnails); validated models; real notification channels; GIS from live sources; workers/monitoring/retries; deploy config that matches REAL mode; remove or isolate legacy/stub packages that inflate perceived completeness.

---

*End of audit. Evidence roots: `backend/app/**`, `frontend/src/**`, `docker-compose.yml`, `.env.example`, local env presence checks (secrets redacted), `src/` and `ai/` confirmed unwired from VisionGuard main.*
