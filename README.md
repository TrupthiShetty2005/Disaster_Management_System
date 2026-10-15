# VisionGuard AI — Karnataka live disaster monitoring

A disaster-monitoring console for **Karnataka, India**, built only on live public data. It predicts **river flooding**, detects and forecasts **fire**, maps flood water and burn scars from **real Sentinel satellite imagery**, and estimates **infrastructure losses** from OpenStreetMap. Every number comes from a live feed at request time. If a source is down, the affected panel says so.

## What it does

| Area | Live source | What the app computes |
| --- | --- | --- |
| **Water levels** | Copernicus **GloFAS v4** river discharge via Open-Meteo Flood API | Daily discharge at 16 Karnataka dams/gauges + 30-day ensemble forecast. Flood thresholds (2/5/20-year return levels) are fitted per river cell from its June–November maxima since 2005 (Gumbel). Status: NORMAL / WATCH / WARNING / SEVERE, now and predicted. |
| **Rainfall** | **Open-Meteo** forecast + recent observations, **OpenWeather** current weather | 30-day observed and 7-day forecast rain for all 31 districts, classified with IMD 24-hour categories. |
| **Fire** | **NASA FIRMS** VIIRS (S-NPP, NOAA-20, NOAA-21) + MODIS near-real-time | Detections clipped to the Karnataka boundary, clustered into fire events (2 km). Persistent industrial heat sources such as steel plants are recognised and excluded. 7-day **fire-danger forecast** (Fosberg FFWI) per district. |
| **Satellite** | **Sentinel-1 RTC** and **Sentinel-2 L2A** from Microsoft Planetary Computer | Flood mapping: SAR VV backscatter change, or optical NDWI. Burn scars: dNBR with USGS severity classes. Outputs georeferenced polygons, before/after/change images, and the exact scene IDs used. |
| **Infrastructure losses** | **OpenStreetMap** (Overpass) | Satellite/FIRMS footprint × buildings, roads (by class), railways, power lines and critical facilities. Losses use configurable unit costs × damage ratio, and every assumption is returned with the result. |
| **Alerts** | All of the above + **GDACS** | Raised automatically every 30 min when a live value crosses a threshold. Alerts escalate, auto-resolve when the condition clears, expire, and stream to the browser via server-sent events. |
| **Rescue planning** | OpenStreetMap facilities + **OSRM** routing | Nearest hospitals, fire stations and police stations, ranked by real road drive time. |
| **Computer vision** | YOLOv8n (Ultralytics, COCO) | Counts people, vehicles, boats and animals in uploaded drone/field photos. |

Only OpenWeather needs an API key. Every other source is free and keyless.

## Run with Docker

From a fresh clone, with Docker Desktop or Docker Engine and Compose v2:

```bash
docker compose up --build
```

Then open the app at [http://localhost:5173](http://localhost:5173). The API is at [http://localhost:8000](http://localhost:8000) (docs at [http://localhost:8000/docs](http://localhost:8000/docs)).

The OpenWeather key is already in `backend/.env`. Anyone who can read this repository can see that key. The image also includes the SQLite database, satellite analysis images, the vision gallery photos and videos, and the YOLOv8n weights, so existing analyses and the gallery are there on first start. New analyses are written to the `visionguard_data` volume. `docker compose down -v` drops that volume; the next start copies the baked-in data again.

Reference downloads (district boundaries, facilities, river thresholds) are cached under `storage/cache` and are not in git. The first start rebuilds that cache from the live sources.

## Run locally

Backend (Python 3.11):

```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
# backend/.env is already in the repo (OpenWeather key included)
uvicorn app.main:app --port 8000
```

Frontend (Node 20+):

```bash
cd frontend
npm install
echo "VITE_API_BASE_URL=http://127.0.0.1:8000" > .env
npm run dev                    # http://localhost:5173
```

On first start the backend downloads reference data in the background and caches it on disk under `backend/storage/cache`:

- Karnataka and district boundaries (OSM Nominatim, ~35 s)
- Statewide emergency facilities (Overpass, ~1 min)
- 20 years of seasonal discharge maxima for the 16 river stations

River status shows `CALIBRATING` until a station's thresholds are ready.

## API

Interactive docs are at `http://localhost:8000/docs`. Main routes under `/api/v1`:

- `GET /overview`, `/sources`, `/geo/karnataka`, `/geo/districts`, `/geo/stations`
- `GET /water/stations`, `/water/stations/{id}`
- `GET /rainfall/districts`, `/weather/{district_id}`
- `GET /fire/detections?window=24h|48h|7d`, `/fire/clusters`, `/fire/danger`, `POST /impact/fire-cluster`
- `GET /events` (GDACS)
- `GET /satellite/scenes`, `/satellite/preview`, `POST /satellite/analyze`, `GET /analyses[/{id}]`
- `GET /alerts`, `POST /alerts/refresh`, `POST /alerts/{id}/acknowledge|resolve`, `GET /alerts/stream` (SSE)
- `GET /analytics`, `/rescue/plan?lat=&lon=`
- `GET /vision/status`, `POST /vision/detect`, `GET /vision/jobs`

When an upstream source fails, the API returns `503 {"error": "source_unavailable", "source": "...", "detail": "..."}`. It never substitutes made-up values.

## Tests

```bash
cd backend && pytest                 # unit tests (offline)
cd backend && pytest -m integration  # hits the real FIRMS, GloFAS, Open-Meteo, Planetary Computer, GDACS
cd frontend && npm test && npm run lint && npm run build
```

## Limits worth knowing

- GloFAS is a hydrological model at ~5 km resolution, not a gauge reading. Thresholds are relative to the model's own climatology, which is the standard way GloFAS flood signals are issued.
- Satellite flood maps compare two acquisition dates. A reservoir filling up after the monsoon appears as "newly flooded" relative to the dry-season baseline.
- Loss figures are indicative planning estimates (exposure × unit cost × damage ratio), not surveyed damage.
- Public Overpass/OSRM servers are rate-limited. Large urban footprints can take a minute or be temporarily unavailable.
- This is a student project, not an official warning service. Follow KSNDMC/IMD/district administration advisories.
