import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./layouts/AppLayout";
import { DashboardPage } from "./pages/DashboardPage";
import { WeatherPage } from "./pages/WeatherPage";
import { LoadingState } from "./components/Feedback";
import { DataModeGate } from "./components/DataModeGate";

const RiskIntelligencePage = lazy(() =>
  import("./pages/RiskIntelligencePage").then((m) => ({ default: m.RiskIntelligencePage })),
);
const SituationPage = lazy(() => import("./pages/SituationPage").then((m) => ({ default: m.SituationPage })));
const FloodPage = lazy(() => import("./pages/FloodPage").then((m) => ({ default: m.FloodPage })));
const DamagePage = lazy(() => import("./pages/DamagePage").then((m) => ({ default: m.DamagePage })));
const SatellitePage = lazy(() => import("./pages/SatellitePage").then((m) => ({ default: m.SatellitePage })));
const SatelliteComparePage = lazy(() =>
  import("./pages/SatelliteComparePage").then((m) => ({ default: m.SatelliteComparePage })),
);
const RescuePage = lazy(() => import("./pages/RescuePage").then((m) => ({ default: m.RescuePage })));
const AlertsPage = lazy(() => import("./pages/AlertsPage").then((m) => ({ default: m.AlertsPage })));
const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage").then((m) => ({ default: m.AnalyticsPage })));
const ComputerVisionPage = lazy(() =>
  import("./pages/ComputerVisionPage").then((m) => ({ default: m.ComputerVisionPage })),
);
const DisasterDetailPage = lazy(() =>
  import("./pages/DisasterDetailPage").then((m) => ({ default: m.DisasterDetailPage })),
);
const SettingsPage = lazy(() => import("./pages/SettingsPage").then((m) => ({ default: m.SettingsPage })));

export default function App() {
  return (
    <BrowserRouter>
      <DataModeGate>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/risk" element={<Navigate to="/risk-intelligence" replace />} />
          <Route path="/risk-intelligence" element={<Suspense fallback={<LoadingState />}><RiskIntelligencePage /></Suspense>} />
          <Route path="/situation" element={<Suspense fallback={<LoadingState />}><SituationPage /></Suspense>} />
          <Route path="/live-situation" element={<Navigate to="/situation" replace />} />
          <Route path="/flood" element={<Navigate to="/flood-detection" replace />} />
          <Route path="/flood-detection" element={<Suspense fallback={<LoadingState />}><FloodPage /></Suspense>} />
          <Route path="/damage" element={<Navigate to="/damage-assessment" replace />} />
          <Route path="/damage-assessment" element={<Suspense fallback={<LoadingState />}><DamagePage /></Suspense>} />
          <Route path="/weather" element={<WeatherPage />} />
          <Route path="/satellite" element={<Suspense fallback={<LoadingState />}><SatellitePage /></Suspense>} />
          <Route path="/satellite/compare" element={<Suspense fallback={<LoadingState />}><SatelliteComparePage /></Suspense>} />
          <Route path="/rescue" element={<Navigate to="/rescue-planning" replace />} />
          <Route path="/rescue-planning" element={<Suspense fallback={<LoadingState />}><RescuePage /></Suspense>} />
          <Route path="/alerts" element={<Suspense fallback={<LoadingState />}><AlertsPage /></Suspense>} />
          <Route path="/analytics" element={<Suspense fallback={<LoadingState />}><AnalyticsPage /></Suspense>} />
          <Route path="/computer-vision" element={<Suspense fallback={<LoadingState />}><ComputerVisionPage /></Suspense>} />
          <Route path="/disasters/:id" element={<Suspense fallback={<LoadingState />}><DisasterDetailPage /></Suspense>} />
          <Route path="/settings" element={<Suspense fallback={<LoadingState />}><SettingsPage /></Suspense>} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
      </DataModeGate>
    </BrowserRouter>
  );
}
