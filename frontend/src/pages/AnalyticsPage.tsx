import { Bar, Line } from "react-chartjs-2";
import { getAnalytics } from "../api/endpoints";
import type { Analytics } from "../api/types";
import { baseOptions, shortDate } from "../charts/setup";
import { Async, Card, Empty, ErrorBox, PageHeader, Source } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { fmt, fmtDate, inr, label } from "../lib/format";

const PALETTE = ["#f59e0b", "#38bdf8", "#34d399", "#f472b6", "#a78bfa", "#ef4444", "#facc15", "#94a3b8"];
const HAZARD_COLOR: Record<string, string> = { flood: "#38bdf8", rain: "#2563eb", fire: "#f97316", fire_danger: "#ef4444", gdacs: "#a78bfa" };

function Fires({ f }: { f: Analytics["fires"] }) {
  if (f.status !== "live") return <ErrorBox message={`FIRMS unavailable: ${f.detail ?? ""}`} />;
  const stacked = baseOptions<"bar">("detections");
  stacked.scales = { x: { ...stacked.scales?.x, stacked: true }, y: { ...stacked.scales?.y, stacked: true } };
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <div className="h-64">
        <Bar
          data={{
            labels: (f.days ?? []).map(shortDate),
            datasets: [
              { label: "Vegetation / open fires", data: f.vegetation ?? [], backgroundColor: "#f97316" },
              { label: "Industrial heat sources", data: f.industrial ?? [], backgroundColor: "#475569" },
            ],
          }}
          options={stacked}
        />
      </div>
      <div className="h-64">
        <Bar
          data={{
            labels: Object.keys(f.by_district ?? {}),
            datasets: [{ label: "Fire detections by district (7 d, excl. industrial)", data: Object.values(f.by_district ?? {}), backgroundColor: "#ef4444" }],
          }}
          options={{ ...baseOptions<"bar">(), indexAxis: "y" }}
        />
      </div>
    </div>
  );
}

function Rain({ r }: { r: Analytics["rain"] }) {
  if (r.status !== "live") return <ErrorBox message={`Open-Meteo unavailable: ${r.detail ?? ""}`} />;
  return (
    <div className="grid gap-3 md:grid-cols-[1fr_260px]">
      <div className="h-64">
        <Bar
          data={{
            labels: (r.dates ?? []).map(shortDate),
            datasets: [{ label: "Karnataka mean daily rainfall (grey observed, blue forecast)", data: r.state_mean_mm ?? [], backgroundColor: (r.forecast ?? []).map((f) => (f ? "rgba(56,189,248,0.6)" : "rgba(226,232,240,0.7)")) }],
          }}
          options={baseOptions<"bar">("mm")}
        />
      </div>
      <div>
        <p className="mb-1 text-xs text-slate-500">Wettest districts, last 30 days</p>
        <ul className="space-y-0.5 text-sm">
          {(r.wettest_30d ?? []).map((d) => (
            <li key={d.name} className="flex justify-between">
              <span className="text-slate-300">{d.name}</span>
              <span className="text-sky-300">{fmt(d.mm)} mm</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function Rivers({ r }: { r: Analytics["rivers"] }) {
  if (r.status !== "live") return <ErrorBox message={`GloFAS unavailable: ${r.detail ?? ""}`} />;
  const stations = r.stations ?? [];
  if (!stations.length) return <Empty>No river data.</Empty>;
  return (
    <div className="h-72">
      <Line
        data={{
          labels: stations[0].dates.map(shortDate),
          datasets: stations.map((s, i) => ({
            label: s.name,
            data: s.discharge.map((v) => (v !== null && s.q2 ? Math.round((v / s.q2) * 100) : null)),
            borderColor: PALETTE[i % PALETTE.length],
            borderWidth: 1.5,
            pointRadius: 0,
            segment: { borderDash: (ctx: { p1DataIndex: number }) => ((s.dates[ctx.p1DataIndex] ?? "") >= s.forecast_from ? [4, 3] : undefined) },
          })),
        }}
        options={baseOptions<"line">("% of 2-year flood discharge")}
      />
    </div>
  );
}

function AlertHistory({ a }: { a: Analytics["alerts"] }) {
  const opts = baseOptions<"bar">("alerts raised");
  opts.scales = { x: { ...opts.scales?.x, stacked: true }, y: { ...opts.scales?.y, stacked: true } };
  if (!a.total_30d) return <Empty>No alerts raised in the last 30 days.</Empty>;
  return (
    <div className="h-56">
      <Bar
        data={{
          labels: a.days.map(shortDate),
          datasets: Object.entries(a.series).map(([h, v]) => ({ label: label(h), data: v, backgroundColor: HAZARD_COLOR[h] ?? "#94a3b8" })),
        }}
        options={opts}
      />
    </div>
  );
}

export default function AnalyticsPage() {
  const state = useAsync(getAnalytics, [], 900_000);
  return (
    <div className="space-y-3">
      <PageHeader title="Analytics" subtitle="Trends computed from the live feeds and from what this system has recorded: fire activity, rainfall, river behaviour against flood thresholds, alert history and mapped losses." />
      <Async state={state} loadingText="Aggregating live feeds…">
        {(d) => (
          <>
            <Card title="Satellite fire activity, last 7 days">
              <Fires f={d.fires} />
              <Source>NASA FIRMS VIIRS + MODIS. Industrial = detections inside persistent heat-source clusters.</Source>
            </Card>
            <Card title="Rainfall, 30 days observed + 7 days forecast">
              <Rain r={d.rain} />
              <Source>Open-Meteo, averaged over the 31 district headquarters.</Source>
            </Card>
            <Card title="Rivers relative to their 2-year flood (dashed = forecast)">
              <Rivers r={d.rivers} />
              <Source>GloFAS v4 discharge divided by each station's Gumbel 2-year return level. 100% = a flow reached on average once every two monsoons.</Source>
            </Card>
            <div className="grid gap-3 lg:grid-cols-2">
              <Card title={`Alerts raised (30 days: ${d.alerts.total_30d})`}>
                <AlertHistory a={d.alerts} />
              </Card>
              <Card title="Fire detections recorded by this system (24 h rolling)">
                {d.fire_history.times.length > 1 ? (
                  <div className="h-56">
                    <Line
                      data={{ labels: d.fire_history.times.map((t) => fmtDate(t)), datasets: [{ label: "FIRMS detections in Karnataka, previous 24 h", data: d.fire_history.detections_24h, borderColor: "#f97316", pointRadius: 2 }] }}
                      options={baseOptions<"line">()}
                    />
                  </div>
                ) : (
                  <Empty>This history builds up as the backend refreshes every 30 minutes ({d.fire_history.times.length} sample so far).</Empty>
                )}
              </Card>
            </div>
            <Card title="Mapped losses">
              {d.analyses.length ? (
                <table className="w-full text-xs">
                  <thead className="text-left text-slate-500">
                    <tr>
                      <th className="py-1">Analysis</th>
                      <th>Date</th>
                      <th className="text-right">Hazard km²</th>
                      <th className="text-right">Buildings</th>
                      <th className="text-right">Road km</th>
                      <th className="text-right">Loss</th>
                    </tr>
                  </thead>
                  <tbody>
                    {d.analyses.map((a) => (
                      <tr key={a.id} className="border-t border-line/50">
                        <td className="py-1 text-slate-200">
                          {label(a.kind)} · {a.area_name}
                        </td>
                        <td className="text-slate-400">{fmtDate(a.created_at)}</td>
                        <td className="text-right">{fmt(a.hazard_km2, 2)}</td>
                        <td className="text-right">{fmt(a.buildings)}</td>
                        <td className="text-right">{fmt(a.road_km, 1)}</td>
                        <td className="text-right text-red-300">{inr(a.loss_crore)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <Empty>No satellite analyses yet.</Empty>
              )}
            </Card>
          </>
        )}
      </Async>
    </div>
  );
}
