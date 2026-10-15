# Implementation status (honest)

Default mode is **REAL DATA** (`USE_MOCK_PROVIDERS=false`, frontend mock only if `VITE_USE_MOCK=true`). Primary live AOI is **Karnataka / Bengaluru, India**. Demo Mode (`USE_MOCK_PROVIDERS=true`) still uses the seeded **Kuttanad** case file.

| Feature | Status | Implementation | Real/Mock | File location |
| --- | --- | --- | --- | --- |
| Weather current/forecast | IMPLEMENTED | OpenWeather at selected AOI lat/lon; metric units; fail 503 if no key | LIVE if key set; else NOT_CONFIGURED | `weather/openweather_provider.py`, `live_provider.py` |
| Weather history | IMPLEMENTED | NASA POWER daily; `-999` treated as missing | LIVE (no key) | `weather/nasa_power.py` |
| IMD warnings | PARTIALLY IMPLEMENTED | Optional IMD client; empty/unconfigured is not “no warnings issued” | NOT_CONFIGURED unless key works | `weather/imd_client.py` |
| Satellite | IMPLEMENTED | Copernicus CDSE STAC Sentinel-2 for Karnataka AOI from **1 May 2026**; genuine previews only | LIVE catalogue; MOCK rasters in Demo Mode | `satellite/copernicus_provider.py`, `mock_provider.py` |
| Flood detection | IMPLEMENTED (heuristic) | Live: Sentinel before/after OpenCV water-change. Demo: synthetic rasters. U-Net/DeepLab not implemented | DERIVED_LIVE / Demo MOCK | `flood/service.py`, `processing.py` |
| Computer vision | IMPLEMENTED | YOLO only if local weights; DemoVisionModel **Demo Mode only** | NOT_CONFIGURED live without weights | `vision/factory.py` |
| Damage assessment | IMPLEMENTED (heuristic) | Live Sentinel pair; **no invented building/road inventory** in live | DERIVED_LIVE; SIMULATED mix in Demo Mode | `damage/service.py` |
| Risk prediction | IMPLEMENTED (rules) | Weighted formulas on available live inputs; demo 82% overlay **Demo Mode only** | RULE-BASED | `risk/flood.py`, `cyclone.py` |
| Resource allocation | IMPLEMENTED | DB status update on seeded inventory | SIMULATED Demo Mode; hidden in REAL DATA | `rescue/service.py`, `ops.py` |
| Rescue planning | IMPLEMENTED | Rules + demo graph; live has no vehicle feed | RULE-BASED / UNAVAILABLE live | `rescue/` |
| Alerts | IMPLEMENTED | Engine + DB + in-memory SSE | RULE-BASED; not official warnings | `alerts/` |
| Notifications SMS/email | NOT IMPLEMENTED (wired) | Adapters log mock or refuse | MOCK | `alerts/notifications.py` |
| GIS | IMPLEMENTED | Live: OSM Overpass for selected AOI. Demo: `gisMock.ts` | STATIC_EXTERNAL live; MOCK demo | `gis/overpass.py`, `frontend/src/services/gis.ts` |
| AOI | IMPLEMENTED | Karnataka default; district/point select; Kerala demo bbox rejected | STATIC_EXTERNAL | `geo/aoi.py`, `GET/PUT /gis/aoi` |
| Analytics | IMPLEMENTED | Live: no 34.5/82/42000 substitution; seed hidden | DERIVED_LIVE / SIMULATED demo | `analytics/service.py` |
| Reports | IMPLEMENTED | Live: no silent `DEMO_INCIDENT_ID` / `DEMO_REGION`; AOI-scoped or 503 | JSON only; PDF stub | `reports/service.py` |
| Database | IMPLEMENTED | SQLite/Postgres URL; JSON geo | REAL local DB; PostGIS types unused | `models/entities.py` |
| Auth / roles | NOT IMPLEMENTED | User row in seed only | — | `entities.User` |
| Alembic | NOT IMPLEMENTED | README only | — | `db/migrations/README.md` |
| PDF reports | NOT IMPLEMENTED | `to_pdf` returns None | — | `reports/service.py` |
| NASA/NOAA live (legacy) | Specified in `src/` | Not mounted on product FastAPI | NOT CONNECTED to UI | `src/app/routes/` |
| ai/ stubs | IMPLEMENTED as tests | Not used at runtime by backend | MOCK | `ai/` |
| Docker Compose | IMPLEMENTED as files | Requires Docker engine | — | `docker-compose.yml` |

Statuses: IMPLEMENTED, PARTIALLY IMPLEMENTED, MOCK, SIMULATED, NOT IMPLEMENTED, DERIVED_LIVE, STATIC_EXTERNAL, NOT_CONFIGURED, UNAVAILABLE.
