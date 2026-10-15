import { useState } from "react";
import { ClockStamp } from "./AlertPanel";
import { DataModeBadge } from "./DataModeBadge";
import { getModeSnapshot } from "../services/dataMode";

export function Header({
  title,
  alertCount = 0,
  onMenu,
}: {
  title: string;
  alertCount?: number;
  onMenu?: () => void;
}) {
  const [openNotif, setOpenNotif] = useState(false);
  const modeLabel = getModeSnapshot().dataMode;

  return (
    <header className="flex items-center justify-between gap-3 border-b border-line bg-panel px-4 py-2.5 md:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          className="rounded border border-line px-2 py-1 text-slate-400 lg:hidden"
          onClick={onMenu}
          aria-label="Open navigation"
        >
          Menu
        </button>
        <div className="min-w-0">
          <p className="font-display text-lg tracking-wide text-amber-400 md:text-xl">VISIONGUARD AI</p>
          <h1 className="truncate text-sm text-slate-300">{title}</h1>
        </div>
      </div>
      <div className="flex items-center gap-2 text-xs md:gap-4">
        <DataModeBadge />
        <ClockStamp />
        <div className="relative">
          <button
            type="button"
            className="rounded border border-line px-2 py-1 text-slate-300"
            onClick={() => setOpenNotif((v) => !v)}
            aria-label="Notifications"
          >
            Alerts {alertCount > 0 ? <span className="ml-1 rounded bg-danger px-1.5 text-[10px] text-white">{alertCount}</span> : null}
          </button>
          {openNotif ? (
            <p className="absolute right-0 z-20 mt-1 w-56 rounded border border-line bg-ink p-2 text-slate-400">
              {alertCount} active alert{alertCount === 1 ? "" : "s"} in the ops feed. Open Alerts for full list.
            </p>
          ) : null}
        </div>
        <div className="hidden items-center gap-2 sm:flex">
          <div className="hidden md:block text-right">
            <p className="text-slate-200">Decision-support console</p>
            <p className="text-[10px] text-slate-500">
              No user login
              {modeLabel ? ` · ${modeLabel}` : ""}
            </p>
          </div>
        </div>
      </div>
    </header>
  );
}
