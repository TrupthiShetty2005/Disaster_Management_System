import { Link } from "react-router-dom";
import { getAlerts, getOverview } from "../api/endpoints";
import type { Overview } from "../api/types";
import { Async, Card, Empty, ErrorBox, Kpi, LevelBadge, PageHeader, Source } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { fmt, fmtDate, inr, label, levelColor, timeAgo } from "../lib/format";
import { KarnatakaMap } from "../maps/KarnatakaMap";
import { ClusterMarkers, DetectionMarkers, EventMarkers, StationMarkers } from "../maps/layers";

function Unavailable({ section }: { section: { status: string; detail?: string } }) {
  return section.status === "live" ? null : <ErrorBox message={`Live source unavailable: ${section.detail ?? "unknown error"}`} />;
}

function Summary({ o }: { o: Overview }) {
  const water = o.water.data;
  const fire = o.fire.data;
  const rain = o.rain.data;
  const elevated = water ? water.stations.filter((s) => ["WATCH", "WARNING", "SEVERE"].includes(s.status)).length : null;
  const vegetationClusters = fire ? fire.active_clusters.length : null;
  return (
    <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
      <Kpi label="Open alerts" value={o.alerts.open} hint={Object.entries(o.alerts.by_hazard).map(([h, n]) => `${n} ${h}`).join(" · ") || "none active"} color={o.alerts.open ? "#f97316" : "#34d399"} />
      <Kpi label="Rivers above normal" value={elevated ?? "—"} hint={water ? `of ${water.stations.length} GloFAS stations (now or forecast)` : "GloFAS unavailable"} color={elevated ? "#facc15" : "#34d399"} />
      <Kpi label="Fire detections (24 h)" value={fire ? fire.detections_24h : "—"} hint={fire ? `${vegetationClusters} active fire clusters · ${fire.industrial_sources.length} industrial sources excluded` : "FIRMS unavailable"} color="#f97316" />
      <Kpi label="Heavy rain forecast" value={rain ? rain.heavy_forecast.length : "—"} hint={rain ? `districts ≥ 64.5 mm/day in 7 days · wettest week: ${rain.wettest_7d ?? "—"}` : "Open-Meteo unavailable"} color={rain?.heavy_forecast.length ? "#f59e0b" : "#38bdf8"} />
    </div>
  );
}

export default function DashboardPage() {
  const overview = useAsync(getOverview, [], 300_000);
  const alerts = useAsync(() => getAlerts("open"), [], 120_000);

  return (
    <div className="space-y-3">
      <PageHeader title="Karnataka situation" subtitle="Live river discharge forecasts, satellite fire detections, rainfall and disaster events across Karnataka. Every number on this page comes from a public live data feed." />
      <Async state={overview} loadingText="Fetching live feeds (GloFAS, FIRMS, Open-Meteo, GDACS)…">
        {(o) => (
          <>
            <Summary o={o} />
            <div className="grid gap-3 xl:grid-cols-[1fr_380px]">
              <Card title="Live hazard map" actions={<span className="text-[11px] text-slate-500">rivers · FIRMS fires (24 h) · fire clusters · GDACS events</span>}>
                <KarnatakaMap height={560}>
                  {o.fire.data ? <ClusterMarkers clusters={[...o.fire.data.active_clusters, ...o.fire.data.industrial_sources]} /> : null}
                  {o.fire.data ? <DetectionMarkers detections={o.fire.data.detections_24h_points} /> : null}
                  {o.water.data ? <StationMarkers stations={o.water.data.stations} /> : null}
                  {o.events.data ? <EventMarkers events={o.events.data.filter((e) => e.near_karnataka)} /> : null}
                </KarnatakaMap>
                <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-slate-400">
                  {["NORMAL", "WATCH", "WARNING", "SEVERE"].map((l) => (
                    <span key={l} className="flex items-center gap-1">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: levelColor(l) }} /> River {label(l)}
                    </span>
                  ))}
                  <span className="flex items-center gap-1">
                    <span className="h-2.5 w-2.5 rounded-full bg-orange-500" /> VIIRS/MODIS fire pixel
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="h-2.5 w-2.5 rounded-full border border-dashed border-slate-400" /> Persistent industrial heat (excluded)
                  </span>
                </div>
              </Card>
              <div className="space-y-3">
                <Card title="Active alerts" actions={<Link to="/alerts" className="text-xs text-amber-300">All alerts →</Link>}>
                  <Async state={alerts}>
                    {(a) =>
                      a.items.length ? (
                        <ul className="max-h-72 space-y-2 overflow-auto">
                          {a.items.slice(0, 12).map((al) => (
                            <li key={al.id} className="border-l-2 pl-2" style={{ borderColor: levelColor(al.severity) }}>
                              <p className="text-sm text-slate-200">{al.title}</p>
                              <p className="text-[11px] text-slate-500">
                                {al.source} · updated {timeAgo(al.updated_at)}
                              </p>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <Empty>No live condition currently crosses an alert threshold.</Empty>
                      )
                    }
                  </Async>
                </Card>
                <Card title="River outlook" actions={<Link to="/water" className="text-xs text-amber-300">Details →</Link>}>
                  <Unavailable section={o.water} />
                  {o.water.data ? (
                    <table className="w-full text-xs">
                      <tbody>
                        {o.water.data.stations.slice(0, 8).map((s) => (
                          <tr key={s.id} className="border-b border-line/50">
                            <td className="py-1 text-slate-300">{s.name}</td>
                            <td className="text-right text-slate-400">{fmt(s.percent_of_2yr_flood)}% Q2</td>
                            <td className="pl-2 text-right">
                              <LevelBadge level={s.status} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : null}
                </Card>
              </div>
            </div>
            <div className="grid gap-3 lg:grid-cols-3">
              <Card title="Fire by district (24 h)">
                <Unavailable section={o.fire} />
                {o.fire.data ? (
                  Object.keys(o.fire.data.by_district_24h).length ? (
                    <ul className="space-y-1 text-sm">
                      {Object.entries(o.fire.data.by_district_24h).map(([d, n]) => (
                        <li key={d} className="flex justify-between">
                          <span className="text-slate-300">{d}</span>
                          <span className="text-orange-300">{n}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <Empty>No satellite fire detections in Karnataka in the last 24 hours.</Empty>
                  )
                ) : null}
                <Source>NASA FIRMS VIIRS (S-NPP, NOAA-20, NOAA-21) + MODIS, clipped to the Karnataka boundary.</Source>
              </Card>
              <Card title="Rain: next 7 days">
                <Unavailable section={o.rain} />
                {o.rain.data ? (
                  <ul className="space-y-1 text-sm">
                    {[...o.rain.data.districts]
                      .sort((a, b) => b.forecast_7d_mm - a.forecast_7d_mm)
                      .slice(0, 8)
                      .map((d) => (
                        <li key={d.id} className="flex items-center justify-between gap-2">
                          <span className="text-slate-300">{d.name}</span>
                          <span className="text-sky-300">{fmt(d.forecast_7d_mm)} mm</span>
                          <LevelBadge level={d.category} />
                        </li>
                      ))}
                  </ul>
                ) : null}
                <Source>Open-Meteo forecast (ECMWF/GFS blend); IMD 24-hour rainfall categories.</Source>
              </Card>
              <Card title="Recent satellite analyses" actions={<Link to="/satellite" className="text-xs text-amber-300">Run analysis →</Link>}>
                {o.recent_analyses.length ? (
                  <ul className="space-y-2 text-sm">
                    {o.recent_analyses.map((a) => (
                      <li key={a.id}>
                        <Link to={`/impact?analysis=${a.id}`} className="text-slate-200 hover:text-amber-300">
                          {a.kind === "flood" ? "Flood" : "Burn scar"} · {a.area_name}
                        </Link>
                        <p className="text-[11px] text-slate-500">
                          {fmtDate(a.created_at)} · {fmt(a.impact_summary?.buildings)} buildings · {fmt(a.impact_summary?.road_km, 1)} km road · {inr(a.loss)}
                        </p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <Empty>No analyses yet. Run a Sentinel-1/2 analysis from the Satellite page.</Empty>
                )}
              </Card>
            </div>
            {o.events.data && o.events.data.length ? (
              <Card title="GDACS disaster events (India, last 90 days)">
                <ul className="grid gap-2 text-sm md:grid-cols-2">
                  {o.events.data.map((e) => (
                    <li key={e.id} className="rounded border border-line p-2">
                      <p className="text-slate-200">
                        {e.name} <LevelBadge level={e.alert_level === "Red" ? "SEVERE" : e.alert_level === "Orange" ? "WARNING" : "NORMAL"} text={e.alert_level} />
                        {e.inside_karnataka ? <span className="ml-1 text-[11px] text-amber-300">in Karnataka</span> : null}
                      </p>
                      <p className="text-[11px] text-slate-500">
                        {fmtDate(e.from_date)} – {fmtDate(e.to_date)} · {e.is_current ? "ongoing" : "ended"}
                        {e.report_url ? (
                          <>
                            {" · "}
                            <a className="text-sky-400" href={e.report_url} target="_blank" rel="noreferrer">
                              report
                            </a>
                          </>
                        ) : null}
                      </p>
                    </li>
                  ))}
                </ul>
              </Card>
            ) : null}
          </>
        )}
      </Async>
    </div>
  );
}
