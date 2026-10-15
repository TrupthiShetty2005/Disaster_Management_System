# VisionGuard AI — API

Base path: `/api/v1`  
OpenAPI: `http://localhost:8000/docs`

All list endpoints return `{ "items": [...], "total": n }` unless noted. IDs are UUIDs.

## Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Liveness, environment name, mock-mode flag |

## Disasters

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/disasters` | Active and historical events (`?phase=response`) |
| GET | `/api/v1/disasters/{id}` | Single disaster with related summaries |

## Risk

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/risk-zones` | Risk polygons + scores |
| GET | `/api/v1/risk-zones/{id}` | Zone detail + explainability |

## Weather

Weather is **provider-agnostic**. Without `OPENWEATHER_API_KEY` (or with `USE_MOCK_PROVIDERS=true`), **MockWeatherProvider** is used. OpenWeather is optional and falls back to mock on failure.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/weather/current?location_id=` | Current observation |
| GET | `/api/v1/weather/forecast?location_id=` | Forecast periods |
| GET | `/api/v1/weather/history?location_id=` | Daily history series |
| GET | `/api/v1/weather/rainfall?location_id=` | Cumulative / intensity / anomaly / short-term risk (0–100) |
| GET | `/api/v1/weather/alerts?location_id=` | Provider alerts + persisted risk candidates (no SMS/email) |
| GET | `/api/v1/risk/flood` | Prototype flood probability |
| GET | `/api/v1/risk/cyclone` | Prototype cyclone risk |
| GET | `/api/v1/risk-zones/{id}` | Zone + explainability factors |

Flood/cyclone outputs include `estimate_label`: **Prototype AI Risk Estimate**.

## Vision

CPU by default. Demo model unless `YOLO_WEIGHTS_PATH` is a local file.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/vision/detect` | Multipart `file` — boxes (demo or local YOLO) |
| POST | `/api/v1/vision/analyze` | Same pipeline + incident summary |
| GET | `/api/v1/vision/health` | Backend, GPU flag, specialized-class honesty |
| GET | `/api/v1/vision/jobs/{id}/annotated` | JPEG with boxes/labels |

## Satellite

Synthetic Sentinel-2 / Landsat stand-ins. No GEE credentials required.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/satellite/images` | Demo scene catalog |
| GET | `/api/v1/satellite/images/{id}` | Scene metadata + footprint |
| GET | `/api/v1/satellite/images/{id}/preview` | PNG preview of synthetic raster |
| POST | `/api/v1/satellite/analyze` | `{ image_id, analysis_type }` water/veg/burn/urban/flood |
| GET | `/api/v1/satellite/analysis/{id}` | Stored GeoJSON + metrics |
| POST | `/api/v1/satellite/compare` | `{ before_image, after_image }` change detection |

## Flood detection

OpenCV/NumPy water mask. **Not** a trained U-Net/DeepLab. Interfaces exist for future models.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/flood/analyze` | `{ scene_kind, population }` demo raster pipeline |
| GET | `/api/v1/flood/events` | Stored flood analyses |
| GET | `/api/v1/flood/events/{id}` | One analysis (extent, heatmap, affected assets) |

## Damage assessment

Before/after change detection. JSON report; PDF not implemented.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/damage/analyze` | `{ before_kind, after_kind }` |
| GET | `/api/v1/damage/assessments` | Stored reports |
| GET | `/api/v1/damage/assessments/{id}` | Full JSON report |

## Rescue planning

Prototype decision-support. Not guaranteed optimal. No Google Maps.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/resources` | Inventory (boats, ambulances, teams, …) |
| POST | `/api/v1/resources/allocate` | `{ resource_id, incident_id }` |
| GET | `/api/v1/rescue/priorities` | 0–100 scores + LOW–CRITICAL |
| POST | `/api/v1/rescue/plan` | Generate plan + routes + reasoning |
| GET | `/api/v1/rescue/plans/{id}` | Stored plan |
| POST | `/api/v1/rescue/plans/{id}/decision` | `{ action: accept\|modify\|reject, notes }` (audit log) |

## Early warning / alerts

Dashboard alerts only. SMS/email/push adapters are **mock** unless explicitly configured (and even then no live client is wired). Simulated alerts are **not** official emergency warnings.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/alerts` | History (`severity`, `location_id`, `status`, `disaster_type`, `date_from`, `date_to`) |
| GET | `/api/v1/alerts/{id}` | One alert |
| POST | `/api/v1/alerts/generate` | Run AlertEngine on weather/risk signals |
| POST | `/api/v1/alerts/{id}/acknowledge` | `{ actor }` |
| POST | `/api/v1/alerts/{id}/resolve` | `{ actor }` |
| GET | `/api/v1/alerts/stream` | SSE prototype stream |
| GET | `/api/v1/alerts/events` | Poll fallback (`?since=`) |

Thresholds live in `backend/app/services/alerts/rules.json` (not hardcoded in pages).

## Analytics, reports, incident command

All streams attach to demo incident `aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa` (Kuttanad).

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/analytics/overview` | KPIs + series (`date_from/to`, `disaster_type`, `location_id`, `severity`) |
| GET | `/api/v1/analytics/disasters` | Frequency / listing |
| GET | `/api/v1/analytics/damage` | Building/road/flood stats |
| GET | `/api/v1/analytics/resources` | Utilization |
| GET | `/api/v1/analytics/risks` | Zone scores |
| GET | `/api/v1/analytics/alerts` | Severity mix |
| GET | `/api/v1/incidents/{id}` | Command picture (weather, risk, flood, GIS, alerts, rescue) |
| POST | `/api/v1/reports/generate` | `{ kind: incident\|damage\|rescue\|risk }` JSON (PDF later) |
| GET | `/api/v1/exports/{dataset}` | CSV: analytics, incident, damage, resources, alerts |
| GET | `/api/v1/audit-logs` | Decision audit trail |

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/resources` | Rescue assets |
| GET | `/api/v1/evacuation-centers` | Shelters and capacity |

## Errors

Structured JSON:

```json
{ "detail": "Human-readable message", "code": "not_found" }
```

Validation errors follow FastAPI/Pydantic `422` shape.
