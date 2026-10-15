import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { acknowledgeAlert, getAlerts, refreshAlerts, resolveAlert } from "../api/endpoints";
import type { Alert } from "../api/types";
import { Async, Card, Empty, ErrorBox, LevelBadge, PageHeader, Source } from "../components/ui";
import { useAlertStream, type StreamEvent } from "../hooks/useAlertStream";
import { useAsync } from "../hooks/useAsync";
import { fmt, fmtDateTime, label, levelColor, timeAgo } from "../lib/format";

const STATUS_FILTERS = [
  { id: "open", label: "Open" },
  { id: "RESOLVED", label: "Resolved" },
  { id: "EXPIRED", label: "Expired" },
  { id: "all", label: "All" },
];

function AlertRow({ a, onChange }: { a: Alert; onChange: () => void }) {
  const [busy, setBusy] = useState(false);
  const act = (fn: (id: string) => Promise<Alert>) => {
    setBusy(true);
    fn(a.id)
      .then(onChange)
      .finally(() => setBusy(false));
  };
  const open = a.status === "ACTIVE" || a.status === "ACKNOWLEDGED";
  return (
    <li className="rounded border border-line border-l-4 bg-ink/30 p-3" style={{ borderLeftColor: levelColor(a.severity) }}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm text-slate-100">
            <LevelBadge level={a.severity} /> <span className="ml-1">{a.title}</span>
          </p>
          <p className="mt-1 text-xs text-slate-400">{a.message}</p>
          <p className="mt-1 text-[11px] text-slate-500">
            {label(a.hazard)} · {a.district ?? "Karnataka"} · {a.source}
            {a.observed_value !== null ? ` · observed ${fmt(a.observed_value, 1)} ${a.unit ?? ""}` : ""}
            {a.threshold !== null ? ` (threshold ${fmt(a.threshold, 1)})` : ""} · first raised {fmtDateTime(a.created_at)} · updated {timeAgo(a.updated_at)}
            {a.valid_until ? ` · valid until ${fmtDateTime(a.valid_until)}` : ""}
            {a.acknowledged_by ? ` · acknowledged by ${a.acknowledged_by}` : ""}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <span className="text-[11px] text-slate-500">{label(a.status)}</span>
          {a.latitude !== null ? (
            <Link className="btn" to={`/rescue?lat=${a.latitude}&lon=${a.longitude}&alert=${a.id}`}>
              Plan response
            </Link>
          ) : null}
          {a.status === "ACTIVE" ? (
            <button className="btn" disabled={busy} onClick={() => act(acknowledgeAlert)}>
              Acknowledge
            </button>
          ) : null}
          {open ? (
            <button className="btn" disabled={busy} onClick={() => act(resolveAlert)}>
              Resolve
            </button>
          ) : null}
          {a.source_url ? (
            <a className="btn" href={a.source_url} target="_blank" rel="noreferrer">
              Source
            </a>
          ) : null}
        </div>
      </div>
    </li>
  );
}

export default function AlertsPage() {
  const [status, setStatus] = useState("open");
  const [hazard, setHazard] = useState("");
  const alerts = useAsync(() => getAlerts(status), [status], 120_000);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMsg, setRefreshMsg] = useState<string | null>(null);
  const reload = alerts.reload;

  const onEvent = useCallback(
    (e: StreamEvent) => {
      setEvents((prev) => [e, ...prev].slice(0, 30));
      reload();
    },
    [reload],
  );
  const connected = useAlertStream(onEvent);

  const refresh = () => {
    setRefreshing(true);
    setRefreshMsg(null);
    refreshAlerts()
      .then((s) => {
        const errs = Object.entries(s.errors);
        setRefreshMsg(`Re-evaluated live feeds: ${s.created} new, ${s.updated} updated, ${s.resolved} resolved, ${s.expired} expired.${errs.length ? ` Unavailable: ${errs.map(([k]) => k).join(", ")}.` : ""}`);
        reload();
      })
      .catch((e: Error) => setRefreshMsg(e.message))
      .finally(() => setRefreshing(false));
  };

  return (
    <div className="space-y-3">
      <PageHeader
        title="Alerts"
        subtitle="Alerts are raised automatically every 30 minutes when a live measurement or forecast crosses a threshold: river discharge vs return levels, IMD heavy-rain categories, FIRMS fire events, fire-danger index, and GDACS events near Karnataka. They resolve on their own when the condition clears."
        actions={
          <button className="btn-primary" onClick={refresh} disabled={refreshing}>
            {refreshing ? "Checking all live feeds…" : "Re-evaluate now"}
          </button>
        }
      />
      {refreshMsg ? <p className="rounded border border-line bg-panel p-2 text-sm text-slate-300">{refreshMsg}</p> : null}
      <div className="grid gap-3 xl:grid-cols-[1fr_320px]">
        <Card
          title="Alert feed"
          actions={
            <div className="flex flex-wrap gap-1">
              {STATUS_FILTERS.map((f) => (
                <button key={f.id} onClick={() => setStatus(f.id)} className={`btn text-xs ${status === f.id ? "border-amber-500/60 text-amber-300" : ""}`}>
                  {f.label}
                </button>
              ))}
              <select className="rounded border border-line bg-ink px-2 text-xs" value={hazard} onChange={(e) => setHazard(e.target.value)} aria-label="Hazard filter">
                <option value="">All hazards</option>
                {[...new Set(alerts.data?.items.map((a) => a.hazard) ?? [])].sort().map((h) => (
                  <option key={h} value={h}>
                    {label(h)}
                  </option>
                ))}
              </select>
            </div>
          }
        >
          {alerts.error && !alerts.data ? <ErrorBox message={alerts.error} onRetry={alerts.reload} /> : null}
          <Async state={alerts}>
            {(d) => {
              const items = d.items.filter((a) => !hazard || a.hazard === hazard);
              return items.length ? (
                <ul className="space-y-2">
                  {items.map((a) => (
                    <AlertRow key={a.id} a={a} onChange={reload} />
                  ))}
                </ul>
              ) : (
                <Empty>{status === "open" ? "No live condition currently crosses an alert threshold in Karnataka." : "No alerts with this status."}</Empty>
              );
            }}
          </Async>
        </Card>
        <Card title="Live event stream" actions={<span className={`text-[11px] ${connected ? "text-emerald-400" : "text-slate-500"}`}>{connected ? "connected" : "offline"}</span>}>
          {events.length ? (
            <ul className="space-y-1 text-xs">
              {events.map((e, i) => (
                <li key={`${e.emitted_at}-${i}`} className="border-b border-line/50 pb-1">
                  <span className="text-amber-300">{label(e.type)}</span> <span className="text-slate-300">{e.title ?? ""}</span>
                  <span className="block text-[10px] text-slate-500">{fmtDateTime(e.emitted_at)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <Empty>Waiting for alert events (server-sent events)…</Empty>
          )}
          <Source>Streamed from the backend as alerts are created, escalated, acknowledged or resolved.</Source>
        </Card>
      </div>
    </div>
  );
}
