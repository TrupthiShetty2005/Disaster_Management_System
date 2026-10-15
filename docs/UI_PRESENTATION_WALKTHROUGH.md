# VisionGuard UI — Full Presentation Walkthrough

Present **top to bottom**: shell → each sidebar page.  
Assume **LIVE DATA MODE** (`frontend/.env`: `VITE_USE_MOCK=false`, backend `USE_MOCK_PROVIDERS=false`).

**Switch rule (say once):**  
If `VITE_USE_MOCK` is not exactly `false`, every `frontend/src/services/*.ts` file returns data from `frontend/src/data/mock.ts` and **does not call** FastAPI.  
Mode check: `frontend/src/services/apiClient.ts` → `isMockMode()`.

---

## 0) Shared shell (every page)

| UI piece | Function | Data | Code |
| --- | --- | --- | --- |
| Sidebar | Navigation | Links only; Incident uses fixed demo ID | `frontend/src/components/Sidebar.tsx` |
| Header | Brand + **LIVE / DEMO** badge + alert count | Badge from `/api/v1/data-sources/status` | `Header.tsx`, `DataModeBadge.tsx` |
| Incident bar | Pins Kuttanad flood scenario | **Constants** (same ID as DB seed) | `IncidentBar.tsx`, `constants/demo.ts` |
| Safety + provenance panel | Honesty labels per module | Live probe API | `AppLayout.tsx`, `SafetyBanner.tsx`, `DataModeBadge.tsx` → `GET /api/v1/data-sources/status` |
| Routes | Which page loads | — | `App.tsx` |

**Always-demo IDs (not “fake weather” — fixed scenario keys):**

```
frontend/src/constants/demo.ts
backend/app/db/seed.py   (same UUID: aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa)
```

---

## 1) Command dashboard — `/dashboard`

**Say:** “This is the command overview: active disasters, alerts, people at risk, flooded area, resources, weather strip, and a map.”

| What you see | Function | LIVE mode data | MOCK mode data | Code path |
| --- | --- | --- | --- | --- |
| KPI cards | Big numbers | Disasters/alerts/resources from **seeded DB**; flooded/damage from analytics (may mix flood runs); weather tile **LIVE OpenWeather** | `mock.ts` + `DEMO_STATS` | Page: `DashboardPage.tsx` · FE: `disasters.ts`, `ops.ts`, `weather.ts`, `analytics.ts`, `intel.ts` · BE: `router.py` + services |
| Map layers | Flood/risk/roads polygons | **Catalog always from `gisMock.ts`** (`fetchGisCatalog`) | Same `gisMock` | `gis.ts` → `data/gisMock.ts` · Map: `DisasterMap.tsx` |
| Alert list | Recent alerts | Seeded + generated alerts in DB | `mockAlerts` | `ops.ts` / `alerts.ts` → `EarlyWarningService` |
| Charts | Trends | Analytics overview API | `mockAnalytics` | `DashboardCharts.tsx` |

**Present clearly:** Map **story polygons** = frontend demo GeoJSON. Weather number = can be live. Population/resources = seeded demo inventory.

---

## 2) Incident command — `/disasters/:id`

**Say:** “One unified flood story for Kuttanad so every module stays on the same incident.”

| What | Data | Code |
| --- | --- | --- |
| Incident picture / summary | LIVE: API incident aggregate · MOCK: `mockDisasters` | `DisasterDetailPage.tsx` → `services/incident.ts` → `GET /api/v1/incidents/{id}` · Seed: `db/seed.py` |

---

## 3) Risk Intelligence — `/risk-intelligence`

**Say:** “High-risk zones on a map for planning.”

| What | LIVE | MOCK | Code |
| --- | --- | --- | --- |
| Risk zones table/map | DB risk zones (**seeded**) | `mockRiskZones` | `RiskIntelligencePage.tsx` → `services/risk.ts` → `GET /api/v1/risk-zones` |
| Map catalog | Always `gisMock` catalog | same | `fetchGisCatalog` → `gisMock.ts` |

Flood/cyclone **% scores** live on Weather page (rule-based from live weather) — Risk Intelligence page is mainly zone list + map.

---

## 4) Live Situation — `/situation`

**Say:** “Situation awareness: OSM reference features + demo catalog + incident list.”

| What | LIVE | MOCK | Code |
| --- | --- | --- | --- |
| OSM / Overpass features | **STATIC_EXTERNAL** live Overpass | `gisMock` features | `SituationPage.tsx` → `fetchGisWithProvenance` → `GET /api/v1/gis/features` · BE: `services/gis/overpass.py` |
| Catalog layer names | Always `gisMock` | same | `fetchGisCatalog` |
| Disasters table | **SEEDED** DB | `mockDisasters` | `fetchDisasters` → `DisasterService` |
| Provenance cards | GIS + incidents badges | FE-only mock panel | `ModuleProvenance` |

---

## 5) Flood Detection — `/flood-detection`

**Say:** “Press Run. We take two real Sentinel-2 preview images and measure water change. Heuristic — not U-Net.”

| What | LIVE | MOCK | Code |
| --- | --- | --- | --- |
| Run analysis | **DERIVED_LIVE** from Copernicus previews | Local mock flood object in `flood.ts` | FE: `FloodPage.tsx` → `services/flood.ts` → `POST /api/v1/flood/analyze` · BE: `services/flood/service.py` → `satellite/processing.compare_water_change` |
| Scene list / events | Stored flood events + live scenes | mock list | `GET /flood/events` |
| Scenario callout (34.5 km² etc.) | **DEMO_STATS** reference strip (simulated scenario numbers) | same constants | `constants/demo.ts` shown on page |
| Provenance | `flood_analysis` + `satellite` | — | `ModuleProvenance` |

**Point in code when asked:**  
`backend/app/services/satellite/processing.py` → `compare_water_change`  
`backend/app/services/flood/service.py` → `analyze`

---

## 6) Damage Assessment — `/damage-assessment`

**Say:** “Same EO change idea → severity labels for buildings/roads. Not a trained damage neural net.”

| What | LIVE | MOCK | Code |
| --- | --- | --- | --- |
| Run damage | **DERIVED_LIVE** | mock assessment in `damage.ts` | `DamagePage.tsx` → `services/damage.ts` → `POST /api/v1/damage/analyze` · BE: `services/damage/service.py`, `damage/classify.py` |
| Before/after thumbs | Copernicus preview URLs | mock images | `services/satellite.ts` |

---

## 7) Weather — `/weather`

**Say:** “Live weather for Alappuzha, history from NASA, risk % calculated by our rules — not IMD.”

| Block | LIVE | MOCK | FE service | Backend |
| --- | --- | --- | --- | --- |
| Current / forecast | **LIVE** OpenWeather | `mockWeather`, `mockForecast` | `weather.ts` | `weather_intel.py`, `weather/openweather_provider.py` / `live_provider.py` |
| History | **LIVE** NASA POWER | `mockHistory` | `weather.ts` | `weather/nasa_power.py` |
| Rainfall / flood risk / cyclone | **DERIVED_LIVE** rules | mock risk objects | `weather.ts` | `services/risk/*.py` |
| Weather alerts panel | Mix / engine | mock | `fetchWeatherAlerts` | alerts + weather |
| IMD card | **NOT_CONFIGURED** (no key) | — | provenance | `imd_client.py` |
| River level | **UNAVAILABLE** | — | provenance | not wired |
| Provenance cards | weather, history, risk, imd, river | — | `WeatherPage.tsx` | `provenance.py` |

---

## 8) Satellite Analysis — `/satellite`

**Say:** “Real Sentinel-2 catalogue and preview thumbnails for our AOI.”

| What | LIVE | MOCK | Code |
| --- | --- | --- | --- |
| Image list | **LIVE** Copernicus STAC | `mockImages` in `satellite.ts` | `SatellitePage.tsx` → `fetchSatelliteImages` → `GET /api/v1/satellite/images` · BE: `copernicus_provider.py` |
| Analyze button | Processing on scene | mock analysis | `POST /satellite/analyze` → `satellite/service.py` |
| Preview image | Thumbnail URL / proxy | mock path | `previewSrc` → `/satellite/images/{id}/preview` |

---

## 9) Satellite Compare — `/satellite/compare`

**Say:** “Pick before and after scenes and compare.”

| What | LIVE | MOCK | Code |
| --- | --- | --- | --- |
| Compare | Live scenes + change | mock compare result | `SatelliteComparePage.tsx` → `compareSatellite` → `POST /api/v1/satellite/compare` |

---

## 10) Computer Vision — `/computer-vision`

**Say:** “Upload a ground photo. Default is DemoVisionModel. YOLO only if local weights exist — we don’t download models.”

| What | Typical status | Code |
| --- | --- | --- |
| Detect / analyze | **NOT_CONFIGURED** or Demo model (simulated boxes) | `ComputerVisionPage.tsx` → `services/vision.ts` → `POST /api/v1/vision/detect` · BE: `vision/factory.py`, `demo_model.py`, `yolo_model.py` |

---

## 11) Rescue Planning — `/rescue-planning`

**Say:** “System ranks priorities from seeded boats/centers; officer must Accept — human in the loop.”

| What | LIVE | MOCK | Code |
| --- | --- | --- | --- |
| Resources / centers | **SEEDED** DB | `mockResources`, `mockCenters` | `RescuePage.tsx` → `ops.ts` → `/resources`, `/evacuation-centers` · `db/seed.py` |
| Priorities | Rule scoring on seeded data | `mockPriorities` | `rescue.ts` → `services/rescue/priority.py` |
| Generate plan + Accept | DB plan + decision | `mockPlan` | `POST /rescue/plan`, `/rescue/plans/{id}/decision` · `rescue/service.py` |

---

## 12) Alerts — `/alerts`

**Say:** “Generate alerts from weather/risk rules; acknowledge and resolve.”

| What | LIVE | MOCK | Code |
| --- | --- | --- | --- |
| List / generate / ack | **DERIVED_LIVE** engine + DB rows | `mockAlerts` | `AlertsPage.tsx` → `services/alerts.ts` → `/alerts`, `/alerts/generate` · BE: `alerts/engine.py`, `rules.json` |
| SMS/email/push | **MOCK** (not wired) | same | `alerts/notifications.py` |
| Stream | SSE if live | disabled in FE mock | `useAlertStream.ts` |

---

## 13) Analytics — `/analytics`

**Say:** “Roll-up KPIs and charts for the demo incident.”

| What | LIVE | MOCK | Code |
| --- | --- | --- | --- |
| Overview / filters | Mix: live-derived flood metrics + seeded counts | `mockAnalytics` | `AnalyticsPage.tsx` → `services/analytics.ts` → `/analytics/overview` · BE: `analytics/service.py` |

---

## 14) Settings — `/settings`

**Say:** “Shows which incident we use and how Demo vs Live flags work. No secrets in the browser.”

| What | Data | Code |
| --- | --- | --- |
| Demo IDs, mode help | Constants + env explanation | `SettingsPage.tsx`, `constants/demo.ts` |
| Full provenance | Same status API | `DataSourcePanel` / `SafetyBanner` |

---

## Master cheat sheet — LIVE vs MOCK vs SEEDED

### Always / mostly MOCK or demo-shaped (even in LIVE UI)

| Item | Location |
| --- | --- |
| GIS **catalog** polygons/layers for command map | `frontend/src/data/gisMock.ts` via `fetchGisCatalog()` |
| Scenario constants 82%, 34.5 km², 42,000… | `frontend/src/constants/demo.ts` (`DEMO_STATS`) — reference strip on Flood; KPIs if DEMO mode |
| Notification SMS/email | Backend mock adapters |
| FE full offline mode | `frontend/src/data/mock.ts` when `VITE_USE_MOCK≠false` |

### SEEDED (real DB rows, demo content)

| Item | Location |
| --- | --- |
| Disaster incident, resources, centers, risk zones seed | `backend/app/db/seed.py` |
| FE IDs aligned | `frontend/src/constants/demo.ts` |

### LIVE external APIs

| Item | Frontend call | Backend |
| --- | --- | --- |
| Weather current/forecast | `services/weather.ts` | OpenWeather provider |
| Weather history | `services/weather.ts` | NASA POWER |
| Satellite catalogue/previews | `services/satellite.ts` | `copernicus_provider.py` |
| OSM features | `services/gis.ts` `fetchGisWithProvenance` | `gis/overpass.py` |

### DERIVED from live (computed)

| Item | Where computed |
| --- | --- |
| Flood change | `flood/service.py` + `satellite/processing.py` |
| Damage classes | `damage/service.py` + `classify.py` |
| Risk % | `services/risk/*.py` |
| Alerts | `alerts/engine.py` + `rules.json` |

### Not configured / unavailable

| Item | Status |
| --- | --- |
| IMD | NOT_CONFIGURED |
| YOLO weights | NOT_CONFIGURED (DemoVisionModel fallback) |
| River gauge | UNAVAILABLE |

---

## Suggested live demo order (talk track)

1. Point header **LIVE DATA MODE** + provenance grid  
2. Dashboard — “mix of seeded ops + live weather + demo map catalog”  
3. Weather — “this is live OpenWeather / NASA”  
4. Satellite — “live Sentinel list”  
5. Flood → Run — “derived change on real previews; open `compare_water_change` if asked”  
6. Damage → Run — “heuristic classes”  
7. Situation — “OSM Overpass vs demo catalog”  
8. Rescue Accept — “seeded boats, human approval”  
9. Alerts generate — “rules, not SMS”  
10. Settings — “flags and honesty”

---

## One closing sentence

> “Every screen is wired end-to-end. Live APIs power weather and satellites; flood and damage are calculated from those pictures; rescue inventory and the Kuttanad incident are seeded; map story layers and DEMO_STATS are clearly demo — and the badges on screen say which is which.”
