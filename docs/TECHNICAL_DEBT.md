# Technical debt

Documented only — not a commitment that items below are already fixed in code.

## CRITICAL

| Item | Notes |
| --- | --- |
| No authentication | Any client can call mutate endpoints (allocate, ack, generate, AOI change). Fine for a local demo; not for a network-exposed ops system. |
| Dual mock flags | Backend `USE_MOCK_PROVIDERS` and frontend `VITE_USE_MOCK` must both be live (`false` / not `"true"`). If only the UI flag is true, `gisMock` / `mock.ts` appear without hitting the API. |

## HIGH

| Item | Notes |
| --- | --- |
| Seed skip if any disaster exists | Cannot refresh Demo Mode numbers without deleting the DB. Leftover SQLite seed rows may remain after switching to REAL DATA; list APIs hide them. |
| Analytics Demo Mode overwrite | Mock-provider mode forces DEMO KPIs (34.5 / 82 / 42000), hiding OpenCV flood-run values. Live mode must not use those constants. |
| FloodAnalysis vs FloodEvent | Two flood tables; analyze writes `flood_analyses`, seed writes `flood_events`. |
| Vision ↛ rescue | Spec-style pipeline “CV → priority” is not an automatic call chain. |
| Notifications unwired | Flags `ENABLE_REAL_*` still do not send (adapters refuse if “live” is flagged without a client). |
| In-memory alert SSE | Lost on process restart; not multi-worker safe. |
| SQLite in demo | Concurrent writes from reload + tests can lock; no connection pool tuning. |
| IMD empty list | Unconfigured IMD must not be read as “no official warnings”. |
| Dashboard rainfall chart | `fetchAnalytics` maps flood-expansion into a chart titled Rainfall. |

## MEDIUM

| Item | Notes |
| --- | --- |
| Duplicate mock + seed | `frontend/src/data/mock.ts` vs `seed.py` can drift (Demo Mode only). |
| Unused pages | `OverviewPage.tsx`, `RiskPage.tsx`. |
| Duplicate intel stubs | `intel.ts` hard-coded notes / 34.5 km² (not the live dashboard path). |
| No Alembic | Schema drift via ad-hoc SQLite ALTERs. |
| No spatial indexes | JSON geo cannot use PostGIS even if Docker Postgres is up. |
| ultralytics optional undeclared | YOLO path missing → 503 in REAL DATA (DemoVision fallback disabled live). |
| Legacy `src/` | Confusing second weather API if someone runs it on port 8000. |
| CORS allow_credentials + listed origins | Typical demo config; tighten for deploy. |
| File uploads stored locally | No virus scan beyond type/size/magic; paths sanitized by suffix only. |
| GIS live vs demo | Live maps use Overpass (`gis.ts`). `gisMock.ts` is **Demo Mode only**, not the command-map source in REAL DATA. |

## LOW

| Item | Notes |
| --- | --- |
| Chart/map bundle size | Vite warns on large JS chunk. |
| Tests | Backend API tests exist; few frontend component tests; no E2E browser suite in repo. |
| PDF | Stub only. |
| Duplicate API.md vs API_REFERENCE.md | Overlap. |
| `ai/` unused at runtime | Easy to think FastAPI uses it. |

## Scalability / performance

Single-process uvicorn, in-memory Overpass cache, generated rasters per request. Adequate for a demo, not for concurrent emergency load. Overpass 429s fail closed (503).

## Security (demo context)

Secrets belong in `.env` (not committed). OpenWeather / Copernicus / IMD keys optional. No rate limiting. Structured 500s hide traces. SQLAlchemy ORM on routers (no raw user SQL found).

## Live-data limitations (not bugs if labeled)

Copernicus dates are archive acquisitions, not a real-time EO stream. OSM is volunteer mapping (ODbL), not official government GIS. Flood/damage from Sentinel RGB previews are heuristics, not validated flood boundaries or building surveys. No live rescue vehicles, official shelters, river gauges, or census in REAL DATA unless those APIs are actually integrated.
