import { useEffect, useMemo, useState } from "react";
import type { AlertItem } from "../types/api";
import { StatusBadge } from "./StatusBadge";
import { SafetyBanner } from "./SafetyBanner";

export type AlertFilter = "all" | "critical" | "warning" | "watch" | "info";

export function normalizeAlertSeverity(value: string): AlertFilter {
  const v = value.toLowerCase();
  if (v === "critical" || v === "severe") return "critical";
  if (v === "warning" || v === "high") return "warning";
  if (v === "watch" || v === "medium") return "watch";
  return "info";
}

export function filterAlerts(items: AlertItem[], filter: AlertFilter): AlertItem[] {
  if (filter === "all") return items;
  return items.filter((a) => normalizeAlertSeverity(a.severity) === filter);
}

const rank: Record<string, number> = { critical: 0, warning: 1, watch: 2, info: 3 };

export function AlertPanel({
  items,
  onAck,
  onResolve,
  showSafety = false,
  highlightedId,
}: {
  items: AlertItem[];
  onAck?: (id: string) => void;
  onResolve?: (id: string) => void;
  showSafety?: boolean;
  highlightedId?: string | null;
}) {
  const [filter, setFilter] = useState<AlertFilter>("all");
  const shown = useMemo(() => {
    const list = filterAlerts(items, filter);
    return [...list].sort((a, b) => rank[normalizeAlertSeverity(a.severity)] - rank[normalizeAlertSeverity(b.severity)]);
  }, [items, filter]);

  return (
    <section className="flex h-full min-h-[240px] flex-col rounded border border-line bg-panel">
      <div className="flex items-center justify-between border-b border-line px-3 py-2">
        <h3 className="text-xs uppercase tracking-widest text-slate-500">Alerts</h3>
        <div className="flex gap-1 text-[11px]">
          {(["all", "critical", "warning", "watch", "info"] as AlertFilter[]).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`rounded px-2 py-0.5 capitalize ${filter === f ? "bg-amber-500/20 text-amber-300" : "text-slate-500 hover:text-slate-300"}`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>
      {showSafety ? (
        <div className="px-3 pt-2">
          <SafetyBanner compact />
        </div>
      ) : null}
      <div className="flex-1 space-y-2 overflow-auto p-3">
        {shown.length === 0 ? <p className="text-sm text-slate-500">No alerts in this filter.</p> : null}
        {shown.map((a) => (
          <article
            key={a.id}
            className={`rounded border p-2 ${highlightedId === a.id ? "border-amber-400 bg-amber-500/10" : "border-line"}`}
          >
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-medium text-slate-100">{a.title}</p>
              <StatusBadge value={normalizeAlertSeverity(a.severity)} />
            </div>
            <p className="mt-1 text-xs text-slate-400">
              {a.location_name ?? a.category} · score {a.risk_score ?? "—"} · {new Date(a.issued_at).toLocaleString()} · {a.status ?? "ACTIVE"}
              {a.official_warning
                ? " · official warning"
                : a.alert_kind === "heuristic_risk_estimate"
                  ? " · derived risk estimate (not official)"
                  : a.provenance_status === "UNKNOWN"
                    ? " · unverified provenance"
                    : ""}
            </p>
            <p className="mt-1 text-xs text-slate-500">{a.message}</p>
            {a.reason ? <p className="mt-1 text-xs text-slate-500">Reason: {a.reason}</p> : null}
            {a.recommended_action || a.recommendation ? (
              <p className="mt-1 text-xs text-amber-200/90">Rec: {a.recommended_action || a.recommendation}</p>
            ) : null}
            {onAck || onResolve ? (
              <div className="mt-2 flex gap-2">
                {onAck ? (
                  <button type="button" className="text-xs text-sky-300" onClick={() => onAck(a.id)}>
                    Acknowledge
                  </button>
                ) : null}
                {onResolve ? (
                  <button type="button" className="text-xs text-emerald-300" onClick={() => onResolve(a.id)}>
                    Resolve
                  </button>
                ) : null}
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}

export function ClockStamp() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);
  return (
    <time className="font-mono text-xs text-slate-400" dateTime={now.toISOString()}>
      {now.toLocaleString("en-IN", { timeZone: "Asia/Kolkata", hour12: false })} IST
    </time>
  );
}
