# User workflows

Default **frontend** mock (`VITE_USE_MOCK` not `"false"`): the same screens run using `src/data/mock.ts` without FastAPI. Below assumes `VITE_USE_MOCK=false` and backend up.

## Dashboard

1. USER opens `/dashboard`
2. FRONTEND `DashboardPage` + `useAsync`
3. API GET `/disasters`, `/alerts`, `/resources`, `/weather/current`, `/analytics/overview`
4. GIS from `gisMock` (not API)
5. UI: KPIs (`DEMO_STATS` for flood area/buildings/population in the dashboard code), map, alerts, charts

## Weather monitoring

1. USER opens `/weather`
2. GET `/weather/current|forecast|history|rainfall`, `/risk/flood`, `/risk/cyclone`, `/weather/alerts`
3. `WeatherIntelService` + mock or OpenWeather
4. UI: numbers, Chart.js, flood 82% when mock overlay applies

## Risk analysis

1. USER opens `/risk-intelligence`
2. GET `/risk-zones` (`RiskService.explain`)
3. Map still `gisMock`; panel shows API zone factors
4. USER clicks a zone button

## Satellite analysis

1. USER opens `/satellite`
2. GET `/satellite/images`
3. USER runs analyze → POST `/satellite/analyze`
4. Overlay GeoJSON on `SatelliteOverlayMap`
5. Compare page: POST `/satellite/compare`

## Flood detection

1. USER clicks Run flood analysis
2. POST `/flood/analyze`
3. `DemoFloodModel` + GeoJSON saved
4. Map shows extent/heatmap toggles

## Computer vision

1. USER selects a file
2. POST `/vision/analyze` multipart
3. `VisionPipeline` + DemoVisionModel (or local YOLO)
4. UI shows severity, list, annotated image URL

## Damage assessment

1. USER runs analysis
2. POST `/damage/analyze`
3. JSON report + overlay
4. Doughnut charts from `report.building_statistics` / `road_statistics`

## Rescue planning

1. USER generates plan → POST `/rescue/plan`
2. Rules + demo graph
3. USER accept/modify/reject → POST `.../decision`
4. Audit log row

## Alerts

1. USER generate → POST `/alerts/generate`
2. Engine + `rules.json` + mock notifications
3. Ack/resolve POSTs
4. Optional SSE if not mock mode

## Analytics

1. USER opens `/analytics`
2. GET `/analytics/overview`
3. Simulated KPI overlay when backend mock providers on
4. Settings page can GET CSV `/exports/{dataset}`
