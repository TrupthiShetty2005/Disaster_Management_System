import { useEffect, useState } from "react";
import { Bar, Doughnut, Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  ArcElement,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { Breadcrumbs } from "../components/Breadcrumbs";
import { EmptyState, ErrorState, LoadingState } from "../components/Feedback";
import { KpiCard } from "../components/KpiCard";
import { fetchAnalyticsOverview, exportUrl, type AnalyticsOverview } from "../services/analytics";
import type { ReactNode } from "react";
import { isMockMode } from "../services/apiClient";
import { seriesLooksMeasured } from "../services/analytics";
import { DEMO_LOCATION_ID } from "../constants/demo";

ChartJS.register(ArcElement, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Tooltip, Legend, Filler);

const axis = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { labels: { color: "#94a3b8", boxWidth: 10, font: { size: 11 } } } },
  scales: {
    x: { ticks: { color: "#64748b", font: { size: 10 } }, grid: { color: "#243044" } },
    y: { ticks: { color: "#64748b", font: { size: 10 } }, grid: { color: "#243044" } },
  },
};

export function AnalyticsPage() {
  const [disasterType, setDisasterType] = useState("flood");
  const [severity, setSeverity] = useState("");
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = { disaster_type: disasterType };
      if (isMockMode()) params.location_id = DEMO_LOCATION_ID;
      if (severity) params.severity = severity;
      setData(await fetchAnalyticsOverview(params));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading && !data) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!data) return <EmptyState message="No analytics yet." />;

  const s = data.series;
  const k = data.kpis;

  return (
    <div className="space-y-4">
      <Breadcrumbs items={[{ to: "/dashboard", label: "Command dashboard" }, { label: "Disaster analytics" }]} />
      <p className="text-xs text-slate-500">{data.estimate_label}</p>
      <div className="flex flex-wrap gap-2 text-xs">
        <label>
          Disaster type
          <select className="ml-1 rounded border border-line bg-black/30 px-2 py-1" value={disasterType} onChange={(e) => setDisasterType(e.target.value)}>
            <option value="flood">flood</option>
            <option value="landslide">landslide</option>
            <option value="cyclone">cyclone</option>
          </select>
        </label>
        <label>
          Severity
          <select className="ml-1 rounded border border-line bg-black/30 px-2 py-1" value={severity} onChange={(e) => setSeverity(e.target.value)}>
            <option value="">all</option>
            <option value="high">high</option>
            <option value="medium">medium</option>
            <option value="severe">severe</option>
          </select>
        </label>
        <button type="button" className="rounded border border-line px-3 py-1" onClick={() => void load()}>
          Apply filters
        </button>
        <a className="rounded border border-amber-500/40 px-3 py-1 text-amber-200" href={exportUrl("analytics")}>
          Export CSV
        </a>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
        <KpiCard label="Disasters" value={String(k.total_disasters ?? "—")} />
        <KpiCard
          label="Affected pop."
          value={k.population_note === "no live census feed" ? "UNAVAILABLE" : String(k.affected_population ?? "—")}
          hint={typeof k.population_note === "string" ? k.population_note : undefined}
        />
        <KpiCard label="Flooded km²" value={String(k.flooded_area ?? "—")} />
        <KpiCard label="Alerts" value={String(k.alert_count ?? "—")} />
        <KpiCard
          label="Avg response min"
          value={k.rescue_inventory_available === false ? "UNAVAILABLE" : String(k.average_response_time ?? "—")}
        />
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <Chart title={seriesLooksMeasured(s.disaster_frequency) ? "Disaster frequency" : "Disaster frequency — UNAVAILABLE"}>
          {seriesLooksMeasured(s.disaster_frequency) ? (
            <Bar data={{ labels: s.labels, datasets: [{ label: "Events", data: s.disaster_frequency, backgroundColor: "#f59e0baa" }] }} options={axis} />
          ) : (
            <p className="pt-8 text-center text-xs text-slate-500">No disaster-frequency series. Zeros are not charted as events.</p>
          )}
        </Chart>
        <Chart title={seriesLooksMeasured(s.risk_trend) ? "Risk trends" : "Risk trends — UNAVAILABLE"}>
          {seriesLooksMeasured(s.risk_trend) ? (
            <Line data={{ labels: s.labels, datasets: [{ label: "Risk", data: s.risk_trend, borderColor: "#f59e0b" }] }} options={axis} />
          ) : (
            <p className="pt-8 text-center text-xs text-slate-500">No measured risk-trend series. Zeros are not charted.</p>
          )}
        </Chart>
        <Chart title={seriesLooksMeasured(s.affected_population) && k.population_note !== "no live census feed" ? "Affected population" : "Affected population — UNAVAILABLE"}>
          {seriesLooksMeasured(s.affected_population) && k.population_note !== "no live census feed" ? (
            <Bar data={{ labels: s.labels, datasets: [{ label: "People (k)", data: s.affected_population, backgroundColor: "#ef4444aa" }] }} options={axis} />
          ) : (
            <p className="pt-8 text-center text-xs text-slate-500">No census feed. Zeros are not charted as measured impact.</p>
          )}
        </Chart>
        <Chart title={Object.values(s.damage_by_category).some((n) => Number(n) > 0) ? "Damage by category" : "Damage by category — UNAVAILABLE"}>
          {Object.values(s.damage_by_category).some((n) => Number(n) > 0) ? (
          <Doughnut
            data={{
              labels: Object.keys(s.damage_by_category),
              datasets: [{ data: Object.values(s.damage_by_category), backgroundColor: ["#38bdf8", "#f97316", "#22c55e"] }],
            }}
            options={{ responsive: true, maintainAspectRatio: false }}
          />
          ) : (
            <p className="pt-8 text-center text-xs text-slate-500">No measured damage inventory to chart.</p>
          )}
        </Chart>
        <Chart title={k.rescue_inventory_available === true ? "Resource utilization" : "Resource utilization — UNAVAILABLE"}>
          {k.rescue_inventory_available === true ? (
            <Line data={{ labels: s.labels, datasets: [{ label: "%", data: s.resource_utilization, borderColor: "#34d399" }] }} options={axis} />
          ) : (
            <p className="pt-8 text-center text-xs text-slate-500">No live rescue inventory. Zeros are not charted as utilization.</p>
          )}
        </Chart>
        <Chart title={seriesLooksMeasured(Object.values(s.alert_severity)) ? "Alert severity" : "Alert severity — UNAVAILABLE"}>
          {seriesLooksMeasured(Object.values(s.alert_severity)) ? (
          <Doughnut
            data={{
              labels: Object.keys(s.alert_severity),
              datasets: [{ data: Object.values(s.alert_severity), backgroundColor: ["#22c55e", "#eab308", "#f97316", "#ef4444"] }],
            }}
            options={{ responsive: true, maintainAspectRatio: false }}
          />
          ) : (
            <p className="pt-8 text-center text-xs text-slate-500">No alert-severity counts to chart.</p>
          )}
        </Chart>
        <Chart title={seriesLooksMeasured(s.flood_expansion) ? "Flood expansion" : "Flood expansion — UNAVAILABLE"}>
          {seriesLooksMeasured(s.flood_expansion) ? (
            <Bar data={{ labels: s.labels, datasets: [{ label: "km²", data: s.flood_expansion, backgroundColor: "#0ea5e9aa" }] }} options={axis} />
          ) : (
            <p className="pt-8 text-center text-xs text-slate-500">No measured flood-area series. Zeros are not charted as expansion.</p>
          )}
        </Chart>
        <Chart title={seriesLooksMeasured(s.response_performance) ? "Response performance" : "Response performance — UNAVAILABLE"}>
          {seriesLooksMeasured(s.response_performance) ? (
            <Line data={{ labels: s.labels, datasets: [{ label: "Index", data: s.response_performance, borderColor: "#a78bfa" }] }} options={axis} />
          ) : (
            <p className="pt-8 text-center text-xs text-slate-500">No live response-time feed. Zeros are not charted as performance.</p>
          )}
        </Chart>
      </div>
    </div>
  );
}

function Chart({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="h-48 rounded border border-line bg-panel p-3">
      <p className="mb-1 text-[11px] uppercase tracking-widest text-slate-500">{title}</p>
      <div className="h-[148px]">{children}</div>
    </div>
  );
}
