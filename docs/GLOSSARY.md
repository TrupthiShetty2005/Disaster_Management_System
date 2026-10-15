# Glossary

**GIS** — Geographic Information System. Here: Leaflet maps plus GeoJSON layers.

**GeoJSON** — JSON for points, lines, polygons. Coordinates are `[longitude, latitude]`.

**Risk zone** — A named polygon in the DB (`RiskZone`) with a score/level; the dashboard map also draws polygons from `gisMock.ts` which may not be the same objects.

**Flood segmentation** — Labeling pixels as water. Here: color threshold, not a trained U-Net.

**Object detection** — Boxes around objects. Default: fake boxes (`DemoVisionModel`). Optional: local YOLO.

**Damage assessment** — Comparing before/after rasters and assigning building/road classes by rules.

**Rescue priority** — A 0–100 style score from weighted factors (`RescuePriorityService`).

**Early warning** — `AlertEngine` writing dashboard alerts from thresholds. Not an official IMD/NDMA feed.

**PostGIS** — Postgres extension for spatial SQL. Docker can run it; this app’s models still use JSON.

**YOLO** — You Only Look Once detector. Optional local Ultralytics weights; not bundled.

**U-Net** — Common segmentation net. **Specified but not currently implemented** (`NotImplementedError`).

**Raster** — Grid of pixels (the synthetic RGB arrays).

**Vector** — Points/lines/polygons (GeoJSON).

**Inference** — Running a model on an input. Demo vision “infers” by hashing size; YOLO infers if loaded.

**Confidence** — A 0–1 (or percent) score on a detection or analysis. Demo values are assigned, not calibrated.

**Demo mode** — UI: `VITE_USE_MOCK` not `"false"`. Backend: `USE_MOCK_PROVIDERS=true`. Header also shows a DEMO MODE label. Means simulated/mock data, not live emergency systems.

**Prototype AI Risk Estimate** — Label on flood/cyclone JSON meaning a formula, not a certified model.

**SIMULATED** — Canonical Kuttanad numbers (82%, 34.5 km², etc.) applied in overlay/analytics.
