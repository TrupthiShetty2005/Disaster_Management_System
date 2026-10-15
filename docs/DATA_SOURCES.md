# VisionGuard AI — Data sources

## Principle

Every external source is an **adapter**. If credentials or live feeds are missing, the app uses **deterministic mock data** (Indian demo scenarios, fictional operational details — not live government feeds).

## Weather

| Source | Status | Adapter |
|--------|--------|---------|
| OpenWeather | Optional (`OPENWEATHER_API_KEY`) | Planned plug-in from legacy `src/app/services/openweather_services.py` |
| NOAA | Optional | Legacy `src/app/services/noaa_services.py` |
| NASA POWER | Optional | Legacy `src/app/services/nasa_services.py` |
| Seed DB / JSON | Default | `backend` seed + `data/mock` |

## Satellite imagery

No live satellite provider is configured. `satellite_images` rows point at local demo paths under `data/mock/satellite/`. Analysis results are stored as `image_analysis_results` + `detected_objects`.

## GIS

Locations, risk zones, roads, buildings, flood extents: GeoJSON in the database / mock JSON. PostGIS can replace JSON geometry later.

## MongoDB

Document store for raw imagery metadata is a **future option**. The application does not depend on MongoDB.
