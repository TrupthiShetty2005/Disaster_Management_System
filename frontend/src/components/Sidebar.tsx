import { flushSync } from "react-dom";
import { NavLink, useNavigate } from "react-router-dom";
import { DEMO_INCIDENT_ID } from "../constants/demo";
import { isMockMode } from "../services/apiClient";

export type SidebarItem = { to: string; label: string };

const CORE_ITEMS: SidebarItem[] = [
  { to: "/dashboard", label: "Command dashboard" },
  { to: "/risk-intelligence", label: "Risk Intelligence" },
  { to: "/situation", label: "Live Situation" },
  { to: "/flood-detection", label: "Flood Detection" },
  { to: "/damage-assessment", label: "Damage Assessment" },
  { to: "/weather", label: "Weather" },
  { to: "/satellite", label: "Satellite Analysis" },
  { to: "/satellite/compare", label: "Satellite Compare" },
  { to: "/computer-vision", label: "Computer Vision" },
  { to: "/rescue-planning", label: "Rescue Planning" },
  { to: "/alerts", label: "Alerts" },
  { to: "/analytics", label: "Analytics" },
  { to: "/settings", label: "Settings" },
];

/** Demo Mode only: seeded Kuttanad incident. Hidden in REAL DATA — no live incident-command workflow. */
export function sidebarItems(demoMode: boolean, _liveIncidentId?: string | null): SidebarItem[] {
  const items = [...CORE_ITEMS];
  if (demoMode) {
    items.splice(1, 0, { to: `/disasters/${DEMO_INCIDENT_ID}`, label: "Incident command" });
  }
  return items;
}

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const navigate = useNavigate();
  const items = sidebarItems(isMockMode());
  return (
    <aside className="flex h-full w-56 shrink-0 flex-col border-r border-line bg-panel">
      <div className="border-b border-line px-4 py-4">
        <p className="font-display text-2xl tracking-wide text-amber-400">VISIONGUARD</p>
        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Command center</p>
      </div>
      <nav aria-label="Primary" className="flex-1 space-y-0.5 overflow-auto p-2">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/dashboard"}
            onClick={(e) => {
              e.preventDefault();
              onNavigate?.();
              flushSync(() => {
                navigate(item.to);
              });
            }}
            className={({ isActive }) =>
              `block rounded px-3 py-2 text-sm ${
                isActive ? "bg-amber-500/15 text-amber-300" : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      <p className="px-4 py-3 text-[10px] text-slate-600">India · Karnataka AOI · not official warnings</p>
    </aside>
  );
}
