# API reference

Base URL in development: `http://127.0.0.1:8000`  
Prefix: `/api/v1` (from `Settings.api_v1_prefix`)  
OpenAPI UI: `/docs`  
Source of truth: `backend/app/api/v1/router.py`  
Schemas: `backend/app/schemas/common.py`  
Errors: `{ "detail": "...", "code": "not_found" | "http_error" | "internal_error" }` from `backend/app/core/errors.py`. Validation failures are FastAPI **422**.

There is **no authentication**. CORS is configured in `backend/app/main.py`.

`GET /` (not under `/api/v1`) returns `{ "service", "docs", "api" }`.

---

## Health

### GET `/api/v1/health`

**Purpose:** Liveness and whether mock providers are on.

**Query / body:** none

**Response:** `HealthOut` — `status`, `service`, `environment`, `use_mock_providers`

**DB:** none  
**Service:** reads `settings` only  
**Implementation:** `health()` in `router.py`

---

## Disasters

### GET `/api/v1/disasters`

**Purpose:** List disasters.

**Query:** `phase` optional string (e.g. response)

**Response:** `{ items: DisasterOut[], total }`

**DB:** `disasters` via `DisasterRepository`  
**Service:** `DisasterService.list`  
**Implementation:** `list_disasters`

### GET `/api/v1/disasters/{disaster_id}`

**Purpose:** One disaster.

**Path:** `disaster_id`

**Errors:** 404 Disaster not found

**DB:** `disasters`  
**Service:** `DisasterService.get`

---

## Risk zones

### GET `/api/v1/risk-zones`

**Purpose:** Zones plus explained scores/factors.

**Response:** `RiskZoneList` including `flood_probability`, `contributing_factors`, `estimate_label`

**DB:** `risk_zones`  
**Service:** `RiskService.list` + `explain` (weather + `BaselineFloodRiskModel`, demo overlay for Polder A)

### GET `/api/v1/risk-zones/{zone_id}`

Same as one item of the list. 404 if missing.

### GET `/api/v1/risk/flood`

**Query:** `location_id` optional

**Response:** `FloodRiskOut` — probability, score, level, factors, recommended_action, estimate_label

**Service:** `WeatherIntelService.flood`  
**DB:** not required for the calculation (weather comes from provider)

### GET `/api/v1/risk/cyclone`

**Query:** `location_id` optional  
**Response:** `CycloneRiskOut`  
**Service:** `WeatherIntelService.cyclone` → `evaluate_cyclone`

---

## Weather

All weather GETs take optional `location_id`.

### GET `/api/v1/weather/current`

**Response:** `WeatherCurrentOut` (temp, humidity, rain, wind, pressure, visibility, river_level, storm_probability, conditions, `provider_live`)

**Service:** `WeatherService.current` → provider (`MockWeatherProvider` default)

### GET `/api/v1/weather/forecast`

**Response:** `{ items, total, provider_live }`

### GET `/api/v1/weather/history`

**Response:** `{ items: WeatherHistoryPointOut[], total }`

### GET `/api/v1/weather/rainfall`

**Response:** `RainfallAnalysisOut` — cumulative_mm, intensity_mm_h, anomaly, short_term_risk, label

**Service:** `analyze_rainfall` on history series

### GET `/api/v1/weather/alerts`

**Response:** `WeatherAlertsOut` — provider alerts plus generated DB candidates, flood_probability, cyclone_risk

**DB:** may insert `Alert` via `persist_alert_candidate` if thresholds exceeded

---

## Alerts

### GET `/api/v1/alerts`

**Query:** `severity`, `location_id`, `status`, `disaster_type`, `date_from`, `date_to`

**Response:** `{ items: AlertOut[], total }` sorted CRITICAL first

**Service:** `EarlyWarningService.list`

### GET `/api/v1/alerts/stream`

SSE (`text/event-stream`). In-memory queue (`alerts/stream.py`). Not a durable event bus.

### GET `/api/v1/alerts/events`

**Query:** `since` optional  
**Response:** `{ items, total }` from the same in-memory list

### POST `/api/v1/alerts/generate`

**Body:** `{ "location_id": string | null }` (`AlertGenerateRequest`)

**Service:** `EarlyWarningService.generate` → `AlertEngine`  
**DB:** inserts `alerts`  
**Notifications:** `notifications.dispatch` — mock / refused, not carrier SMS

### GET `/api/v1/alerts/{alert_id}`

404 if missing.

### POST `/api/v1/alerts/{alert_id}/acknowledge`

**Body:** `{ "actor": "ops.demo" }` default  
**DB:** updates status ACKNOWLEDGED

### POST `/api/v1/alerts/{alert_id}/resolve`

**Body:** `{ "actor" }`  
**DB:** RESOLVED

---

## Resources and rescue

### GET `/api/v1/resources`

**Response:** `ResourceList`  
**Service:** `ResourceService` / `RescuePlanningService` listing (router uses `_resource_out`)

### POST `/api/v1/resources/allocate`

**Body:** `{ resource_id, incident_id }`  
**DB:** updates `rescue_resources` status DEPLOYED, `assigned_incident`  
**Audit:** allocate action

### GET `/api/v1/rescue/priorities`

**Response:** scored `RescuePriorityList`  
**Service:** `RescuePlanningService` priority scoring

### POST `/api/v1/rescue/plan`

**Body:** `{ disaster_id?: string }` defaults to demo incident in service  
**Response:** `RescuePlanOut` with nested `plan` JSON  
**DB:** `rescue_plans`

### GET `/api/v1/rescue/plans/{plan_id}`

404 if missing.

### POST `/api/v1/rescue/plans/{plan_id}/decision`

**Body:** `{ "action": "accept"|"modify"|"reject", "notes": "" }`  
**DB:** plan decision + `audit_logs`

### GET `/api/v1/evacuation-centers`

**Response:** `EvacuationCenterList`  
**Service:** `EvacuationService`

---

## Satellite

### GET `/api/v1/satellite/images`

Catalog after `sync_catalog`. Mock scenes + seeded rows.

### GET `/api/v1/satellite/images/{image_id}`

Metadata + footprint.

### GET `/api/v1/satellite/images/{image_id}/preview`

PNG of **synthetic** raster (`encode_png`). Content-Type image/png.

### POST `/api/v1/satellite/analyze`

**Body:** `{ image_id, analysis_type }` default analysis_type `"flood"`  
**DB:** `image_analysis_results`  
**Logic:** OpenCV channel masks on generated raster — not a trained EO model

### GET `/api/v1/satellite/analysis/{analysis_id}`

Stored metrics + GeoJSON.

### POST `/api/v1/satellite/compare`

**Body:** `{ before_image, after_image }`  
**Logic:** `compare_scenes` on two rasters

---

## Computer vision

### GET `/api/v1/vision/health`

**Response:** model `health()` dict (`demo` vs `yolo`, gpu_required false, notes)

### POST `/api/v1/vision/detect`

**Body:** multipart field `file`  
**Service:** `VisionPipeline.run(..., mode="detect")`  
**DB:** `vision_jobs`  
**Files:** `VISION_STORAGE_DIR`

### POST `/api/v1/vision/analyze`

Same pipeline, `mode="analyze"` (incident summary).

### GET `/api/v1/vision/jobs/{job_id}/annotated`

JPEG bytes. 404 if missing.

**Errors:** 400 empty/unsupported/too large/not an image (`validation.py`)

---

## Flood

### POST `/api/v1/flood/analyze`

**Body:** `{ scene_kind: "flood", population: 42000 }`  
**Service:** `FloodDetectionService.analyze`  
**DB:** `flood_analyses`  
**Model:** `DemoFloodModel` (U-Net/DeepLab raise if selected)

### GET `/api/v1/flood/events`

List analyses.

### GET `/api/v1/flood/events/{event_id}`

404 if missing.

---

## Damage

### POST `/api/v1/damage/analyze`

**Body:** `{ before_kind, after_kind }`  
**DB:** `damage_reports`  
**Response:** `pdf_available: false`

### GET `/api/v1/damage/assessments`

### GET `/api/v1/damage/assessments/{assessment_id}`

---

## Analytics, incident, reports, audit, export

### GET `/api/v1/analytics/overview`

**Query:** `date_from`, `date_to`, `disaster_type`, `location_id`, `severity`  
**Service:** `AnalyticsService.overview`  
When `use_mock_providers`, KPIs use `DEMO_*` constants (`data_class: SIMULATED`).

### GET `/api/v1/analytics/disasters`

### GET `/api/v1/analytics/damage`

### GET `/api/v1/analytics/resources`

### GET `/api/v1/analytics/risks`

### GET `/api/v1/analytics/alerts`

Same optional date/type filters as overview where the router passes `_analytics_filters`.

### GET `/api/v1/incidents/{incident_id}`

**Service:** `IncidentCommandService.picture`  
Combined JSON: incident, weather, zones, flood, infrastructure, roads, buildings, resources, alerts, priorities, rescue_plan, audit, timeline, links

### POST `/api/v1/reports/generate`

**Body:** `{ kind: "incident"|"damage"|"rescue"|"risk", disaster_id? }`  
**PDF:** not generated (`to_pdf` returns None)

### GET `/api/v1/audit-logs`

Last 100 `audit_logs` by created_at desc.

### GET `/api/v1/exports/{dataset}`

**Path dataset:** `analytics` | `alerts` | `resources` | `damage` | `incident`  
**Response:** `text/csv`  
**404:** unknown dataset

---

## Not present

- No `/auth` login JWT routes
- Legacy `src/` NASA/NOAA/OpenWeather routes are **not** mounted on this app
