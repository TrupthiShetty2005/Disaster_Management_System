import { useMemo, useState } from "react";
import { Bar } from "react-chartjs-2";
import { CircleMarker, Tooltip } from "react-leaflet";
import { getRainfall, getWeather } from "../api/endpoints";
import type { RainDistrict } from "../api/types";
import { baseOptions, shortDate } from "../charts/setup";
import { Async, Card, ErrorBox, Kpi, LevelBadge, PageHeader, Source } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { fmt, fmtDate, fmtDateTime, label, RAIN_COLOR } from "../lib/format";
import { KarnatakaMap } from "../maps/KarnatakaMap";

function RainChart({ d }: { d: RainDistrict }) {
  const data = useMemo(() => {
    const s = d.series ?? [];
    return {
      labels: s.map((p) => shortDate(p.date)),
      datasets: [
        {
          label: "Daily rainfall (observed / forecast)",
          data: s.map((p) => p.rain_mm),
          backgroundColor: s.map((p) => (p.forecast ? "rgba(56,189,248,0.45)" : "rgba(226,232,240,0.7)")),
        },
      ],
    };
  }, [d]);
  return (
    <div className="h-56">
      <Bar data={data} options={baseOptions<"bar">("mm")} />
    </div>
  );
}

function WeatherPanel({ districtId }: { districtId: string }) {
  const w = useAsync(() => getWeather(districtId), [districtId], 900_000);
  return (
    <Async state={w} loadingText="Fetching OpenWeather observation…">
      {(d) => (
        <div className="space-y-2">
          {d.current ? (
            <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
              <Kpi label={`Now · ${d.current.station}`} value={`${fmt(d.current.temperature_c, 1)}°C`} hint={d.current.condition} />
              <Kpi label="Rain last hour" value={`${fmt(d.current.rain_1h_mm ?? 0, 1)} mm`} hint={`humidity ${d.current.humidity_pct}%`} color="#38bdf8" />
              <Kpi label="Wind" value={`${fmt(d.current.wind_speed_ms * 3.6)} km/h`} hint={d.current.wind_gust_ms ? `gusts ${fmt(d.current.wind_gust_ms * 3.6)} km/h` : undefined} />
              <Kpi label="Pressure" value={`${d.current.pressure_hpa} hPa`} hint={`observed ${fmtDateTime(new Date(d.current.observed_at * 1000).toISOString())}`} />
            </div>
          ) : (
            <ErrorBox message={`OpenWeather unavailable: ${d.unavailable?.current ?? "no data"}`} />
          )}
          {d.forecast ? (
            <div className="flex gap-1 overflow-x-auto pb-1 text-[11px]">
              {d.forecast.slice(0, 16).map((f) => (
                <div key={f.time} className="min-w-[70px] rounded border border-line p-1 text-center">
                  <p className="text-slate-500">{new Date(f.time * 1000).toLocaleString("en-IN", { weekday: "short", hour: "2-digit" })}</p>
                  <p className="text-slate-200">{fmt(f.temperature_c)}°</p>
                  <p className="text-sky-300">{fmt(f.rain_3h_mm, 1)} mm</p>
                  <p className="text-slate-500">{Math.round(f.pop * 100)}%</p>
                </div>
              ))}
            </div>
          ) : null}
          <Source>OpenWeather current conditions and 3-hourly forecast for the district headquarters.</Source>
        </div>
      )}
    </Async>
  );
}

export default function RainfallPage() {
  const state = useAsync(getRainfall, [], 1_800_000);
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div className="space-y-3">
      <PageHeader title="Rainfall & weather" subtitle="Observed rainfall for the last 30 days and the 7-day forecast for every Karnataka district, classified with IMD's 24-hour rainfall categories, plus live OpenWeather conditions." />
      <Async state={state} loadingText="Fetching Open-Meteo rainfall for 31 districts…">
        {(r) => {
          const sorted = [...r.items].sort((a, b) => b.forecast_7d_mm - a.forecast_7d_mm);
          const cur = r.items.find((d) => d.id === selected) ?? sorted[0];
          return (
            <div className="grid gap-3 xl:grid-cols-[460px_1fr]">
              <div className="space-y-3">
                <KarnatakaMap height={360}>
                  {r.items.map((d) => (
                    <CircleMarker
                      key={d.id}
                      center={[d.latitude, d.longitude]}
                      radius={6 + Math.min(14, Math.sqrt(d.forecast_7d_mm))}
                      pathOptions={{ color: "#0b1016", weight: 1, fillColor: RAIN_COLOR[d.category] ?? "#334155", fillOpacity: 0.85 }}
                      eventHandlers={{ click: () => setSelected(d.id) }}
                    >
                      <Tooltip>
                        {d.name}: {fmt(d.forecast_7d_mm)} mm next 7 days · peak {fmt(d.peak_day.rain_mm)} mm ({label(d.category)})
                      </Tooltip>
                    </CircleMarker>
                  ))}
                </KarnatakaMap>
                <Card title="Districts">
                  <div className="max-h-[420px] overflow-auto">
                    <table className="w-full text-xs">
                      <thead className="sticky top-0 bg-panel text-left text-slate-500">
                        <tr>
                          <th className="py-1">District</th>
                          <th className="text-right">Past 7 d</th>
                          <th className="text-right">Next 7 d</th>
                          <th className="text-right">Peak day</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sorted.map((d) => (
                          <tr key={d.id} onClick={() => setSelected(d.id)} className={`cursor-pointer border-t border-line/50 hover:bg-white/5 ${d.id === cur.id ? "bg-amber-500/10" : ""}`}>
                            <td className="py-1 text-slate-200">{d.name}</td>
                            <td className="text-right text-slate-400">{fmt(d.observed_7d_mm)}</td>
                            <td className="text-right text-sky-300">{fmt(d.forecast_7d_mm)}</td>
                            <td className="text-right">
                              <LevelBadge level={d.category} text={`${fmt(d.peak_day.rain_mm)} mm`} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              </div>
              <div className="space-y-3">
                <Card title={`${cur.name} (${cur.hq})`} actions={<LevelBadge level={cur.alert_level} />}>
                  <div className="mb-3 grid grid-cols-2 gap-2 md:grid-cols-4">
                    <Kpi label="Observed 30 days" value={`${fmt(cur.observed_30d_mm)} mm`} />
                    <Kpi label="Observed 7 days" value={`${fmt(cur.observed_7d_mm)} mm`} />
                    <Kpi label="Forecast 3 days" value={`${fmt(cur.forecast_3d_mm)} mm`} color="#38bdf8" />
                    <Kpi label="Wettest day ahead" value={`${fmt(cur.peak_day.rain_mm)} mm`} hint={`${fmtDate(cur.peak_day.date)} · ${label(cur.category)}`} color={RAIN_COLOR[cur.category]} />
                  </div>
                  <RainChart d={cur} />
                  <Source>
                    {r.source}. Grey bars = observed, blue = forecast. {r.note}
                  </Source>
                </Card>
                <Card title="Live weather">
                  <WeatherPanel districtId={cur.id} />
                </Card>
              </div>
            </div>
          );
        }}
      </Async>
    </div>
  );
}
