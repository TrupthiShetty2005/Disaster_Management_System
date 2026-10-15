# VisionGuard AI — Real API Integration

This document describes the **live external data** integrations. **Real Data Mode is the default development/test path.** Demo Mode exists only as an explicit fallback (`USE_MOCK_PROVIDERS=true` / `VITE_USE_MOCK=true`) and must never be used silently when live providers fail.

## Mode switch

| Setting | Meaning |
| --- | --- |
| `USE_MOCK_PROVIDERS=false` (default) | **REAL DATA** — OpenWeather + NASA POWER + Copernicus STAC (+ optional IMD). Failures return `503 provider_unavailable` — **no** mock weather, synthetic rasters, or hard-coded 82% / 34.5 km² |
| `USE_MOCK_PROVIDERS=true` | **DEMO DATA** (explicit fallback only) — `MockWeatherProvider`, synthetic satellite rasters, canonical demo KPIs |

Frontend: `VITE_USE_MOCK=false` (default in `.env.example`) calls the backend and **does not** catch-and-swap to `mock.ts`. Set `VITE_USE_MOCK=true` only for offline Demo Mode.

Header / SafetyBanner show **DEMO DATA** or **REAL DATA** via `GET /api/v1/data-sources`.

---

## APIs integrated

### 1. OpenWeather (current + forecast)

| Item | Detail |
| --- | --- |
| Used for | Current temperature, humidity, pressure, wind, rainfall, conditions; 3-hour forecast |
| Provider class | `OpenWeatherProvider` / `LiveWeatherProvider` |
| Endpoints | `api.openweathermap.org/data/2.5/weather`, `/forecast` |
| Query | `OPENWEATHER_QUERY` (default `Alappuzha,IN`) |
| Key | `OPENWEATHER_API_KEY` **required** in real mode |
| Status if missing | `503 provider_unavailable` — **does not** invent mock numbers in real mode |

**Test status:** Implementation verified. Live value fetch **not completed in this environment** because `OPENWEATHER_API_KEY` is empty in local `.env`.

### 2. NASA POWER (historical meteorology)

| Item | Detail |
| --- | --- |
| Used for | Daily history: rainfall (`PRECTOTCORR`), temperature (`T2M`), humidity (`RH2M`), wind (`WS2M`); anomaly / short-term rainfall risk |
| Provider class | `NasaPowerClient` → `LiveWeatherProvider.history` |
| Endpoint | `https://power.larc.nasa.gov/api/temporal/daily/point` |
| Key | **None** |
| AOI | `DEMO_LATITUDE` / `DEMO_LONGITUDE` (Kuttanad 9.517, 76.522) |

**Test status:** **Completed** — HTTP 200, parameters returned for Kuttanad (`pytest` integration + manual probe).

### 3. IMD (India Meteorological Department)

| Item | Detail |
| --- | --- |
| Used for | Official district warnings when a valid token is configured (`ImdClient.district_warnings`) |
| Base URL | `https://api.imd.gov.in/api/v1` |
| Key | `IMD_API_KEY` (JWT / portal credential) |
| Without key | Status reports **unavailable**; **no fake IMD data** is generated |

**Test status:** Official API probed → `401 API key missing` without credentials. Client implemented; **live IMD products not completed** without an IMD-issued token.

### 4. Copernicus Data Space — Sentinel STAC

| Item | Detail |
| --- | --- |
| Used for | Sentinel-2 L2A + Sentinel-1 GRD catalogue over Kuttanad AOI; acquisition time, platform, cloud cover, source; thumbnail preview |
| Provider class | `CopernicusStacProvider` |
| STAC URL | `COPERNICUS_STAC_URL` (default `https://stac.dataspace.copernicus.eu/v1`) |
| OAuth | Optional `COPERNICUS_CLIENT_ID` / `COPERNICUS_CLIENT_SECRET` for protected assets |
| Label | **Latest Available Satellite Imagery** (not “live stream”) |

**Test status:** **Completed** for catalogue search + thumbnail download (HTTP 200, real JPEG bytes) without OAuth. Full SAFE/JP2 product download may still need CDSE OAuth / S3 credentials.

---

## Weather data flow (real mode)

```text
Weather / Risk / Dashboard
  → LiveWeatherProvider
      → OpenWeather current + forecast   (needs key)
      → NASA POWER history               (no key)
      → IMD alerts                       (optional key)
  → WeatherIntelService.flood / rainfall / cyclone
      → rule-based scores (no 82% overlay when mock is off)
```

## Satellite data flow (real mode)

```text
Satellite / Compare / Flood Detection
  → CopernicusStacProvider.refresh()
      → STAC POST /search (bbox + datetime + cloud filter)
      → sync into satellite_images (stable UUID from STAC id)
  → preview via /api/v1/satellite/images/{id}/preview
      → fetch STAC thumbnail href (JPEG)
  → analyze / compare
      → OpenCV heuristic on real preview pixels
      → labeled as latest-available + heuristic (not trained U-Net)
```

---

## Features using real data (when `USE_MOCK_PROVIDERS=false` and keys present)

| Feature | Real inputs |
| --- | --- |
| `/weather` current/forecast | OpenWeather |
| `/weather` history + rainfall anomaly | NASA POWER |
| `/weather` IMD alert list | IMD (if key works) |
| `/risk-intelligence` scores | Live weather + NASA-driven factors (population profile still seeded) |
| `/dashboard` weather card | OpenWeather when available |
| `/satellite` catalogue + preview | Copernicus STAC + thumbnails |
| `/satellite/compare` | Two latest-available STAC scenes |
| `/flood-detection` Run | OpenCV on Sentinel-2 preview (if STAC available) |
| `/api/v1/data-sources` | Live status of each provider |

## Features that remain mock / demo / heuristic

| Feature | Status |
| --- | --- |
| Command map GIS (`gisMock.ts`) | Static demo GeoJSON |
| Canonical KPIs 82% / 34.5 / 42000 / 18 / 3 | **Demo Mode only** (not forced in real analytics) |
| Seeded disasters / resources / population | Demo inventory |
| Flood/damage “AI” | OpenCV / rules — not trained U-Net |
| `DemoVisionModel` | Still demo unless local YOLO weights configured |
| Rescue routing graph | Demo graph |
| Email/SMS/push | Still mock / unwired |
| Authentication | Not implemented |

---

## Setup

1. Copy `.env.example` → `.env` (and `frontend/.env.example` → `frontend/.env`).
2. Set `USE_MOCK_PROVIDERS=false`.
3. Set `OPENWEATHER_API_KEY=...` for current/forecast.
4. Optionally set `IMD_API_KEY`, `COPERNICUS_CLIENT_ID`, `COPERNICUS_CLIENT_SECRET`.
5. Frontend: `VITE_USE_MOCK=false`.

```powershell
cd backend
..\venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir .
```

```powershell
cd frontend
npm run dev
```

Check:

- http://127.0.0.1:8000/api/v1/health  
- http://127.0.0.1:8000/api/v1/data-sources  
- http://127.0.0.1:5173/weather  

Integration tests (network):

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest tests/test_real_providers.py -q
```

---

## Limitations

1. OpenWeather history API is paid — history uses **NASA POWER** instead.
2. River gauges are not provided by OpenWeather; risk formula uses a transparent rainfall-based proxy in real mode.
3. IMD requires an official portal credential; without it IMD stays unavailable (by design).
4. Copernicus full-resolution JP2/SAFE download is not wired; UI shows **thumbnails** + metadata.
5. Satellite analyze/flood masks are **heuristics on previews**, not production EO models.
6. GIS command map is still frontend `gisMock` — not live PostGIS.
7. Do not call latest STAC scenes “live”; the product label is **Latest Available Satellite Imagery**.
