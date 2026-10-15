# Architecture decisions

This document separates **what the repository contains** from **likely reasons** (inferred, not from an ADR file in git).

## Observed implementation

- **React + TypeScript + Vite** in `frontend/`
- **FastAPI + Pydantic + SQLAlchemy** in `backend/`
- **SQLite by default**; **Postgres URL** and **PostGIS Docker image** in Compose
- **Python** for API, OpenCV, numpy
- **Leaflet** for maps; **Chart.js** for charts
- **Docker Compose** for optional three-service stack
- **No PyTorch** in requirements or imports
- **OpenCV** for rasters, masks, image decode/annotate
- **Pluggable protocols** (`WeatherProvider`, `VisionModel`, `FloodSegModel`) with mock/demo defaults
- **GeoJSON in JSON columns**, not SQL geometry types
- **No JWT auth**

## Likely architectural rationale (inferred)

| Choice | Likely rationale | Certainty |
| --- | --- | --- |
| React SPA | Interactive ops console (maps, many pages) | High — matches UI |
| FastAPI | Typed JSON APIs and `/docs` for a student project | High |
| SQLite default | Run without Docker for demo/tests | High — `database_url` default |
| PostGIS in Compose | Future spatial queries; image is ready | Medium — types not used yet |
| JSON GeoJSON | Same models on SQLite and Postgres | High — documented in ARCHITECTURE.md |
| Mock providers | Demo without keys | High — `USE_MOCK_PROVIDERS` |
| OpenCV heuristics | Visible “AI-like” outputs without training data | High — comments in flood/vision code |
| Leaflet | Standard web GIS for GeoJSON | High |
| Docker | Reproducible postgres+app | Medium |
| Separate `ai/` package | Place to drop weights later | Medium — unused by API |
| Legacy `src/` | Earlier weather/NASA experiments | High — not wired to new UI |

## Specified vs implemented

| Specification-style idea | In this repo |
| --- | --- |
| Live GEE/Sentinel | Class name exists; `get_satellite_provider()` returns mock |
| Trained U-Net flood | Not implemented |
| Government SMS alerts | Not implemented |
| PostGIS spatial ops | Not implemented |
| User login | Not implemented |
| PyTorch training | Not present |
