# Code explanation (presentation-oriented)

Do not paste large source listings. This is the logic a viva audience needs.

## Frontend shell

**What:** Browser app.  
**Why:** Operators need maps and forms.  
**Starts:** `main.tsx` → `App.tsx` → `AppLayout`.  
**Calls:** `services/*`.  
**Shows:** pages in the outlet.

## apiClient

**What:** `fetch` wrapper.  
**Receives:** path + JSON or File.  
**Returns:** typed JSON or mock via each domain service.  
**Switch:** `isMockMode()`.

## Dashboard

**What:** Home KPIs + GIS.  
**Gets:** disasters, alerts, resources, weather, analytics.  
**Map data:** `gisMock`, not the incident API.  
**Shows:** `DisasterMap`, `KpiCard`, charts.

## WeatherIntelService

**What:** One facade for weather + derived risk.  
**Calls:** weather provider, `BaselineFloodRiskModel`, `evaluate_cyclone`, `analyze_rainfall`.  
**Returns:** snapshots and scores.  
**Shown on:** Weather and Risk pages.

## AlertEngine

**What:** Turns numeric signals into alert rows.  
**Reads:** `rules.json`.  
**Writes:** `alerts`.  
**Does not:** send real SMS.

## SatelliteService

**What:** Fake scene catalog and raster math.  
**Calls:** `MockSatelliteProvider`, `processing.py`.  
**Returns:** metrics + GeoJSON.  
**Shown on:** Satellite pages.

## FloodDetectionService

**What:** Demo water mask pipeline.  
**Input:** `scene_kind` string.  
**Output:** `FloodAnalysis` row.  
**Shown on:** Flood page overlay.

## VisionPipeline

**What:** Upload → validate → detect → annotate.  
**Model:** Demo or YOLO factory.  
**Shown on:** Computer Vision page.  
**Does not call:** rescue planner.

## DamageAssessmentService

**What:** Two rasters → change % → class counts → JSON.  
**Shown on:** Damage page.  
**PDF:** none.

## RescuePlanningService

**What:** Build a plan JSON from rules and a toy graph.  
**Human:** accept/modify/reject with audit.  
**Shown on:** Rescue page.

## AnalyticsService

**What:** Count DB rows; in mock mode overwrite key KPIs with `DEMO_*`.  
**Shown on:** Analytics and dashboard charts.

## IncidentCommandService

**What:** Bundle many queries for one disaster id.  
**Shown on:** `/disasters/:id`.

## GIS (frontend)

**What:** Layered GeoJSON for the command map.  
**Why:** Fast demo map without spatial SQL.  
**Limitation:** can drift from API seed geometry.

## ai/ package

**What:** Stub detect/classify dicts.  
**Who calls:** `ai/tests`, not FastAPI.
