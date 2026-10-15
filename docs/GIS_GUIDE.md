# GIS guide

## Map library

**Leaflet 1.9** + **react-leaflet 5**. Basemap tiles: Carto `dark_all` (`https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`). That is a **public cartographic basemap**, not live disaster satellite.

`DisasterMap` can overlay an extra tile layer when the `satellite` visibility flag is on; it is still a raster tile URL in the component, not the FastAPI satellite PNG catalog.

## Coordinate system

GeoJSON positions are `[longitude, latitude]` (e.g. 76.522, 9.517). No map projection library (proj4) is used. Leaflet displays them as geographic coordinates on Web Mercator tiles.

## Where geographic data comes from

### Command dashboard / risk map (`DisasterMap`)

```
frontend/src/data/gisMock.ts
  → fetchGisCatalog() in services/gis.ts
  → always returns gisCatalog (even if VITE_USE_MOCK is false)
  → DisasterMap GeoJSON layers
  → click → SelectedAreaPanel
```

Layers (`types/gis.ts`): satellite (tiles), disasters, floodCurrent, floodPredicted, risk, population, roads, buildings, evacuation, rescue, hospitals, shelters.

This path **does not** load `GET /api/v1/incidents/{id}` GeoJSON into `DisasterMap`.

### Flood / satellite / damage overlays (`SatelliteOverlayMap`)

```
POST /flood/analyze or satellite/damage APIs
  → boundary_geojson / overlay_geojson in JSON
  → SatelliteOverlayMap <GeoJSON>
```

These overlays **are** API-driven when mock mode is off.

### Rescue map (`RescuePlanningMap`)

Uses plan payload / resource coordinates from rescue APIs (and mock objects in mock mode).

### Situation map (`SituationMap`)

`fetchMapPoints()` in `intel.ts` **always** returns `mockMapPoints`.

## Geographic calculations

- `flood/geo.py`: pixel → lon/lat using bbox, polygon extraction, heatmap cells, `flooded_area_km2`.
- `satellite/processing.py`: `bbox_area_km2`, `mask_to_geojson`, `flooded_metrics`.
- `SatelliteOverlayMap.polygonAreaKm2`: client-side area helper.
- Rescue `routing.py`: **abstract graph**, not spherical geodesic routing.

## Spatial database

**Specified (PostGIS) but not currently implemented** as native geometry types or spatial indexes. Docker can run PostGIS; the ORM still uses JSON.

## User interaction

Layer toggles and name search (`searchFeatures`) on `DisasterMap`. Selecting a feature updates `SelectedAreaPanel`.
