# Project summary

## What VisionGuard AI is

A **university/demo decision-support console** for a **simulated** Kerala flood (Kuttanad). It is **not** an operational emergency-management system.

## What has actually been built

A React ops UI and a FastAPI `/api/v1` backend with SQLite (or Postgres URL), seeded demo disasters, Leaflet maps, Chart.js, OpenCV raster heuristics, rule-based risk/rescue/alerts, optional OpenWeather and optional local YOLO, Docker Compose files, and pytest/vitest tests.

## Architecture

Browser → Vite React → `apiClient` → FastAPI router → services → SQLAlchemy JSON+relational data. See [diagrams/system-architecture.mmd](./diagrams/system-architecture.mmd).

## Main modules

Dashboard, weather, risk, satellite, flood, damage, computer vision, rescue, alerts, analytics, incident command, settings.

## Technology stack

React 19, TS, Vite, Tailwind, Leaflet, Chart.js; FastAPI, SQLAlchemy, Pydantic, NumPy, OpenCV headless; SQLite default; PostGIS **image** in Docker unused as geometry type.

## AI capabilities

DemoVisionModel (mock boxes), optional YOLO, OpenCV water/change detection, weighted risk formulas, rescue if-then rules. **No PyTorch training in repo.** U-Net/DeepLab **not implemented**.

## GIS

Frontend `gisMock` FeatureCollections + API GeoJSON overlays on some pages. Basemap: Carto dark tiles.

## Database

See [DATABASE_GUIDE.md](./DATABASE_GUIDE.md) and [diagrams/database-erd.mmd](./diagrams/database-erd.mmd).

## API

See [API_REFERENCE.md](./API_REFERENCE.md). No auth.

## Frontend

See [FRONTEND_GUIDE.md](./FRONTEND_GUIDE.md). Mock mode can run without backend.

## Demo workflow

Open `/dashboard` → incident → weather → risk → satellite → flood → damage → rescue (accept) → alerts → analytics. Details: [END_TO_END_EXAMPLE.md](./END_TO_END_EXAMPLE.md).

## Real vs mock

Default weather/satellite/vision: **mock/demo**. Risk 82% **simulated overlay**. Flood/damage: **heuristics**. Alerts: **prototype**. OpenWeather/YOLO: **optional**. SMS: **not sent**.

## Known limitations

GIS not bound to API; two flood tables; no login; no Alembic; PDF missing; `ai/` unused by API; PostGIS types unused.

## Future improvements (not implemented)

Trained weights, PostGIS queries, auth, real notify clients, unified GIS from API, Alembic.

## Important files

[IMPORTANT_FILES.md](./IMPORTANT_FILES.md)

## How to run

[RUNNING_THE_PROJECT.md](./RUNNING_THE_PROJECT.md)
