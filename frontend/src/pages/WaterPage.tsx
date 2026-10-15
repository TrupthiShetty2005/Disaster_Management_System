import { useMemo, useState } from "react";
import { Line } from "react-chartjs-2";
import { getWaterStations } from "../api/endpoints";
import type { StationReport } from "../api/types";
import { baseOptions, shortDate } from "../charts/setup";
import { Async, Card, Kpi, LevelBadge, PageHeader, Source } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { fmt, fmtDate, levelColor } from "../lib/format";
import { KarnatakaMap } from "../maps/KarnatakaMap";
import { StationMarkers } from "../maps/layers";

function DischargeChart({ s }: { s: StationReport }) {
  const data = useMemo(() => {
    const series = s.series ?? [];
    const labels = series.map((p) => shortDate(p.date));
    const observed = series.map((p) => (p.forecast ? null : p.discharge));
    const lastObs = series.findLastIndex((p) => !p.forecast);
    const fc = (k: "median" | "p25" | "p75" | "min" | "max") => series.map((p, i) => (p.forecast || i === lastObs ? (i === lastObs ? p.discharge : p[k]) : null));
    const flat = (v: number | undefined) => series.map(() => v ?? null);
    const th = s.thresholds;
    return {
      labels,
      datasets: [
        { label: "Ensemble max", data: fc("max"), borderColor: "transparent", backgroundColor: "rgba(56,189,248,0.08)", pointRadius: 0, fill: "+1" },
        { label: "Ensemble min", data: fc("min"), borderColor: "transparent", pointRadius: 0, fill: false },
        { label: "Forecast p75", data: fc("p75"), borderColor: "transparent", backgroundColor: "rgba(56,189,248,0.22)", pointRadius: 0, fill: "+1" },
        { label: "Forecast p25", data: fc("p25"), borderColor: "transparent", pointRadius: 0, fill: false },
        { label: "Forecast median", data: fc("median"), borderColor: "#38bdf8", borderDash: [5, 4], borderWidth: 2, pointRadius: 0 },
        { label: "GloFAS daily discharge", data: observed, borderColor: "#e2e8f0", borderWidth: 2, pointRadius: 0 },
        ...(th
          ? [
              { label: `2-yr flood (${fmt(th.q2)})`, data: flat(th.q2), borderColor: levelColor("WATCH"), borderWidth: 1, pointRadius: 0 },
              { label: `5-yr flood (${fmt(th.q5)})`, data: flat(th.q5), borderColor: levelColor("WARNING"), borderWidth: 1, pointRadius: 0 },
              { label: `20-yr flood (${fmt(th.q20)})`, data: flat(th.q20), borderColor: levelColor("SEVERE"), borderWidth: 1, pointRadius: 0 },
            ]
          : []),
      ],
    };
  }, [s]);
  const options = baseOptions<"line">("m³/s");
  options.plugins = {
    ...options.plugins,
    legend: { labels: { boxWidth: 12, font: { size: 10 }, filter: (item) => !/min|p25/.test(item.text) } },
  };
  return (
    <div className="h-80">
      <Line data={data} options={options} />
    </div>
  );
}

function StationDetail({ s }: { s: StationReport }) {
  const peak = s.forecast_peak;
  const th = s.thresholds;
  return (
    <Card
      title={
        <span>
          {s.name} <span className="text-sm text-slate-400">· {s.river} · {s.district}</span>
        </span>
      }
      actions={<LevelBadge level={s.status} />}
    >
      <div className="mb-3 grid grid-cols-2 gap-2 md:grid-cols-4">
        <Kpi label="Discharge today" value={fmt(s.current?.discharge)} hint={`m³/s · ${s.trend_7d_pct === null ? "—" : `${s.trend_7d_pct > 0 ? "+" : ""}${fmt(s.trend_7d_pct, 1)}%`} vs 7 days ago`} />
        <Kpi label="Of 2-year flood" value={`${fmt(s.percent_of_2yr_flood)}%`} hint={th ? `Q2 = ${fmt(th.q2)} m³/s` : "calibrating"} color={levelColor(s.current_level)} />
        <Kpi label="Predicted peak (30 d)" value={fmt(peak?.expected?.discharge)} hint={`median, ${fmtDate(peak?.expected?.date)} → ${s.predicted_level}`} color={levelColor(s.predicted_level)} />
        <Kpi label="Worst ensemble member" value={fmt(peak?.worst_case?.discharge)} hint={`${fmtDate(peak?.worst_case?.date)} · p75 ${fmt(peak?.upper_p75?.discharge)}`} />
      </div>
      <DischargeChart s={s} />
      {th ? (
        <p className="mt-2 text-xs text-slate-400">
          Return levels fitted to {th.record_years} seasonal maxima ({th.record_period}). Record: {fmt(th.record_max)} m³/s in {th.record_max_year}. Typical monsoon median: {fmt(th.season_median_flow)} m³/s.
        </p>
      ) : null}
      <Source>
        {s.source}. GloFAS river cell {s.glofas_cell.latitude.toFixed(3)}, {s.glofas_cell.longitude.toFixed(3)} (highest-flow cell next to the dam/gauge). {s.method}
      </Source>
    </Card>
  );
}

export default function WaterPage() {
  const state = useAsync(() => getWaterStations(true), [], 600_000);
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div className="space-y-3">
      <PageHeader
        title="River water levels & flood prediction"
        subtitle="Daily river discharge at 16 Karnataka dams and river gauges from the Copernicus GloFAS hydrological model. The 30-day ensemble forecast is compared with each river's own historical flood return levels to predict flood status."
      />
      <Async state={state} loadingText="Fetching GloFAS discharge for 16 stations…">
        {(d) => {
          const current = d.items.find((s) => s.id === selected) ?? d.items[0];
          return (
            <div className="grid gap-3 xl:grid-cols-[420px_1fr]">
              <div className="space-y-3">
                <KarnatakaMap height={340}>
                  <StationMarkers stations={d.items} onSelect={setSelected} />
                </KarnatakaMap>
                <Card title="Stations">
                  <table className="w-full text-xs">
                    <thead className="text-left text-slate-500">
                      <tr>
                        <th className="py-1">Station</th>
                        <th className="text-right">Now m³/s</th>
                        <th className="text-right">% Q2</th>
                        <th className="text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {d.items.map((s) => (
                        <tr key={s.id} onClick={() => setSelected(s.id)} className={`cursor-pointer border-t border-line/50 hover:bg-white/5 ${s.id === current?.id ? "bg-amber-500/10" : ""}`}>
                          <td className="py-1.5">
                            <p className="text-slate-200">{s.name}</p>
                            <p className="text-[10px] text-slate-500">{s.river}</p>
                          </td>
                          <td className="text-right text-slate-300">{fmt(s.current?.discharge)}</td>
                          <td className="text-right text-slate-400">{fmt(s.percent_of_2yr_flood)}</td>
                          <td className="text-right">
                            <LevelBadge level={s.status} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Card>
              </div>
              {current ? <StationDetail s={current} /> : null}
            </div>
          );
        }}
      </Async>
    </div>
  );
}
