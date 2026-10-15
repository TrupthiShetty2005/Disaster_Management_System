import { DataTable } from "../components/DataTable";
import { StatusBadge } from "../components/StatusBadge";
import { LoadingState } from "../components/Feedback";
import { useAsync } from "../hooks/useAsync";
import { fetchRiskZones } from "../services/risk";

export function RiskPage() {
  const { data, loading } = useAsync(fetchRiskZones, []);
  if (loading) return <LoadingState />;
  const items = data?.items ?? [];
  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-400">Predictive risk scores from demo models. Plug in real ensembles later.</p>
      <DataTable
        columns={["Zone", "Hazard", "Score", "Level"]}
        rows={items.map((z) => [z.name, z.hazard_type, z.risk_score.toFixed(2), z.risk_level])}
      />
      <div className="flex gap-2">
        {items.map((z) => (
          <StatusBadge key={z.id} value={z.risk_level} />
        ))}
      </div>
    </div>
  );
}
