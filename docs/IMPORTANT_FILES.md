# Important source files

Ranked by how much of the product they define.

| Rank | File | What it does | Why it matters | Connected to |
| --- | --- | --- | --- | --- |
| 1 | `backend/app/api/v1/router.py` | All `/api/v1` routes | HTTP surface | Every service |
| 2 | `backend/app/main.py` | App, CORS, seed on boot | Process entry | config, init_db |
| 3 | `frontend/src/App.tsx` | Routes | UI surface | pages |
| 4 | `backend/app/models/entities.py` | Tables | Data model | seed, services |
| 5 | `frontend/src/services/apiClient.ts` | fetch + mock switch | All API calls | services/* |
| 6 | `backend/app/db/seed.py` | Demo incident | Consistent IDs | demo.py, frontend constants |
| 7 | `backend/app/core/config.py` | Env | Mock vs live, DB URL | factory classes |
| 8 | `backend/app/core/demo.py` | Canonical KPIs/IDs | Demo consistency | analytics overlay |
| 9 | `frontend/src/constants/demo.ts` | Same IDs in UI | Incident bar/links | Dashboard |
| 10 | `frontend/src/pages/DashboardPage.tsx` | Home screen | First demo impression | map, KPIs |
| 11 | `frontend/src/components/DisasterMap.tsx` | Command GIS | Map UX | gisMock |
| 12 | `frontend/src/data/gisMock.ts` | Map GeoJSON | Layers without API | DisasterMap |
| 13 | `backend/app/services/weather_intel.py` | Weather+risk facade | Precaution path | flood overlay |
| 14 | `backend/app/services/risk/flood.py` | Risk formula + 82% overlay | “AI risk” honesty | Risk API |
| 15 | `backend/app/services/weather/factory.py` | Mock vs OpenWeather | Live weather gate | providers |
| 16 | `backend/app/services/satellite/service.py` | Scene analyze | Satellite feature | processing.py |
| 17 | `backend/app/services/satellite/processing.py` | Rasters and masks | Shared flood/damage pixels | flood, damage |
| 18 | `backend/app/services/flood/service.py` | Flood analyze persist | Flood feature | DemoFloodModel |
| 19 | `backend/app/services/vision/pipeline.py` | CV job | Vision feature | demo_model |
| 20 | `backend/app/services/vision/demo_model.py` | Fake detections | Default CV | factory |
| 21 | `backend/app/services/damage/service.py` | Damage JSON | Recovery feature | classify.py |
| 22 | `backend/app/services/rescue/service.py` | Plans and decisions | Response feature | routing, recommend |
| 23 | `backend/app/services/alerts/engine.py` | Alert fusion | Early warning | rules.json |
| 24 | `backend/app/services/alerts/service.py` | Generate/ack/resolve | Alert API | notifications |
| 25 | `backend/app/services/analytics/service.py` | KPIs | Analytics | demo constants |
| 26 | `backend/app/services/incident/service.py` | Combined incident | Command page | many models |
| 27 | `frontend/src/data/mock.ts` | Offline UI data | VITE_USE_MOCK | services |
| 28 | `backend/app/schemas/common.py` | JSON contracts | Client/server shape | router |
| 29 | `backend/app/db/init_db.py` | create_all | Schema without Alembic | models |
| 30 | `frontend/src/layouts/AppLayout.tsx` | Chrome | Every page | Sidebar |
| 31 | `backend/app/services/vision/yolo_model.py` | Optional YOLO | Honesty about COCO | factory |
| 32 | `backend/app/services/alerts/notifications.py` | Mock notify | No real SMS | engine |
| 33 | `docker-compose.yml` | Infra | Optional stack | Dockerfiles |
| 34 | `frontend/src/pages/RescuePage.tsx` | Rescue UX | Human-in-loop | rescue APIs |
| 35 | `scripts/seed_demo_data.py` | CLI seed | Repeatable demo | seed.py |
