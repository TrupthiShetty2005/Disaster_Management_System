# Database guide

## Technology

**Observed implementation:** SQLAlchemy 2.x models in `backend/app/models/entities.py`. Engine in `app/db/session.py`.

**Default URL:** `sqlite:///./visionguard.db` (`Settings.database_url`). Tests often use `sqlite:///./test_visionguard.db`.

**Docker Compose** defines a **PostGIS** image (`postgis/postgis:16-3.4`) and a Postgres URL for the backend container. The Python models store geography as **JSON GeoJSON**, not PostGIS `Geometry` columns. Spatial SQL (`ST_Intersects`, etc.) is **not currently implemented**.

## Connection

`create_engine(settings.database_url)`. SQLite: `connect_args={"check_same_thread": False}`. Sessions: `SessionLocal` / `get_db()`.

## Migrations

**Specified but not currently implemented:** Alembic. `init_db()` uses `create_all` plus manual `ALTER TABLE` helpers for SQLite columns added after the first table create.

## Indexes

**Not currently implemented** as SQLAlchemy `Index()` on models. Primary keys only (`String(36)`). `User.email` is `unique=True`.

## Relationships

See [diagrams/database-erd.mmd](./diagrams/database-erd.mmd).

- `Location` is the geographic parent for disasters, weather, satellite, assets, many alerts.
- `Disaster` parents flood_events, damage_assessments, rescue_priorities, rescue_plans.
- `SatelliteImage` → `ImageAnalysisResult` → `DetectedObject`.
- `User` optionally parents `AuditLog.actor_id`.
- `FloodAnalysis` and `DamageReport` / `VisionJob` are analysis result tables without FK to disaster in the model (flood analyze does not set `disaster_id` on `FloodAnalysis`).

## Spatial fields

JSON columns named `geojson`, `bbox_geojson`, `result_geojson`, `boundary_geojson`, `heatmap_geojson`, `overlay_geojson`. Coordinates in seed data are lon/lat WGS84-style numbers around Kerala (9.517, 76.522).

## Seed data

`backend/app/db/seed.py` / `python scripts/seed_demo_data.py`.

If `Disaster` count > 0, seed **returns without inserting**.

Canonical flood: id `aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa`, location `11111111-1111-4111-8111-111111111111` Kuttanad. Also seeds landslide and cyclone **demo** disasters, risk zones, weather rows, satellite stub, flood event 34.5 km², one damage row, roads (including blocked), buildings, resources, shelters, priority, alerts, user, audit seed row.

IDs also listed in `app/core/demo.py` and `frontend/src/constants/demo.ts`.
