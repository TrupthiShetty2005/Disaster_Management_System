import { useState } from "react";
import { Breadcrumbs } from "../components/Breadcrumbs";
import { AlertPanel } from "../components/AlertPanel";
import { SafetyBanner } from "../components/SafetyBanner";
import { DataTable } from "../components/DataTable";
import { ErrorState, LoadingState } from "../components/Feedback";
import { useAsync } from "../hooks/useAsync";
import { useAlertStream } from "../hooks/useAlertStream";
import { acknowledgeAlert, fetchAlerts, generateAlerts, resolveAlert } from "../services/alerts";
import { partitionAlerts } from "../utils/alertBuckets";
import type { AlertItem } from "../types/api";

export function AlertsPage() {
  const { data, loading, error } = useAsync(fetchAlerts, []);
  const [items, setItems] = useState<AlertItem[] | null>(null);
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const res = await fetchAlerts({ severity: severity || undefined, status: status || undefined });
      setItems(res.items);
      setGenError(null);
    } catch (err) {
      setGenError(err instanceof Error ? err.message : "Alert list refresh failed");
    }
  };

  useAlertStream(() => {
    void refresh();
  });

  if (loading && !items && !error) return <LoadingState />;
  const list = items ?? data?.items ?? [];
  const buckets = partitionAlerts(list);
  const onAck = async (id: string) => {
    try {
      const row = await acknowledgeAlert(id);
      setItems((prev) => (prev ?? list).map((a) => (a.id === id ? { ...a, ...row } : a)));
    } catch (err) {
      setGenError(err instanceof Error ? err.message : "Acknowledge failed");
    }
  };
  const onResolve = async (id: string) => {
    try {
      const row = await resolveAlert(id);
      setItems((prev) => (prev ?? list).map((a) => (a.id === id ? { ...a, ...row } : a)));
    } catch (err) {
      setGenError(err instanceof Error ? err.message : "Resolve failed");
    }
  };

  return (
    <div className="space-y-4">
      <Breadcrumbs items={[{ to: "/dashboard", label: "Command dashboard" }, { label: "Early warning alerts" }]} />
      <SafetyBanner />
      <div className="flex flex-wrap items-end gap-2">
        <label className="text-xs text-slate-400">
          Severity
          <select className="ml-1 rounded border border-line bg-black/30 px-2 py-1" value={severity} onChange={(e) => setSeverity(e.target.value)}>
            <option value="">all</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="WARNING">WARNING</option>
            <option value="WATCH">WATCH</option>
            <option value="INFO">INFO</option>
          </select>
        </label>
        <label className="text-xs text-slate-400">
          Status
          <select className="ml-1 rounded border border-line bg-black/30 px-2 py-1" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">all</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
            <option value="RESOLVED">RESOLVED</option>
          </select>
        </label>
        <button type="button" className="rounded border border-line px-3 py-1 text-sm" onClick={() => void refresh()}>
          Filter history
        </button>
        <button
          type="button"
          disabled={busy}
          className="rounded border border-amber-500/40 px-3 py-1 text-sm text-amber-200"
          onClick={async () => {
            setBusy(true);
            setGenError(null);
            try {
              const res = await generateAlerts();
              setItems(res.items);
            } catch (err) {
              setGenError(err instanceof Error ? err.message : "Alert generation failed");
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? "Generating…" : "Generate alerts"}
        </button>
      </div>
      {error && !items ? <ErrorState message={error} /> : null}
      {genError ? <ErrorState message={genError} /> : null}
      <p className="text-xs text-slate-500">
        Official government warnings, VisionGuard heuristic risk estimates, and persisted/history rows are listed
        separately. Heuristic items are not IMD/NDMA products.
      </p>
      <div className="grid gap-3 xl:grid-cols-3">
        <div className="h-[42vh]">
          <p className="mb-1 text-[11px] uppercase tracking-widest text-emerald-300">Official warnings</p>
          <AlertPanel items={buckets.official} showSafety onAck={onAck} onResolve={onResolve} />
        </div>
        <div className="h-[42vh]">
          <p className="mb-1 text-[11px] uppercase tracking-widest text-amber-200">Heuristic risk estimates</p>
          <AlertPanel items={buckets.heuristic} onAck={onAck} onResolve={onResolve} />
        </div>
        <div className="h-[42vh]">
          <p className="mb-1 text-[11px] uppercase tracking-widest text-slate-400">Historical / persisted</p>
          <AlertPanel items={buckets.historical} onAck={onAck} onResolve={onResolve} />
        </div>
      </div>
      <DataTable
        columns={["Severity", "Location", "Score", "Time", "Status"]}
        rows={list.map((a) => [
          a.severity,
          a.location_name || a.category,
          String(a.risk_score ?? "—"),
          a.issued_at,
          a.status ?? "ACTIVE",
        ])}
      />
    </div>
  );
}
