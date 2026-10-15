import { lazy } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import "./charts/setup";
import { AppLayout } from "./layout/AppLayout";

const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const WaterPage = lazy(() => import("./pages/WaterPage"));
const FirePage = lazy(() => import("./pages/FirePage"));
const RainfallPage = lazy(() => import("./pages/RainfallPage"));
const SatellitePage = lazy(() => import("./pages/SatellitePage"));
const ImpactPage = lazy(() => import("./pages/ImpactPage"));
const AlertsPage = lazy(() => import("./pages/AlertsPage"));
const RescuePage = lazy(() => import("./pages/RescuePage"));
const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage"));
const VisionPage = lazy(() => import("./pages/VisionPage"));
const SourcesPage = lazy(() => import("./pages/SourcesPage"));

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="water" element={<WaterPage />} />
          <Route path="fire" element={<FirePage />} />
          <Route path="rainfall" element={<RainfallPage />} />
          <Route path="satellite" element={<SatellitePage />} />
          <Route path="impact" element={<ImpactPage />} />
          <Route path="alerts" element={<AlertsPage />} />
          <Route path="rescue" element={<RescuePage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="vision" element={<VisionPage />} />
          <Route path="sources" element={<SourcesPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
