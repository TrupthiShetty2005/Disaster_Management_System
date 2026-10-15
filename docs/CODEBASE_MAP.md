# Codebase map

```
Disaster_Management_System/
├── frontend/          React ops console (product UI)
├── backend/           FastAPI /api/v1 (product API)
├── ai/                Stub package; not imported by FastAPI
├── src/               Legacy FastAPI NASA/NOAA/OpenWeather; not the dashboard API
├── docs/              Architecture and this documentation set
├── scripts/           Seed wrappers
├── data/mock/         Text placeholder for satellite demo path
├── docker/            Dockerfiles
├── docker-compose.yml Postgres + backend + frontend
├── README.md
└── prompts            Cursor prompt history (not runtime)
```

## frontend/src

| Folder | Responsibility |
| --- | --- |
| `pages/` | Route screens |
| `components/` | Shared UI and maps |
| `services/` | HTTP and mock adapters |
| `data/` | mock.ts, gisMock.ts |
| `hooks/` | useAsync, alert stream |
| `layouts/` | Shell |
| `constants/` | Demo IDs |
| `types/` | TS types |
| `styles/` | Tailwind entry |

## backend/app

| Folder | Responsibility |
| --- | --- |
| `api/v1/` | HTTP |
| `services/` | Domain logic |
| `models/` | ORM |
| `schemas/` | Pydantic |
| `repositories/` | Simple queries |
| `db/` | engine, seed, init |
| `core/` | config, errors, demo IDs |

## ai/

| Folder | Responsibility |
| --- | --- |
| `inference/` | `run_stub_pipeline` |
| `services/` | Stub flood/damage/vision protocols |
| `preprocessing/` | Tiny numpy raster stub |
| `postprocessing/` | Empty GeoJSON stub |
| `models/` | README only (no weights) |

## src/

Older weather/NASA/NOAA API. Independent of `backend/app/main.py`.
