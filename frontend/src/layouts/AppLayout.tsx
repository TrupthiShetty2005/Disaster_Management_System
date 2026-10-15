import { Suspense, useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { LoadingState } from "../components/Feedback";
import { Header } from "../components/Header";
import { Sidebar } from "../components/Sidebar";
import { IncidentBar } from "../components/IncidentBar";
import { SafetyBanner } from "../components/SafetyBanner";
import { DataSourcePanel } from "../components/DataModeBadge";
import { RegionPanel } from "../components/RegionPanel";
import { useAsync } from "../hooks/useAsync";
import { fetchAlerts } from "../services/ops";

const titles: Record<string, string> = {
  "/": "Situation Awareness Dashboard",
  "/dashboard": "Situation Awareness Dashboard",
  "/risk": "Risk Intelligence",
  "/risk-intelligence": "Risk Intelligence",
  "/situation": "Live Situation",
  "/live-situation": "Live Situation",
  "/flood": "Flood Detection",
  "/flood-detection": "Flood Detection",
  "/damage": "Damage Assessment",
  "/damage-assessment": "Damage Assessment",
  "/weather": "Weather Intelligence",
  "/satellite": "Satellite Analysis",
  "/satellite/compare": "Satellite Comparison",
  "/computer-vision": "Computer Vision",
  "/rescue": "Rescue Planning",
  "/rescue-planning": "Rescue Planning",
  "/alerts": "Alerts",
  "/analytics": "Disaster analytics",
  "/settings": "Settings",
};

function pageTitle(pathname: string): string {
  if (pathname.startsWith("/disasters/")) return "Incident command";
  return titles[pathname] ?? "VisionGuard";
}

export function AppLayout() {
  const { pathname } = useLocation();
  const [menu, setMenu] = useState(false);
  const alerts = useAsync(fetchAlerts, []);
  const count = alerts.data?.total ?? 0;

  useEffect(() => {
    setMenu(false);
    document.getElementById("main-content")?.scrollTo({ top: 0 });
  }, [pathname]);

  return (
    <div className="flex h-full min-h-0 overflow-hidden">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-ink focus:px-3 focus:py-2"
      >
        Skip to main content
      </a>
      <div className="relative z-20 hidden h-full min-h-0 lg:block">
        <Sidebar />
      </div>
      {menu ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button className="absolute inset-0 bg-black/60" onClick={() => setMenu(false)} aria-label="Close menu" />
          <div className="relative z-50 h-full w-56">
            <Sidebar onNavigate={() => setMenu(false)} />
          </div>
        </div>
      ) : null}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <Header title={pageTitle(pathname)} alertCount={count} onMenu={() => setMenu(true)} />
        <IncidentBar />
        <main id="main-content" tabIndex={-1} className="relative z-10 min-h-0 flex-1 overflow-y-auto overflow-x-hidden p-3 md:p-4">
          <div className="mb-3 space-y-2 border-b border-line pb-3">
            <SafetyBanner compact />
            <DataSourcePanel compact />
            <RegionPanel />
          </div>
          <Suspense fallback={<LoadingState />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  );
}
