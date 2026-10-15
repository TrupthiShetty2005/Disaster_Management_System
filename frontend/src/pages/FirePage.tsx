import { useState } from "react";
import { Polygon } from "react-leaflet";
import { getFireClusterImpact, getFireClusters, getFireDanger, getFireDetections, type FireWindow } from "../api/endpoints";
import type { FireCluster, Impact } from "../api/types";
import { ImpactSummary } from "../components/ImpactSummary";
import { Async, Card, Empty, ErrorBox, Kpi, LevelBadge, Loading, PageHeader, Source } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { DANGER_COLOR, fmt, fmtDate, fmtDateTime, label, timeAgo } from "../lib/format";
import { KarnatakaMap } from "../maps/KarnatakaMap";
import { ClusterMarkers, DetectionMarkers } from "../maps/layers";

function ClusterImpact({ cluster }: { cluster: FireCluster }) {
  const [radius, setRadius] = useState(500);
  const [state, setState] = useState<{ loading: boolean; impact?: Impact; error?: string }>({ loading: false });
  const run = () => {
    setState({ loading: true });
    getFireClusterImpact(cluster.id, radius)
      .then((r) => setState({ loading: false, impact: r.impact }))
      .catch((e: Error) => setState({ loading: false, error: e.message }));
  };
  return (
    <Card title={`Infrastructure at risk · ${cluster.district} fire`} actions={<LevelBadge level={cluster.severity} />}>
      <p className="mb-2 text-xs text-slate-400">
        {cluster.classification}: {cluster.detections} detections ({cluster.high_confidence} high-confidence) by {cluster.sensors.join(", ")}, {fmtDateTime(cluster.first_seen)} → {fmtDateTime(cluster.last_seen)}. Peak fire radiative power {fmt(cluster.max_frp_mw, 1)} MW.
      </p>
      <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
        <label className="text-slate-400" htmlFor="radius">
          Exposure radius around each fire pixel
        </label>
        <select id="radius" className="rounded border border-line bg-ink px-2 py-1" value={radius} onChange={(e) => setRadius(Number(e.target.value))}>
          {[375, 500, 1000, 2000].map((r) => (
            <option key={r} value={r}>
              {r} m
            </option>
          ))}
        </select>
        <button className="btn-primary" disabled={state.loading} onClick={run}>
          {state.loading ? "Querying OpenStreetMap…" : "Estimate infrastructure losses"}
        </button>
      </div>
      {state.loading ? <Loading text="Intersecting fire footprint with OpenStreetMap buildings, roads and power lines (can take up to a minute)…" /> : null}
      {state.error ? <ErrorBox message={state.error} /> : null}
      {state.impact ? <ImpactSummary impact={state.impact} /> : null}
    </Card>
  );
}

export default function FirePage() {
  const [window, setWindow] = useState<FireWindow>("48h");
  const detections = useAsync(() => getFireDetections(window), [window], 900_000);
  const clusters = useAsync(() => getFireClusters("7d"), [], 900_000);
  const danger = useAsync(getFireDanger, [], 3_600_000);
  const [selected, setSelected] = useState<FireCluster | null>(null);

  const fires = clusters.data?.items.filter((c) => !c.persistent_heat_source) ?? [];
  const industrial = clusters.data?.items.filter((c) => c.persistent_heat_source) ?? [];

  return (
    <div className="space-y-3">
      <PageHeader
        title="Fire detection & fire-danger forecast"
        subtitle="Active fires detected by NASA's VIIRS and MODIS satellite sensors over Karnataka, grouped into fire events. Persistent industrial heat sources (steel plants, kilns) are identified and excluded. A 7-day fire-danger forecast is computed from the live weather forecast."
        actions={
          <div className="flex gap-1">
            {(["24h", "48h", "7d"] as FireWindow[]).map((w) => (
              <button key={w} onClick={() => setWindow(w)} className={`btn ${w === window ? "border-amber-500/60 text-amber-300" : ""}`}>
                {w}
              </button>
            ))}
          </div>
        }
      />
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <Kpi label={`Detections (${window})`} value={detections.data ? detections.data.count : "—"} hint={detections.data ? `retrieved ${timeAgo(detections.data.retrieved_at)}` : undefined} color="#f97316" />
        <Kpi label="Fire events (7 d)" value={clusters.data ? fires.length : "—"} hint={clusters.data ? `${fires.filter((c) => c.active_24h).length} active in last 24 h` : undefined} color="#ef4444" />
        <Kpi label="Industrial heat sources" value={clusters.data ? industrial.length : "—"} hint="seen ≥4 days at a fixed site · excluded" color="#94a3b8" />
        <Kpi label="Highest danger (7 d)" value={danger.data?.items[0] ? label(danger.data.items[0].peak_level) : "—"} hint={danger.data?.items[0] ? `${danger.data.items[0].name}, FFWI ${fmt(danger.data.items[0].peak_ffwi)}` : undefined} color={DANGER_COLOR[danger.data?.items[0]?.peak_level ?? ""] ?? "#e2e8f0"} />
      </div>
      <div className="grid gap-3 xl:grid-cols-[1fr_420px]">
        <Card title="Satellite fire detections">
          {detections.error ? <ErrorBox message={detections.error} onRetry={detections.reload} /> : null}
          <KarnatakaMap height={520}>
            {selected ? <Polygon positions={selected.points.map(([lat, lon]) => [lat, lon] as [number, number])} pathOptions={{ color: "#fde047" }} /> : null}
            <ClusterMarkers clusters={clusters.data?.items ?? []} onSelect={setSelected} />
            <DetectionMarkers detections={detections.data?.detections ?? []} />
          </KarnatakaMap>
          {detections.data ? (
            <Source>
              NASA FIRMS near-real-time feeds: {Object.entries(detections.data.feeds).map(([k, v]) => `${k} ${v}`).join(" · ")}. {detections.data.clipped_by}. Click a circle to select a fire event.
              {Object.keys(detections.data.feed_errors).length ? ` Feeds unavailable: ${Object.keys(detections.data.feed_errors).join(", ")}.` : ""}
            </Source>
          ) : null}
        </Card>
        <Card title="Fire events (last 7 days)">
          <Async state={clusters}>
            {() =>
              fires.length ? (
                <ul className="max-h-[540px] space-y-1 overflow-auto text-xs">
                  {fires.map((c) => (
                    <li key={c.id}>
                      <button onClick={() => setSelected(c)} className={`w-full rounded border px-2 py-1.5 text-left hover:bg-white/5 ${selected?.id === c.id ? "border-amber-500/60" : "border-line"}`}>
                        <div className="flex items-center justify-between">
                          <span className="text-slate-200">{c.district}</span>
                          <LevelBadge level={c.severity} />
                        </div>
                        <p className="text-slate-500">
                          {c.detections} detections · {c.days_seen} day(s) · {fmt(c.total_frp_mw)} MW · last {timeAgo(c.last_seen)}
                        </p>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <Empty>No vegetation fires detected in Karnataka in the last 7 days.</Empty>
              )
            }
          </Async>
        </Card>
      </div>
      {selected ? (
        selected.persistent_heat_source ? (
          <Card title={`${selected.district}: persistent industrial heat source`}>
            <p className="text-sm text-slate-300">
              Detected on {selected.days_seen} of the last 7 days within a few kilometres, which matches a fixed industrial facility (e.g. a steel plant or kiln) rather than a wildfire. It is shown for transparency and excluded from fire alerts and danger scoring.
            </p>
          </Card>
        ) : (
          <ClusterImpact key={selected.id} cluster={selected} />
        )
      ) : null}
      <Card title="7-day fire-danger forecast by district">
        <Async state={danger} loadingText="Computing fire-weather index from the Open-Meteo forecast…">
          {(d) => (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="text-slate-500">
                    <tr>
                      <th className="py-1 text-left">District</th>
                      <th className="text-right">Fires 48 h</th>
                      {d.items[0]?.days.map((day) => (
                        <th key={day.date} className="px-1 text-center">
                          {fmtDate(day.date).replace(/ \d{4}$/, "")}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {d.items.map((row) => (
                      <tr key={row.id} className="border-t border-line/50">
                        <td className="py-1 text-slate-200">{row.name}</td>
                        <td className="text-right text-orange-300">{row.active_detections_48h || ""}</td>
                        {row.days.map((day) => (
                          <td key={day.date} className="px-1 text-center">
                            <span
                              title={`FFWI ${day.ffwi} · ${day.temp_max_c}°C · RH ${day.rh_min_pct}% · wind ${day.wind_max_kmh} km/h · rain ${day.rain_mm} mm`}
                              className="inline-block w-full rounded px-1 py-0.5"
                              style={{ background: `${DANGER_COLOR[day.level] ?? "#334155"}33`, color: DANGER_COLOR[day.level] ?? "#94a3b8" }}
                            >
                              {label(day.level)}
                            </span>
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Source>{d.method}</Source>
            </>
          )}
        </Async>
      </Card>
    </div>
  );
}
