# End-to-end example (Kuttanad demo flood)

This is the **seeded** incident, not an automatic single backend job. The operator walks screens. IDs:

- Disaster: `aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa` (`DIS_FLOOD` in `backend/app/db/seed.py`)
- Location: `11111111-1111-4111-8111-111111111111`
- Frontend copy: `frontend/src/constants/demo.ts`

## 1. Open dashboard

- File: `frontend/src/pages/DashboardPage.tsx`
- Calls: `fetchDisasters` → `GET /api/v1/disasters` (`DisasterService`)
- Seeded row: title “Kuttanad monsoon inundation (demo)”, `people_at_risk=42000`, `status=active`
- Map: `DisasterMap` ← `gisMock.ts` (independent of that GET)
- KPI flooded area / buildings: `DEMO_STATS` in the page (34.5 km², 18), labeled simulated

## 2. Incident command

- Link uses `DEMO_INCIDENT_ID` → `/disasters/:id`
- `DisasterDetailPage` → `fetchIncidentPicture` → `GET /api/v1/incidents/{id}`
- Class: `IncidentCommandService.picture` (`backend/app/services/incident/service.py`)
- Returns narrative from `DEMO_NARRATIVE`, plus nested weather/risk/flood/roads/buildings/resources/alerts

## 3. Weather

- `WeatherPage` → `GET /api/v1/weather/current`
- `WeatherIntelService.current` → `get_weather_provider()`
- Default: `MockWeatherProvider` (e.g. 27.4°C, 48.2 mm rain in the mock implementation)
- `provider_live: false`

## 4. Risk

- `GET /api/v1/risk/flood` → `WeatherIntelService.flood` → `BaselineFloodRiskModel.evaluate`
- Then `overlay_demo_flood` if `use_mock_providers` → **82%**, factors HIGH/MEDIUM
- Zones: `GET /api/v1/risk-zones` → `RiskService.explain`; Polder A uses the same overlay

## 5. Satellite

- `GET /api/v1/satellite/images` → `SatelliteService` + `MockSatelliteProvider.list_scenes`
- Analyze: `POST /api/v1/satellite/analyze` → `generate_demo_raster` + `detect_water` (`processing.py`)
- Preview PNG is generated, not a downloaded Sentinel granule

## 6. Flood

- `POST /api/v1/flood/analyze` → `FloodDetectionService.analyze` → `DemoFloodModel.segment`
- Persists `FloodAnalysis` (not the seed table `FloodEvent`, which is a different model)
- UI: `FloodPage.tsx` + `SatelliteOverlayMap`

## 7. Damage

- `POST /api/v1/damage/analyze` → `DamageAssessmentService`
- `compare_scenes` + `classify_building` / `classify_road`
- `pdf_available` remains false

## 8. Rescue

- `POST /api/v1/rescue/plan` → `RescuePlanningService.generate_plan`
- `recommend_resources` (`rescue/recommend.py`), `shortest_path` (`rescue/routing.py`)
- Human: `POST /api/v1/rescue/plans/{id}/decision` → `decide` + `AuditLog`

## 9. Alerts

- `POST /api/v1/alerts/generate` → `EarlyWarningService.generate` → `AlertEngine` + `rules.json`
- `notifications.dispatch` does not send SMS
- Dashboard also `GET /api/v1/alerts`

## 10. Analytics

- `GET /api/v1/analytics/overview` → `AnalyticsService.overview`
- With mock providers: flooded **34.5**, buildings **18**, roads **3**, population **42000**, `flood_risk_pct` **82**, `data_class` **SIMULATED**

These steps are **screens and APIs composed by the user**, not one orchestrator function that runs 1–10 in a single request.
