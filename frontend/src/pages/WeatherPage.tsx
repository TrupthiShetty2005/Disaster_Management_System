import { Line } from "react-chartjs-2";
import {
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";
import { DataTable } from "../components/DataTable";
import { KpiCard } from "../components/KpiCard";
import { StatusBadge } from "../components/StatusBadge";
import { EstimateCallout } from "../components/EstimateCallout";
import { ModuleProvenance } from "../components/DataModeBadge";
import { LoadingState, ErrorState } from "../components/Feedback";
import { LIVE_REGION } from "../constants/demo";
import { useAsync } from "../hooks/useAsync";
import { fetchAoi } from "../services/region";
import {
  fetchCycloneRisk,
  fetchFloodRisk,
  fetchRainfallAnalysis,
  fetchWeatherAlerts,
  fetchWeatherCurrent,
  fetchWeatherForecast,
  fetchWeatherHistory,
} from "../services/weather";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler);

const opts = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { labels: { color: "#94a3b8" } } },
  scales: {
    x: { ticks: { color: "#64748b" }, grid: { color: "#243044" } },
    y: { ticks: { color: "#64748b" }, grid: { color: "#243044" } },
  },
};

export function WeatherPage() {
  const current = useAsync(fetchWeatherCurrent, []);
  const forecast = useAsync(fetchWeatherForecast, []);
  const history = useAsync(fetchWeatherHistory, []);
  const rain = useAsync(fetchRainfallAnalysis, []);
  const flood = useAsync(fetchFloodRisk, []);
  const cyclone = useAsync(fetchCycloneRisk, []);
  const alerts = useAsync(fetchWeatherAlerts, []);
  const aoi = useAsync(fetchAoi, []);

  const w = current.data;
  const hist = history.data?.items ?? [];
  const labels = hist.map((h) => h.observed_at.slice(0, 10));
  const liveWx = Boolean(w?.provider_live);
  const histSource = hist[0]?.source ?? "";
  const riskKind = (flood.data?.estimate_label || "").includes("SIMULATED")
    ? "SIMULATED DATA"
    : liveWx || histSource === "nasa-power"
      ? "RULE-BASED ESTIMATE"
      : "SIMULATED DATA";

  return (
    <div className="space-y-4">
      <div className="grid gap-2 lg:grid-cols-2">
        <ModuleProvenance moduleKey="weather" title="Weather (current/forecast)" />
        <ModuleProvenance moduleKey="weather_history" title="Weather history" />
        <ModuleProvenance moduleKey="risk" title="VisionGuard calculated risk" />
        <ModuleProvenance moduleKey="imd" title="IMD official warnings" />
        <ModuleProvenance moduleKey="river_level" title="River / gauge level" />
      </div>
      <p className="text-xs text-slate-500">
        Weather is queried at the selected AOI
        {aoi.data ? ` (${aoi.data.aoi_name} · ${aoi.data.latitude.toFixed(4)}N, ${aoi.data.longitude.toFixed(4)}E)` : ` (${LIVE_REGION})`}
        . OpenWeather = current/forecast. NASA POWER = historical daily ~0.5° grid. IMD warnings only if a working key is
        configured. Risk scores are rule-based indexes, not official probabilities. River gauges are unavailable.
      </p>
      {current.loading ? <LoadingState /> : null}
      {current.error ? (
        <ErrorState message={`OpenWeather current unavailable: ${current.error}`} />
      ) : null}
      {forecast.error ? (
        <p className="text-xs text-rose-300">Forecast unavailable: {forecast.error}</p>
      ) : null}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Temperature" value={`${w?.temperature_c ?? "—"}°C`} hint={w?.conditions ?? "—"} />
        <KpiCard
          label="Rain / humidity"
          value={`${w?.rainfall_mm ?? "—"} mm`}
          hint={`${w?.humidity ?? "—"}% RH · ${w?.units?.rainfall_mm ?? "1h/3h window"}`}
        />
        <KpiCard label="Wind / pressure" value={`${w?.wind_speed_ms ?? "—"} m/s`} hint={`${w?.pressure_hpa ?? "—"} hPa`} />
        <KpiCard
          label="Visibility"
          value={`${w?.visibility_km ?? "—"} km`}
          hint={liveWx ? "LIVE · OpenWeather" : current.error ? "UNAVAILABLE" : "—"}
        />
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <KpiCard
          label="Flood risk index (heuristic)"
          value={`${flood.data?.flood_probability ?? "—"}%`}
          hint={flood.data?.estimate_label}
        />
        <KpiCard
          label="Storm / cyclone risk"
          value={`${cyclone.data?.cyclone_risk ?? "—"}`}
          hint={cyclone.data?.severity}
        />
        <KpiCard
          label="Short-term rainfall risk"
          value={`${rain.data?.short_term_risk ?? "—"}`}
          hint={`${rain.data?.label ?? "Rainfall"} · cum ${rain.data?.cumulative_mm ?? "—"} mm`}
        />
      </div>
      <EstimateCallout
        title="Flood risk"
        kind={riskKind}
        value={`${flood.data?.flood_probability ?? "—"}%`}
        factors={(flood.data?.factors ?? []).map((f) => ({ name: f.name, level: f.level }))}
      />
      <p className="text-xs text-slate-500">
        History: {histSource || (history.error ? `unavailable (${history.error})` : history.loading ? "loading…" : "—")}
        {histSource === "nasa-power" ? " · NASA POWER daily (not a forecast, not a gauge)" : ""}
        {flood.error ? ` · flood score unavailable (${flood.error})` : ""}
        {cyclone.error ? ` · cyclone score unavailable (${cyclone.error})` : ""}
      </p>
      <div className="grid gap-3 lg:grid-cols-2">
        <div className="h-52 rounded border border-line bg-panel p-3">
          <p className="mb-1 text-[11px] uppercase tracking-widest text-slate-500">Rainfall history</p>
          <Line
            options={opts}
            data={{
              labels,
              datasets: [{ label: "mm/day", data: hist.map((h) => h.rainfall_mm ?? null), borderColor: "#38bdf8", fill: true, backgroundColor: "#38bdf822", tension: 0.3, spanGaps: true }],
            }}
          />
        </div>
        <div className="h-52 rounded border border-line bg-panel p-3">
          <p className="mb-1 text-[11px] uppercase tracking-widest text-slate-500">Wind</p>
          <Line
            options={opts}
            data={{
              labels,
              datasets: [{ label: "m/s", data: hist.map((h) => h.wind_speed_ms ?? null), borderColor: "#f59e0b", tension: 0.3, spanGaps: true }],
            }}
          />
        </div>
      </div>
      <DataTable
        columns={["Start", "Rain mm", "Temp", "Wind", "Conditions"]}
        rows={(forecast.data?.items ?? []).map((f) => [
          f.period_start,
          String(f.rainfall_mm),
          String(f.temperature_c),
          String(f.wind_speed_ms),
          f.conditions,
        ])}
      />
      <section className="rounded border border-line bg-panel p-3">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-xs uppercase tracking-widest text-slate-500">Weather / risk alerts</h3>
          <StatusBadge value={alerts.data?.dispatch?.includes("no SMS") ? "info" : "warning"} />
        </div>
        <p className="mb-2 text-xs text-slate-500">
          {alerts.data?.dispatch}
          {alerts.data?.imd_source_status ? ` · IMD source: ${alerts.data.imd_source_status}` : ""}
          {alerts.data?.imd_status ? ` · ${alerts.data.imd_status}` : ""}
        </p>
        {alerts.data?.imd_source_status === "NOT_CONFIGURED" ? (
          <p className="border-t border-line py-2 text-sm text-rose-300">
            Official IMD warnings NOT_CONFIGURED — empty list is not an all-clear.
          </p>
        ) : null}
        {alerts.data?.imd_source_status === "UNAVAILABLE" ? (
          <p className="border-t border-line py-2 text-sm text-rose-300">
            Official IMD warnings UNAVAILABLE — provider failed; not an all-clear.
          </p>
        ) : null}
        {alerts.data?.imd_source_status === "LIVE_EMPTY" ? (
          <p className="border-t border-line py-2 text-sm text-amber-200">
            IMD responded with zero district warnings in this payload — not confirmation that no warnings exist.
          </p>
        ) : null}
        {(alerts.data?.items ?? []).map((a) => (
          <p key={a.id ?? a.title} className="border-t border-line py-2 text-sm text-slate-300">
            {a.title} — {a.message}
          </p>
        ))}
      </section>
    </div>
  );
}
