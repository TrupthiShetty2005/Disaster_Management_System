    # VisionGuard — Spoken Presentation Script (Full UI)

Practice this out loud while clicking. Target: **10–15 minutes**.  
Mode for demo: **LIVE DATA MODE** (header should say LIVE).

---

## OPENING (about 45 seconds)

Good morning. This is **VisionGuard AI** — a disaster operations command console.

We built it as decision support for officers during a flood. The story we use is one real place in Kerala: **Kuttanad / Alappuzha**.

How the system works in one sentence:  
the **React frontend** talks to a **FastAPI backend**. The backend pulls **live weather and satellite data**, calculates flood and damage indications, and also uses **seeded demo data** for rescue boats and the incident record — and every screen shows a badge so you can see what is live, what is calculated, and what is demo.

Please look at the top: it says **LIVE DATA MODE**. Below that is our **data provenance panel**. That panel is not decoration — it comes from the API `GET /api/v1/data-sources/status`, coded in `backend/app/services/provenance.py` and shown in `DataModeBadge.tsx`.

One important rule: if the frontend flag `VITE_USE_MOCK` is not set to false, the UI uses `frontend/src/data/mock.ts` and does not call the API. Today it is false, so we are on the live path. That check lives in `frontend/src/services/apiClient.ts`.

---

## SHARED SHELL (every page)

Before pages — this shell stays the same.

On the left is the **sidebar** — `Sidebar.tsx` — navigation only.  
The **incident bar** pins one flood: “Kuttanad monsoon inundation.” That ID is fixed in `frontend/src/constants/demo.ts` and the same ID is seeded in `backend/app/db/seed.py`. So every module talks about the same disaster.  
The **header** shows LIVE or DEMO. Routes are in `App.tsx`. Layout is `AppLayout.tsx`.

---

## 1) COMMAND DASHBOARD

*Click: Command dashboard*

This is the officer’s first view.

You see KPIs — active disasters, critical alerts, population at risk, flooded area, damaged buildings, rescue units — plus weather, a map, charts, and alerts.

**What is live here?**  
The weather strip can be **live OpenWeather** for **Alappuzha, India**. Frontend: `services/weather.ts`. Backend: OpenWeather provider.

**What is seeded?**  
Disasters, alerts count, and rescue resources come from our **database seed** — `seed.py` — not from a government live feed. Frontend services: `disasters.ts`, `ops.ts`.

**What is still demo?**  
The map layer catalog — flood polygons, risk zones drawn for the story — comes from `frontend/src/data/gisMock.ts` through `fetchGisCatalog` in `gis.ts`. Even in LIVE mode, that catalog stays demo-shaped so the narrative map works. The map component is `DisasterMap.tsx`.

The page itself is `DashboardPage.tsx`.

So on this one screen I can honestly say: **mixed** — live weather possible, seeded ops data, demo map story layers.

---

## 2) INCIDENT COMMAND

*Click: Incident command*

This is the single flood case file for Kuttanad.

It loads the incident picture and summary so weather, flood, rescue, and alerts all stay on one event.

Frontend: `DisasterDetailPage.tsx` → `services/incident.ts` → API `/api/v1/incidents/{id}`.  
Data: **seeded** in `db/seed.py`. In full frontend mock mode it would come from `mock.ts`.

---

## 3) RISK INTELLIGENCE

*Click: Risk Intelligence*

Here we show high-risk zones on a map for planning.

The zone list comes from the API `/risk-zones` — in practice **seeded** risk zones in the database. Frontend: `RiskIntelligencePage.tsx` → `services/risk.ts`.

The map catalog again uses **gisMock**.

Important: the flood and cyclone **percentage risk scores** that use **live weather** are mainly shown on the **Weather** page. Those scores are rule-based — VisionGuard rules — not official IMD warnings. Backend: `services/risk/`.

---

## 4) LIVE SITUATION

*Click: Live Situation*

This is situation awareness.

Here we have two kinds of map data, and we distinguish them clearly.

First — **OpenStreetMap through Overpass**: roads, amenities — real reference GIS. We call this **STATIC EXTERNAL** — it is real map data, but it is not a live flood sensor. Frontend: `fetchGisWithProvenance` in `gis.ts`. Backend: `services/gis/overpass.py`. API: `/api/v1/gis/features`.

Second — the **demo catalog polygons** for the command story still come from `gisMock.ts`.

The disaster list is **seeded**. Provenance cards on this page say that — `ModuleProvenance` in `SituationPage.tsx`.

---

## 5) WEATHER *(strong live demo — good place to pause)*

*Click: Weather*

This is where live data is clearest.

**Current weather and forecast** — live from **OpenWeather**, city query **Alappuzha, IN**.  
Code: `WeatherPage.tsx` → `services/weather.ts` → backend `weather/openweather_provider.py`, config default in `core/config.py`.

**History** — live from **NASA POWER** at our demo coordinates about **9.517°N, 76.522°E** — Kuttanad AOI. Backend: `nasa_power.py`.

**Flood and cyclone risk percent** — **calculated** from that weather by our rules — status **DERIVED FROM LIVE**. Backend: `services/risk/`. Not an IMD official warning.

**IMD card** — not configured unless we have an IMD key. We show **NOT CONFIGURED** instead of inventing official alerts.

**River level** — **UNAVAILABLE**. We did not invent a gauge number.

Provenance cards on this page explain each block.

---

## 6) SATELLITE ANALYSIS

*Click: Satellite Analysis*

Here we list real **Sentinel-2** scenes from the **Copernicus** catalogue for our area, with preview thumbnails.

Frontend: `SatellitePage.tsx` → `services/satellite.ts` → API `/satellite/images`.  
Backend: `services/satellite/copernicus_provider.py`.

This is **LIVE** catalogue and preview imagery — not a fake picture file pretending to be satellite.

Analyze uses the satellite service: `satellite/service.py`.

---

## 7) SATELLITE COMPARE

*Click: Satellite Compare*

Officer picks a before scene and an after scene and compares them.

Frontend: `SatelliteComparePage.tsx` → `compareSatellite` → `POST /api/v1/satellite/compare`.

Same live scene catalogue; comparison is our processing path.

---

## 8) FLOOD DETECTION *(core technical story)*

*Click: Flood Detection → Run flood analysis*

This is the heart of the flood story.

We take two **real Sentinel-2 preview images** — before and after — and run a **heuristic water-change** method: pixels that look like water in the after image but not in the before. That is **change indication**, not a trained U-Net flood model.

Status badge: **DERIVED FROM LIVE DATA**.

Frontend: `FloodPage.tsx` → `services/flood.ts` → `POST /api/v1/flood/analyze`.  
Backend orchestration: `services/flood/service.py` function `analyze`.  
Core math: `services/satellite/processing.py` function `compare_water_change`.

You may also see a **scenario strip** with numbers like 34.5 km² and 42,000 people — those come from `DEMO_STATS` in `constants/demo.ts`. That is our **simulated scenario reference**, separate from the live change result. We keep them labeled so judges are not confused.

---

## 9) DAMAGE ASSESSMENT

*Click: Damage Assessment → Run*

Same idea: satellite before/after change signals go into a **rule-based severity classifier** for buildings and roads — NO DAMAGE through DESTROYED.

It is **not** a trained damage neural network. Badge: **DERIVED FROM LIVE**.

Frontend: `DamagePage.tsx` → `services/damage.ts` → `POST /damage/analyze`.  
Backend: `services/damage/service.py` and `damage/classify.py`.

---

## 10) COMPUTER VISION

*Click: Computer Vision*

Officer can upload a ground photo. Default backend is **DemoVisionModel** — simulated detections for the prototype. Optional **YOLO** only if local weights exist — we do not auto-download models, and generic YOLO is not a disaster-trained model.

Frontend: `ComputerVisionPage.tsx` → `services/vision.ts`.  
Backend: `vision/factory.py`, `demo_model.py`, `yolo_model.py`.  
Usually shown as **NOT CONFIGURED** for real YOLO weights.

---

## 11) RESCUE PLANNING

*Click: Rescue Planning → generate plan → Accept*

Here we propose rescue priorities and a plan.

Boats, teams, evacuation centers are **SEEDED** demo inventory in `seed.py` — because there is no public live API for local rescue stock in this demo.

Scoring is rule-based: `services/rescue/priority.py`, `recommend.py`.  
Frontend: `RescuePage.tsx` → `services/rescue.ts` and `ops.ts`.

Critical point: the officer must click **Accept**. Human stays in the loop. We do not auto-dispatch.

---

## 12) ALERTS

*Click: Alerts → Generate if needed → Acknowledge one*

Alerts are produced by our **early-warning engine** using thresholds in `alerts/rules.json`, driven by weather and risk inputs.

So alerts are **DERIVED** — calculated signals — not government SMS.

Frontend: `AlertsPage.tsx` → `services/alerts.ts`.  
Backend: `alerts/engine.py`, `service.py`.

SMS, email, push adapters are **MOCK** — not wired to real telecom. That is honest: `alerts/notifications.py`.

---

## 13) ANALYTICS

*Click: Analytics*

Roll-up KPIs and charts for the incident — a mix of flood-analysis metrics and seeded operational counts.

Frontend: `AnalyticsPage.tsx` → `services/analytics.ts`.  
Backend: `analytics/service.py`.

---

## 14) SETTINGS

*Click: Settings*

Here we explain the demo incident IDs, Demo versus Live flags, and that secrets stay in backend `.env`, not in the browser.

Frontend: `SettingsPage.tsx`. Full provenance panel again.

---

## CLOSING — “Where is mock? Where is live?” (30 seconds)

Let me summarize for the panel in one breath.

**LIVE external data:** OpenWeather and NASA POWER on Weather; Copernicus Sentinel-2 on Satellite and Flood; OpenStreetMap Overpass on Situation.

**DERIVED from live:** flood change, damage classes, risk percentages, alert generation — calculated in our Python services.

**SEEDED:** the Kuttanad incident, rescue resources, centers — `backend/app/db/seed.py`.

**Still demo / mock-shaped:** command-map catalog in `gisMock.ts`; `DEMO_STATS` scenario numbers; notification SMS; and the entire `mock.ts` path if Demo Mode is on.

We chose real free datasets we can explain, and simple OpenCV change detection we can show in code — instead of claiming a trained U-Net or official IMD feed we do not have.

Thank you. Happy to open any file — for flood processing I would open `compare_water_change` in `satellite/processing.py`.

---

## QUICK “IF THEY ASK” LINES

**Which region is weather?**  
Alappuzha, India for OpenWeather; Kuttanad point 9.517, 76.522 for NASA history.

**Is flood AI?**  
Heuristic change on real Sentinel previews — not a trained flood model. Labeled DERIVED LIVE.

**Why seed rescue data?**  
So the full ops workflow works; public live rescue inventory isn’t available for this demo.

**Where is the switch?**  
Frontend `VITE_USE_MOCK` in `apiClient.ts`; backend `USE_MOCK_PROVIDERS` in `config.py`.
