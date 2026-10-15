import { Suspense, useCallback, useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { getAlerts } from "../api/endpoints";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { Loading } from "../components/ui";
import { useAlertStream, type StreamEvent } from "../hooks/useAlertStream";
import { useAsync } from "../hooks/useAsync";

export const NAV = [
  { to: "/", label: "Situation dashboard" },
  { to: "/water", label: "Water levels" },
  { to: "/fire", label: "Fire" },
  { to: "/rainfall", label: "Rainfall & weather" },
  { to: "/satellite", label: "Satellite analysis" },
  { to: "/impact", label: "Infrastructure losses" },
  { to: "/alerts", label: "Alerts" },
  { to: "/rescue", label: "Rescue planning" },
  { to: "/analytics", label: "Analytics" },
  { to: "/vision", label: "Computer vision" },
  { to: "/sources", label: "Data sources" },
];

function Sidebar({ onNavigate, alertCount }: { onNavigate?: () => void; alertCount: number }) {
  return (
    <aside className="flex h-full w-56 shrink-0 flex-col border-r border-line bg-panel">
      <div className="border-b border-line px-4 py-4">
        <p className="font-display text-2xl tracking-wide text-amber-400">VISIONGUARD</p>
        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Karnataka live</p>
      </div>
      <nav aria-label="Primary" className="flex-1 space-y-0.5 overflow-auto p-2">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center justify-between rounded px-3 py-2 text-sm ${
                isActive ? "bg-amber-500/15 text-amber-300" : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
              }`
            }
          >
            {item.label}
            {item.to === "/alerts" && alertCount > 0 ? (
              <span className="rounded bg-red-500/20 px-1.5 text-[11px] text-red-300">{alertCount}</span>
            ) : null}
          </NavLink>
        ))}
      </nav>
      <p className="px-4 py-3 text-[10px] leading-snug text-slate-600">
        Live public data: NASA FIRMS, GloFAS, Open-Meteo, OpenWeather, Sentinel-1/2, GDACS, OpenStreetMap. Not an official warning service.
      </p>
    </aside>
  );
}

export function AppLayout() {
  const { pathname } = useLocation();
  const [menu, setMenu] = useState(false);
  const [toast, setToast] = useState<StreamEvent | null>(null);
  const alerts = useAsync(() => getAlerts("open"), [], 120_000);
  const reloadAlerts = alerts.reload;

  const onEvent = useCallback(
    (e: StreamEvent) => {
      if (e.type.startsWith("alert_") || e.type === "refresh") reloadAlerts();
      if (e.type === "alert_created" || e.type === "alert_escalated") setToast(e);
    },
    [reloadAlerts],
  );
  const connected = useAlertStream(onEvent);

  useEffect(() => {
    setMenu(false);
    document.getElementById("main-content")?.scrollTo({ top: 0 });
  }, [pathname]);

  useEffect(() => {
    if (!toast) return;
    const id = window.setTimeout(() => setToast(null), 6000);
    return () => window.clearTimeout(id);
  }, [toast]);

  const count = alerts.data?.total ?? 0;
  return (
    <div className="flex h-full min-h-0 overflow-hidden">
      <div className="hidden h-full lg:block">
        <Sidebar alertCount={count} />
      </div>
      {menu ? (
        <div className="fixed inset-0 z-[1000] lg:hidden">
          <button className="absolute inset-0 bg-black/60" onClick={() => setMenu(false)} aria-label="Close menu" />
          <div className="relative h-full w-56">
            <Sidebar alertCount={count} onNavigate={() => setMenu(false)} />
          </div>
        </div>
      ) : null}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex items-center justify-between gap-3 border-b border-line bg-panel/80 px-4 py-2">
          <button className="btn lg:hidden" onClick={() => setMenu(true)} aria-label="Open menu">
            Menu
          </button>
          <p className="text-sm text-slate-400">Karnataka · 31 districts · 16 river stations</p>
          <span className={`flex items-center gap-1.5 text-xs ${connected ? "text-emerald-400" : "text-slate-500"}`}>
            <span className={`h-2 w-2 rounded-full ${connected ? "bg-emerald-400" : "bg-slate-600"}`} />
            {connected ? "Live alert stream" : "Alert stream offline"}
          </span>
        </header>
        <main id="main-content" tabIndex={-1} className="min-h-0 flex-1 overflow-y-auto p-3 md:p-4">
          <ErrorBoundary resetKey={pathname}>
            <Suspense fallback={<Loading text="Loading page…" />}>
              <Outlet />
            </Suspense>
          </ErrorBoundary>
        </main>
      </div>
      {toast ? (
        <div className="fixed bottom-4 right-4 z-[1000] max-w-sm rounded border border-amber-500/40 bg-panel px-4 py-3 text-sm shadow-xl" role="status">
          <p className="text-xs uppercase tracking-wider text-amber-400">{toast.type === "alert_created" ? "New alert" : "Alert escalated"}</p>
          <p className="text-slate-200">{toast.title}</p>
        </div>
      ) : null}
    </div>
  );
}
