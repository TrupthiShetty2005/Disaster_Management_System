# VisionGuard AI — Architecture

VisionGuard AI is a computer-vision disaster management and decision-support prototype covering **precaution**, **response**, and **recovery**. This repository is a **working foundation**: APIs, GIS-ready models, a situation dashboard, and **pluggable** AI/data providers. Live models, satellite feeds, and government systems are **not assumed**; mock adapters run until credentials exist.

## System context

```
┌─────────────┐     REST / JSON      ┌──────────────────┐     SQL / GeoJSON      ┌─────────────────┐
│ React SPA   │ ◄──────────────────► │ FastAPI /api/v1  │ ◄───────────────────► │ PostgreSQL      │
│ Vite + TS   │                      │ services/repos   │                       │ + PostGIS later │
└─────────────┘                      └────────┬─────────┘                       └─────────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
             ┌─────────────┐         ┌────────────────┐        ┌────────────────┐
             │ Weather     │         │ Satellite /    │        │ AI inference   │
             │ providers   │         │ GIS adapters   │        │ (ai/) stubs    │
             └─────────────┘         └────────────────┘        └────────────────┘
```

Legacy weather/NASA/NOAA code under `src/` is **not** the product API. New clients use `backend/` only. Existing provider functions can later wrap into `backend/app/services/providers/`.

## Frontend architecture

- **Vite + React + TypeScript + Tailwind**
- Pages map 1:1 to primary navigation plus **Incident command** (`/disasters/:id`) as the central picture
- Shared demo incident ID: Kuttanad flood `aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa`
- **No API calls in UI components** — `src/services/*` + `src/services/apiClient.ts`
- Map: React Leaflet; charts: Chart.js
- Mock fallback when `VITE_USE_MOCK=true` or the API is unreachable

## Backend architecture

Layered FastAPI app (`/api/v1`):

| Layer | Path | Role |
|-------|------|------|
| API | `app/api/v1` | HTTP, validation |
| Schemas | `app/schemas` | Pydantic I/O |
| Services | `app/services` | Orchestration |
| Repositories | `app/repositories` | Persistence |
| Models | `app/models` | SQLAlchemy |
| Core | `app/core` | config, logging, errors, CORS |

## Database architecture

PostgreSQL is the system of record. Geometry is stored as **GeoJSON JSON** in v1 so local SQLite tests work; columns and types are **PostGIS-compatible** (swap JSON → `Geometry` without changing API contracts). MongoDB is optional future only.

## AI service architecture

`ai/` holds preprocessing, inference interfaces, and postprocessing. Runtime uses **stub detectors** returning deterministic demo detections. Real YOLO/segmentation models plug in behind the same interfaces.

## GIS architecture

- GeoJSON FeatureCollections on map layers
- `/rescue-planning` — inventory, priorities, demo graph routes, human override (accept/modify/reject)
- Road accessibility and building damage classes come from prototype change detection, not a trained damage net

## Docker

`docker-compose.yml` runs Postgres, backend, and frontend. See [DEVELOPMENT.md](./DEVELOPMENT.md).
