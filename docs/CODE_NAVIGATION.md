# Code navigation (where to find things)

| Question | Path |
| --- | --- |
| Where is the dashboard? | `frontend/src/pages/DashboardPage.tsx` |
| Where are routes? | `frontend/src/App.tsx` |
| Where is the layout/sidebar? | `frontend/src/layouts/AppLayout.tsx`, `components/Sidebar.tsx` |
| Where is the command map? | `frontend/src/components/DisasterMap.tsx` |
| Where is GIS mock GeoJSON? | `frontend/src/data/gisMock.ts` |
| Where is frontend mock JSON? | `frontend/src/data/mock.ts` |
| Where do I change the API URL? | `frontend/.env` `VITE_API_BASE_URL`; default in `services/apiClient.ts` |
| Where is demo mode for the UI? | `VITE_USE_MOCK` in `frontend/.env`; `isMockMode()` in `apiClient.ts` |
| Where is the weather page? | `frontend/src/pages/WeatherPage.tsx` |
| Where is the weather API? | `GET /api/v1/weather/current` in `backend/app/api/v1/router.py`; `WeatherIntelService` |
| Where is the mock weather? | `backend/app/services/weather/mock_provider.py` |
| Where is OpenWeather? | `backend/app/services/weather/openweather_provider.py`; factory `weather/factory.py` |
| Where is flood risk math? | `backend/app/services/risk/flood.py` |
| Where is the 82% overlay? | `overlay_demo_flood` in `risk/flood.py`; `core/demo.py` |
| Where is flood detection? | UI `pages/FloodPage.tsx`; API `POST /flood/analyze`; `services/flood/service.py` |
| Where is U-Net? | `services/flood/models.py` — raises NotImplementedError |
| Where is YOLO? | `backend/app/services/vision/yolo_model.py`; factory `vision/factory.py` |
| Where is the demo detector? | `vision/demo_model.py` |
| Where is computer vision UI? | `pages/ComputerVisionPage.tsx` |
| Where is satellite analysis? | `services/satellite/service.py`, `processing.py`, `mock_provider.py` |
| Where is damage assessment? | `services/damage/service.py`, `classify.py`; UI `DamagePage.tsx` |
| Where is the rescue plan generated? | `RescuePlanningService.generate_plan` in `services/rescue/service.py` |
| Where are routing rules? | `services/rescue/routing.py`, `recommend.py`, `priority.py` |
| Where are alerts created? | `EarlyWarningService.generate` + `alerts/engine.py` + `alerts/rules.json` |
| Where are notifications? | `alerts/notifications.py` |
| Where is the database model? | `backend/app/models/entities.py` |
| Where is seed/demo data (backend)? | `backend/app/db/seed.py`, `core/demo.py` |
| Where is demo data (frontend)? | `frontend/src/constants/demo.ts`, `data/mock.ts` |
| Where do I add a new disaster type? | Seed/API still use string `disaster_type`; add a `Disaster` row in `seed.py` and UI copy as needed — there is no enum migration |
| Where do I add a new AI model? | Implement protocol (`FloodSegModel` or `VisionModel`) and change `get_flood_model` / `get_vision_model` |
| Where is the UI theme? | `frontend/tailwind.config.js`, `src/styles/index.css` |
| Where is FastAPI created? | `backend/app/main.py` |
| Where are all HTTP routes? | `backend/app/api/v1/router.py` |
| Where is analytics? | `services/analytics/service.py`; UI `AnalyticsPage.tsx` |
| Where is incident command API? | `GET /incidents/{id}` → `incident/service.py` |
| Where is Docker? | `docker-compose.yml`, `docker/backend.Dockerfile`, `docker/frontend.Dockerfile` |
| Where is the leftover NASA API? | `src/app/routes/nasa.py` — not used by the React app |
| Where is the ai/ stub runner? | `ai/inference/runner.py` |
