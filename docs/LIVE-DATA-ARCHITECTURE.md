# VisionGuard Live Data Architecture

## Modes

| Mode | Backend | Frontend | Silent mock fallback? |
| --- | --- | --- | --- |
| **LIVE DATA MODE** | `USE_MOCK_PROVIDERS=false` | `VITE_USE_MOCK=false` | **No** — providers return 503 / UNAVAILABLE |
| **DEMO MODE** | `USE_MOCK_PROVIDERS=true` | `VITE_USE_MOCK=true` | Yes — mocks/seeds allowed and labeled |

## Provider → service → API → UI

```
OpenWeather / NASA POWER / Copernicus / Overpass / (optional IMD)
        ↓
  Provider adapters (httpx)
        ↓
  Domain services (weather_intel, satellite, flood, damage, gis, alerts)
        ↓
  Provenance layer (app/services/provenance.py)
        ↓
  FastAPI /api/v1/*
        ↓
  React pages + ModuleProvenance / DataSourceBadge
```

## Docker LIVE deployment

```bash
cp .env.live.example .env.live
# edit .env.live — set OPENWEATHER_API_KEY at minimum

docker compose --env-file .env.live -f docker-compose.yml -f docker-compose.live.yml up --build
```

Health:

- `GET /api/v1/health`
- `GET /api/v1/data-sources/status?probe=true`

Startup logs print a non-secret LIVE/DEMO banner (`log_live_startup_banner`).

## Module status vocabulary

| Status | Meaning |
| --- | --- |
| LIVE | External API called successfully |
| DERIVED_LIVE | Computed from live inputs (heuristics/rules) |
| STATIC_EXTERNAL | Authoritative reference dataset (e.g. OSM), not real-time telemetry |
| SEEDED | Application DB demo inventory |
| MOCK | Synthetic / demo provider |
| UNAVAILABLE | Live path failed |
| NOT_CONFIGURED | Credentials/flags missing |

## Important honesty rules

- Flood analysis = **REAL SENTINEL DATA — HEURISTIC ANALYSIS** (not “AI flood detection”).
- VisionGuard risk ≠ IMD official warning.
- River level = **UNAVAILABLE** (not invented).
- Resources/incidents = **SEEDED** application data.
- Notifications = **MOCK** (clients unwired).

## Environment variables (live)

See `.env.live.example` and root `.env.example`. Never commit secrets.
