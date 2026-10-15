import { useState } from "react";
import { Breadcrumbs } from "../components/Breadcrumbs";
import { DataTable } from "../components/DataTable";
import { RescuePlanningMap } from "../components/RescuePlanningMap";
import { StatusBadge } from "../components/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "../components/Feedback";
import { useAsync } from "../hooks/useAsync";
import { dashboardLayerView } from "./DashboardPage";
import { fetchCenters, fetchResources } from "../services/ops";
import { decideRescuePlan, fetchRescuePriorities, generateRescuePlan } from "../services/rescue";
import type { RescuePlan } from "../types/api";

export function RescuePage() {
  const resources = useAsync(fetchResources, []);
  const centers = useAsync(fetchCenters, []);
  const priorities = useAsync(fetchRescuePriorities, []);
  const [plan, setPlan] = useState<RescuePlan | null>(null);
  const [busy, setBusy] = useState(false);
  const [notes, setNotes] = useState("");
  const [planError, setPlanError] = useState<string | null>(null);

  const resourceView = dashboardLayerView({
    loading: resources.loading,
    error: resources.error,
    hasPayload: Boolean(resources.data),
  });
  const centerView = dashboardLayerView({
    loading: centers.loading,
    error: centers.error,
    hasPayload: Boolean(centers.data),
  });
  const priorityView = dashboardLayerView({
    loading: priorities.loading,
    error: priorities.error,
    hasPayload: Boolean(priorities.data),
  });
  const inv = resources.data?.items ?? [];
  const prio = priorities.data?.items ?? [];
  const shelterRows = centers.data?.items ?? [];

  return (
    <div className="space-y-4">
      <Breadcrumbs items={[{ to: "/dashboard", label: "Command dashboard" }, { label: "Rescue planning" }]} />
      <p className="text-xs text-slate-500">
        In REAL DATA mode there is no live rescue-inventory API — seeded boats/centers are hidden. Generate plan returns
        unavailable rather than fabricating units. Not an official dispatch system.
      </p>
      <div className="grid gap-3 lg:grid-cols-2">
        <div>
          <h3 className="mb-2 text-xs uppercase tracking-widest text-slate-500">Priority incidents</h3>
          {priorityView === "loading" ? <LoadingState /> : null}
          {priorityView === "error" ? <ErrorState message={priorities.error ?? "Priorities unavailable"} /> : null}
          {priorityView === "empty" || (priorityView === "ready" && prio.length === 0) ? (
            <EmptyState message="No live rescue priorities. Seeded incidents are not shown." />
          ) : null}
          {priorityView === "ready" && prio.length ? (
            <DataTable
              columns={["Title", "Score", "Level", "People"]}
              rows={prio.map((p) => [p.title, String(p.score), p.level, String(p.people_affected)])}
            />
          ) : null}
        </div>
        <div>
          <h3 className="mb-2 text-xs uppercase tracking-widest text-slate-500">Resource inventory</h3>
          {resourceView === "loading" ? <LoadingState /> : null}
          {resourceView === "error" ? <ErrorState message={resources.error ?? "Resources unavailable"} /> : null}
          {resourceView === "empty" || (resourceView === "ready" && inv.length === 0) ? (
            <EmptyState message="No live rescue inventory. Seeded boats/units are not shown." />
          ) : null}
          {resourceView === "ready" && inv.length ? (
            <DataTable
              columns={["Name", "Type", "Status", "Cap"]}
              rows={inv.map((r) => [r.name, r.resource_type, r.status, String(r.capacity ?? r.personnel)])}
            />
          ) : null}
        </div>
      </div>
      <button
        type="button"
        disabled={busy}
        className="rounded border border-amber-500/40 px-4 py-2 text-sm text-amber-200"
        onClick={async () => {
          setBusy(true);
          setPlanError(null);
          try {
            setPlan(await generateRescuePlan());
          } catch (err) {
            setPlan(null);
            setPlanError(err instanceof Error ? err.message : "Rescue plan unavailable");
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "Generating…" : "Generate Rescue Plan"}
      </button>
      {planError ? <ErrorState message={planError} /> : null}
      <div className="h-[400px]">
        <RescuePlanningMap plan={plan} resources={inv} shelters={centers.data?.items ?? []} />
      </div>
      {plan ? (
        <section className="space-y-3 rounded border border-line bg-panel p-3">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge value={plan.decision} />
            <StatusBadge value={plan.plan.priority.level ?? "n/a"} />
            <span className="text-xs text-slate-500">{plan.plan.estimate_label}</span>
          </div>
          <p className="text-sm">
            {plan.plan.incident.title} · pop {plan.plan.affected_population} · ETA {plan.plan.estimated_response_time} min
          </p>
          <h4 className="text-xs uppercase tracking-widest text-slate-500">Recommended deployments</h4>
          <ul className="list-disc pl-5 text-sm text-slate-300">
            {plan.plan.recommended_allocation.map((a) => (
              <li key={a.resource_id}>
                {a.name} ({a.type})
              </li>
            ))}
          </ul>
          <h4 className="text-xs uppercase tracking-widest text-slate-500">Explanation</h4>
          <ul className="list-disc pl-5 text-sm text-slate-400">
            {plan.plan.reasoning.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
          {plan.plan.warnings.map((w) => (
            <p key={w} className="text-sm text-amber-300">
              {w}
            </p>
          ))}
          <input
            className="w-full rounded border border-line bg-black/30 px-2 py-1 text-sm"
            placeholder="Override notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
          <div className="flex flex-wrap gap-2">
            {(["accept", "modify", "reject"] as const).map((action) => (
              <button
                key={action}
                type="button"
                className="rounded border border-line px-3 py-1 text-sm capitalize text-slate-200"
                onClick={async () => {
                  try {
                    setPlan(await decideRescuePlan(plan.id, action, notes));
                    setPlanError(null);
                  } catch (err) {
                    setPlanError(err instanceof Error ? err.message : "Decision failed");
                  }
                }}
              >
                {action}
              </button>
            ))}
          </div>
        </section>
      ) : null}
      <div>
        <h3 className="mb-2 text-xs uppercase tracking-widest text-slate-500">Shelters</h3>
        {centerView === "loading" ? <LoadingState /> : null}
        {centerView === "error" ? <ErrorState message={centers.error ?? "Shelters unavailable"} /> : null}
        {centerView === "empty" || (centerView === "ready" && shelterRows.length === 0) ? (
          <EmptyState message="No live evacuation-center inventory. Seeded shelters are not shown." />
        ) : null}
        {centerView === "ready" && shelterRows.length ? (
          <DataTable
            columns={["Name", "Occupied", "Capacity", "Status"]}
            rows={shelterRows.map((c) => [c.name, String(c.occupied), String(c.capacity), c.status])}
          />
        ) : null}
      </div>
    </div>
  );
}
