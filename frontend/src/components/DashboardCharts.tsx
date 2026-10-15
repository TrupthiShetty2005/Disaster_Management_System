import type { ReactNode } from "react";
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
import { Bar, Doughnut, Line } from "react-chartjs-2";
import type { AnalyticsBundle } from "../types/api";

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

export function DashboardCharts({ data }: { data: AnalyticsBundle }) {
  const rainAvailable = Boolean(data.rainfallAvailable && data.rainfallTrend.some((v) => v != null));
  const rainfall = {
    labels: data.rainfallLabels?.length ? data.rainfallLabels : data.labels,
    datasets: [
      {
        label: data.rainfallSource === "nasa-power" ? "NASA POWER PRECTOTCORR (mm/day)" : "Rainfall (mm)",
        data: data.rainfallTrend,
        borderColor: "#38bdf8",
        backgroundColor: "#38bdf833",
        fill: true,
        tension: 0.35,
        spanGaps: true,
      },
    ],
  };
  const risk = {
    labels: data.labels,
    datasets: [{ label: "Risk index", data: data.riskTrend, borderColor: "#f59e0b", tension: 0.35 }],
  };
  const flood = {
    labels: data.labels,
    datasets: [{ label: "Flood km²", data: data.floodAreaTrend ?? [], backgroundColor: "#0ea5e9aa" }],
  };
  const pop = {
    labels: data.labels,
    datasets: [{ label: "People (thousands)", data: data.affectedPopulation, backgroundColor: "#ef4444aa" }],
  };
  const util = {
    labels: data.labels,
    datasets: [{ label: "Resource %", data: data.resourceUtilization, borderColor: "#34d399", tension: 0.3 }],
  };
  const severity = {
    labels: ["Low", "Moderate", "High", "Severe"],
    datasets: [
      {
        data: data.severityMix ?? [],
        backgroundColor: ["#22c55e", "#eab308", "#f97316", "#ef4444"],
      },
    ],
  };
  const popOk = data.populationAvailable === true;
  const utilOk = data.resourceUtilizationAvailable === true;
  const floodOk = data.floodAreaAvailable === true;
  const sevOk = data.severityMixAvailable === true;

  const doughnutOpts = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: axis.plugins,
  };

  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      <ChartCard
        title={
          rainAvailable
            ? data.rainfallSource === "nasa-power"
              ? "NASA POWER rainfall (mm/day)"
              : "Rainfall trend"
            : "Rainfall — UNAVAILABLE"
        }
      >
        {rainAvailable ? (
          <Line data={rainfall} options={axis} />
        ) : (
          <p className="pt-8 text-center text-xs text-slate-500">
            No NASA POWER daily PRECTOTCORR series for this AOI. Flood-expansion km² is not shown as rainfall.
          </p>
        )}
      </ChartCard>
      <ChartCard title={data.riskTrend?.some((v) => typeof v === "number" && v !== 0) ? "Risk trend" : "Risk trend — UNAVAILABLE"}>
        {data.riskTrend?.some((v) => typeof v === "number" && v !== 0) ? (
          <Line data={risk} options={axis} />
        ) : (
          <p className="pt-8 text-center text-xs text-slate-500">No measured risk-trend series. Zeros are not charted.</p>
        )}
      </ChartCard>
      <ChartCard title={floodOk ? "Flood area trend" : "Flood area — UNAVAILABLE"}>
        {floodOk ? (
          <Bar data={flood} options={axis} />
        ) : (
          <p className="pt-8 text-center text-xs text-slate-500">No measured flood-area time series for this AOI.</p>
        )}
      </ChartCard>
      <ChartCard title={popOk ? "Population affected" : "Population — UNAVAILABLE"}>
        {popOk ? (
          <Bar data={pop} options={axis} />
        ) : (
          <p className="pt-8 text-center text-xs text-slate-500">No census or population-impact feed. Zeros are not shown as measured impact.</p>
        )}
      </ChartCard>
      <ChartCard title={utilOk ? "Resource utilization" : "Resource utilization — UNAVAILABLE"}>
        {utilOk ? (
          <Line data={util} options={axis} />
        ) : (
          <p className="pt-8 text-center text-xs text-slate-500">No live rescue inventory. Zeros are not shown as utilization.</p>
        )}
      </ChartCard>
      <ChartCard title={sevOk ? "Disaster severity" : "Disaster severity — UNAVAILABLE"}>
        {sevOk ? (
          <Doughnut data={severity} options={doughnutOpts} />
        ) : (
          <p className="pt-8 text-center text-xs text-slate-500">No severity mix to chart.</p>
        )}
      </ChartCard>
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="h-48 rounded border border-line bg-panel p-3">
      <p className="mb-1 text-[11px] uppercase tracking-widest text-slate-500">{title}</p>
      <div className="h-[148px]">{children}</div>
    </div>
  );
}
