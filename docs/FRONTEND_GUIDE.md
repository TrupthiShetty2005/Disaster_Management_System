# Frontend guide

Entry: `frontend/src/main.tsx` mounts `App` and `styles/index.css`.

Framework: **React 19 + TypeScript + Vite**. Routing: **react-router-dom** `BrowserRouter`. There is **no Redux/Zustand**. Page data is local `useState` plus `useAsync` (promise → `{ data, error, loading }`).

Styling: **Tailwind** (`tailwind.config.js`, `src/styles/index.css`). Charts: **Chart.js** via `react-chartjs-2`. Maps: **Leaflet** via `react-leaflet`, Carto dark raster tiles (public basemap, not a disaster satellite product).

API: `src/services/apiClient.ts`. If `import.meta.env.VITE_USE_MOCK !== "false"`, most services return `src/data/mock.ts` and skip the network. GIS catalog **always** comes from `src/data/gisMock.ts`.

Layout: `src/layouts/AppLayout.tsx` — skip link, sidebar (desktop), mobile drawer, `Header`, `IncidentBar`, `<Outlet />`.

Unused page files (not in `App.tsx`): `OverviewPage.tsx`, `RiskPage.tsx`.

## Page table

| Page | Route | Main components | API used (when mock off) | Purpose |
| --- | --- | --- | --- | --- |
| Dashboard | `/dashboard` | DisasterMap, KpiCard, AlertPanel, DashboardCharts, SafetyBanner | `/disasters`, `/alerts`, `/resources`, `/weather/current`, `/analytics/overview`; GIS mock | Ops overview |
| Weather | `/weather` | KpiCard, Chart.js Line, DataTable, EstimateCallout | `/weather/*`, `/risk/flood`, `/risk/cyclone` | Weather and prototype risk |
| Risk Intelligence | `/risk-intelligence` | DisasterMap, StatusBadge, EstimateCallout | `/risk-zones` | Zone scores and factors |
| Live situation | `/situation` (`/live-situation` redirects) | DataTable, SituationMap | `/disasters`; map points from `intel.fetchMapPoints` mock | List + simple map |
| Satellite | `/satellite` | SatelliteOverlayMap | `/satellite/images`, POST `/satellite/analyze` | Scene catalog and analysis |
| Satellite compare | `/satellite/compare` | overlay map | POST `/satellite/compare` | Before/after |
| Computer vision | `/computer-vision` | file input, StatusBadge | POST `/vision/analyze`, GET annotated | Upload detections |
| Flood detection | `/flood-detection` | SatelliteOverlayMap, KpiCard | POST `/flood/analyze`, GET `/flood/events` | Water mask map |
| Damage assessment | `/damage-assessment` | Doughnut charts, overlay map | POST `/damage/analyze`, GET assessments, satellite previews | Change detection report |
| Rescue planning | `/rescue-planning` | RescuePlanningMap | `/rescue/priorities`, POST `/rescue/plan`, POST decision, `/resources` | Plan + human decision |
| Alerts | `/alerts` | filters, AlertPanel | `/alerts`, generate, ack, resolve, SSE/poll | Prototype warnings |
| Analytics | `/analytics` | KpiCard, TrendCharts | `/analytics/overview` | KPI time series |
| Incident command | `/disasters/:id` | KPI, links | `/incidents/{id}` | Combined picture |
| Settings | `/settings` | export links | `/exports/{dataset}`, POST `/reports/generate` | Demo IDs and exports |

Redirects: `/` → `/dashboard`; `/risk` → `/risk-intelligence`; `/flood` → `/flood-detection`; `/damage` → `/damage-assessment`; `/rescue` → `/rescue-planning`.

## Shared components

`KpiCard`, `StatusBadge`, `DataTable`, `Feedback` (loading/error/empty/modal), `SafetyBanner`, `EstimateCallout`, `Breadcrumbs`, `SelectedAreaPanel`, `AlertPanel`, `Header`, `Sidebar`, `IncidentBar`, map and chart components listed above.

## Error / loading

Pages that use `useAsync` typically show `LoadingState` then `ErrorState`. Vision/flood/damage also use local `busy`/`error` on button actions.

## Theme

Tailwind colors `ink`, `panel`, `line`, `warn`, `danger`, `ok` in `tailwind.config.js`. Focus styles in `index.css`.
