# Backend guide

Entry: `backend/app/main.py`.

`FastAPI(..., lifespan=lifespan)`:

1. `configure_logging()` (`app/core/logging.py`)
2. `init_db()` — `Base.metadata.create_all` plus SQLite column adders (`app/db/init_db.py`)
3. `seed_if_empty()` (`app/db/seed.py`)

Middleware: `CORSMiddleware` with `settings.cors_origin_list`.  
Handlers: `register_exception_handlers` — HTTP and generic 500 without stack traces.  
Router: `app.include_router(api_router, prefix=settings.api_v1_prefix)` → `/api/v1`.

Config: `app/core/config.py` Pydantic Settings, `.env` from cwd.  
DB session: `app/db/session.py` `create_engine(settings.database_url)`. SQLite gets `check_same_thread=False`.

**Authentication:** Specified in some product visions as roles; **not currently implemented** as login/JWT. A `User` table exists for seed (`ops.demo@visionguard.local`) and optional `AuditLog.actor_id`.

**Alembic:** `app/db/migrations/README.md` — not used; schema is `create_all`.

## Module table

| Module | Location | Responsibility |
| --- | --- | --- |
| API | `app/api/v1/router.py` | HTTP endpoints |
| Schemas | `app/schemas/common.py` | Request/response models |
| Config / demo IDs | `app/core/config.py`, `demo.py` | Env and canonical Kuttanad IDs |
| Errors / logging | `app/core/errors.py`, `logging.py` | JSON errors, log format |
| ORM | `app/models/entities.py` | Tables |
| Repositories | `app/repositories/ops.py` | Disaster, zone, weather, alert, resource, evacuation CRUD-ish reads |
| Ops services | `app/services/ops.py` | Disaster, Risk explain, Weather, Resource, Evacuation |
| Weather intel | `app/services/weather_intel.py` | Provider + flood/cyclone/rainfall |
| Weather adapters | `app/services/weather/` | Mock vs OpenWeather factory |
| Risk math | `app/services/risk/` | Flood/cyclone/rainfall/pipeline |
| Satellite | `app/services/satellite/` | Catalog, rasters, analyze |
| Vision | `app/services/vision/` | Upload pipeline |
| Flood | `app/services/flood/` | Demo segmentation |
| Damage | `app/services/damage/` | Change detection report |
| Rescue | `app/services/rescue/` | Priority, recommend, routing, plan |
| Alerts | `app/services/alerts/` | Engine, rules.json, notifications, SSE |
| Analytics | `app/services/analytics/service.py` | KPIs and CSV |
| Incident | `app/services/incident/service.py` | Combined picture |
| Reports | `app/services/reports/service.py` | JSON; PDF None |
| Seed | `app/db/seed.py` | Demo rows |

See [API_REFERENCE.md](./API_REFERENCE.md) for every route.
