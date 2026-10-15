import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Tooltip,
  Legend,
} from "chart.js";
import { Line, Bar } from "react-chartjs-2";
import type { AnalyticsBundle } from "../types/api";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Tooltip, Legend);

const opts = { responsive: true, plugins: { legend: { labels: { color: "#94a3b8" } } }, scales: { x: { ticks: { color: "#64748b" } }, y: { ticks: { color: "#64748b" } } } };

export function TrendCharts({ data }: { data: AnalyticsBundle }) {
  const rainOk = Boolean(data.rainfallAvailable && data.rainfallTrend.some((v) => v != null));
  const popOk = data.populationAvailable === true;
  const utilOk = data.resourceUtilizationAvailable === true;
  const line = {
    labels: rainOk && data.rainfallLabels?.length ? data.rainfallLabels : data.labels,
    datasets: [
      { label: "Risk", data: data.riskTrend, borderColor: "#f59e0b", tension: 0.3 },
      ...(rainOk ? [{ label: "Rain mm", data: data.rainfallTrend, borderColor: "#38bdf8", tension: 0.3 }] : []),
    ],
  };
  const bar = {
    labels: data.labels,
    datasets: [
      ...(popOk ? [{ label: "People (thousands)", data: data.affectedPopulation, backgroundColor: "#ef4444aa" }] : []),
      ...(utilOk ? [{ label: "Resource %", data: data.resourceUtilization, backgroundColor: "#34d399aa" }] : []),
    ],
  };
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="rounded border border-line bg-panel p-3">
        <p className="mb-2 text-xs uppercase tracking-widest text-slate-500">
          {rainOk ? "Risk & rainfall" : "Risk (rainfall UNAVAILABLE)"}
        </p>
        <Line data={line} options={opts} />
      </div>
      <div className="rounded border border-line bg-panel p-3">
        <p className="mb-2 text-xs uppercase tracking-widest text-slate-500">
          {popOk || utilOk ? "Population & resources" : "Population & resources — UNAVAILABLE"}
        </p>
        {bar.datasets.length ? (
          <Bar data={bar} options={opts} />
        ) : (
          <p className="pt-8 text-center text-xs text-slate-500">
            No census or rescue-inventory feed. Zeros are not charted as measured impact or utilization.
          </p>
        )}
      </div>
    </div>
  );
}
