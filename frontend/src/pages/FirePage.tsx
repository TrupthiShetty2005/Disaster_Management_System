import { useState, type ReactNode } from "react";
import { getFireClusterImpact, getFireClusters, getFireDanger, getFireDetections, getFireIndustrialSites, type FireWindow } from "../api/endpoints";
import type { FireCluster, FireDetectionRecord, Impact, IndustrialSitesResponse, MonitoredSite } from "../api/types";
import { ImpactSummary } from "../components/ImpactSummary";
import { Async, Card, Empty, ErrorBox, Kpi, LevelBadge, Loading, PageHeader, Source } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { clusterBounds, INDUSTRIAL_COLOR, SITE_COLOR, SITE_STATUS_TEXT, siteBounds, type LatLngBounds } from "../lib/fire";
import { DANGER_COLOR, fmt, fmtDate, fmtDateTime, label, timeAgo } from "../lib/format";
import { KarnatakaMap } from "../maps/KarnatakaMap";
import { FlyTo, SelectedClusterLayer, SiteMarkers } from "../maps/fireLayers";
import { ClusterMarkers, DetectionMarkers } from "../maps/layers";

const KARNATAKA_BOUNDS: LatLngBounds = [
  [11.5, 74.0],
  [18.5, 78.6],
];

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

function Field({ name, children }: { name: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-slate-500">{name}</dt>
      <dd className="text-slate-200">{children}</dd>
    </div>
  );
}

function DetectionHistory({ rows, extra }: { rows: FireDetectionRecord[]; extra?: (d: FireDetectionRecord, i: number) => ReactNode }) {
  return (
    <table className="w-full text-[11px]">
      <thead className="sticky top-0 bg-panel text-slate-500">
        <tr>
          <th className="py-0.5 text-left">Time (local)</th>
          <th className="text-left">Sensor</th>
          <th className="text-right">FRP MW</th>
          <th className="text-left pl-1">Conf.</th>
          {extra ? <th className="text-right">km</th> : null}
        </tr>
      </thead>
      <tbody>
        {rows.map((d, i) => (
          <tr key={`${d.acquired_at}-${d.latitude}-${i}`} className="border-t border-line/40">
            <td className="py-0.5 text-slate-300">
              {fmtDateTime(d.acquired_at)} {d.daynight === "N" ? "🌙" : ""}
            </td>
            <td className="text-slate-400">{d.sensor.replace("VIIRS_", "")}</td>
            <td className="text-right text-orange-300">{fmt(d.frp_mw, 1)}</td>
            <td className="pl-1 text-slate-400">{d.confidence}</td>
            {extra ? <td className="text-right text-slate-400">{extra(d, i)}</td> : null}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Panel({ title, accent, onClose, children }: { title: ReactNode; accent: string; onClose: () => void; children: ReactNode }) {
  return (
    <div className="absolute bottom-3 left-3 z-[1000] flex max-h-[50%] w-[360px] lg:max-h-[75%] max-w-[calc(100%-1.5rem)] flex-col rounded border bg-panel/95 text-xs shadow-xl backdrop-blur" style={{ borderColor: accent }}>
      <div className="flex items-start justify-between gap-2 border-b border-line px-3 py-2">
        <div className="text-sm font-medium text-slate-100">{title}</div>
        <button aria-label="Close details" onClick={onClose} className="rounded px-1.5 text-slate-400 hover:bg-white/10 hover:text-slate-100">
          ✕
        </button>
      </div>
      <div className="space-y-2 overflow-auto px-3 py-2">{children}</div>
    </div>
  );
}

function EventPanel({ cluster, onClose }: { cluster: FireCluster; onClose: () => void }) {
  const history = cluster.members ?? [];
  return (
    <Panel
      accent={cluster.persistent_heat_source ? INDUSTRIAL_COLOR : "#fde047"}
      onClose={onClose}
      title={
        <span className="flex items-center gap-2">
          {cluster.district} <LevelBadge level={cluster.severity} />
        </span>
      }
    >
      <p style={{ color: cluster.persistent_heat_source ? INDUSTRIAL_COLOR : undefined }} className="text-slate-300">
        {cluster.classification}
      </p>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1">
        <Field name="Detections">
          {cluster.detections} ({cluster.high_confidence} high-conf.)
        </Field>
        <Field name="Sensors">{cluster.sensors.map((s) => s.replace("VIIRS_", "")).join(", ")}</Field>
        <Field name="Total / peak FRP">
          {fmt(cluster.total_frp_mw)} / {fmt(cluster.max_frp_mw, 1)} MW
        </Field>
        <Field name="Days seen">{cluster.days_seen} of 7</Field>
        <Field name="First seen">{fmtDateTime(cluster.first_seen)}</Field>
        <Field name="Last seen">
          {fmtDateTime(cluster.last_seen)} ({timeAgo(cluster.last_seen)})
        </Field>
        <Field name="Location">
          {cluster.latitude.toFixed(4)}° N, {cluster.longitude.toFixed(4)}° E
        </Field>
        <Field name="Monitored site">{cluster.nearest_site ? `${cluster.nearest_site.name} (${fmt(cluster.nearest_site.distance_km, 1)} km)` : "—"}</Field>
      </dl>
      {cluster.persistent_heat_source ? (
        <p className="text-slate-400">
          Re-detected on {cluster.days_seen} of the last 7 days within a few kilometres: this behaves like a fixed industrial heat source (furnace, kiln, flare) rather than a wildfire, so it is shown here but excluded from fire alerts and danger scoring.
        </p>
      ) : null}
      {history.length ? (
        <div>
          <p className="mb-1 text-slate-500">Detection history (yellow on map)</p>
          <div className="max-h-48 overflow-auto">
            <DetectionHistory rows={history} />
          </div>
        </div>
      ) : null}
    </Panel>
  );
}

function SitePanel({ site, meta, onClose }: { site: MonitoredSite; meta: IndustrialSitesResponse; onClose: () => void }) {
  const cloud = site.cloud_at_passes;
  return (
    <Panel accent={SITE_COLOR} onClose={onClose} title={site.name}>
      <p className="text-slate-400">
        {site.kind} · {site.district} · search radius {site.radius_km} km
      </p>
      <div className="flex flex-wrap gap-1">
        {Object.entries(site.counts).map(([w, n]) => (
          <span key={w} className={`rounded border px-1.5 py-0.5 ${n ? "border-orange-500/60 text-orange-300" : "border-line text-slate-400"}`}>
            {w}: {n}
          </span>
        ))}
      </div>
      <p className="text-slate-200">{site.summary}</p>
      {site.status === "NO_DETECTION" ? (
        <div className="rounded border border-amber-500/40 bg-amber-500/5 p-2 text-amber-200/90">
          <p>
            No NASA FIRMS thermal detection exists for this site between {fmtDateTime(meta.coverage.from)} and {fmtDateTime(meta.coverage.to)} (all VIIRS and MODIS sensors). An incident here in that period was not captured by satellite, or happened earlier than the available window.
          </p>
          <p className="mt-1 text-amber-200/70">{meta.archive.map_key_configured ? meta.archive.note : `Window limited to ${meta.archive.max_days} days: ${meta.archive.note}`}</p>
        </div>
      ) : (
        <div>
          <p className="mb-1 text-slate-500">
            Detection history · {site.days_with_detections} day(s) · total {fmt(site.total_frp_mw)} MW, peak {fmt(site.max_frp_mw, 1)} MW
          </p>
          <div className="max-h-44 overflow-auto">
            <DetectionHistory rows={site.history} extra={(_, i) => fmt(site.history[i].distance_km, 1)} />
          </div>
        </div>
      )}
      {cloud?.days.length ? (
        <div>
          <p className="mb-1 text-slate-500">Cloud cover at VIIRS passes (~01:30 / ~13:30 IST), mean {fmt(cloud.mean_pct)}%</p>
          <div className="flex flex-wrap gap-1">
            {cloud.days.map((d) => (
              <span key={d.date} className="rounded bg-white/5 px-1 py-0.5 text-slate-400" title="night / day cloud cover %">
                {fmtDate(d.date).replace(/ \d{4}$/, "")}: {d.night_pct ?? "—"}/{d.day_pct ?? "—"}%
              </span>
            ))}
          </div>
        </div>
      ) : null}
      {site.facilities.length ? <p className="text-slate-500">Facilities: {site.facilities.map((f) => f.name).join(" · ")}</p> : null}
    </Panel>
  );
}

function SitesTable({ data, selectedId, onSelect }: { data: IndustrialSitesResponse; selectedId: string | null; onSelect: (s: MonitoredSite) => void }) {
  const windows = data.archive.windows;
  return (
    <>
      <p className={`mb-2 rounded border p-2 text-xs ${data.archive.map_key_configured ? "border-line text-slate-400" : "border-amber-500/40 bg-amber-500/5 text-amber-200/90"}`}>
        Satellite coverage available: {fmtDateTime(data.coverage.from)} → {fmtDateTime(data.coverage.to)}. {data.archive.note}
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="text-slate-500">
            <tr>
              <th className="py-1 text-left">Site</th>
              <th className="text-left">District</th>
              {windows.map((w) => (
                <th key={w} className="text-right">
                  {w}
                </th>
              ))}
              <th className="pl-2 text-left">Status</th>
              <th className="text-left">Last detection</th>
              <th className="text-right">Nearest detection</th>
              <th className="text-right">Cloud at passes</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((s) => (
              <tr key={s.id} onClick={() => onSelect(s)} className={`cursor-pointer border-t border-line/50 hover:bg-white/5 ${s.id === selectedId ? "bg-emerald-500/10" : ""}`}>
                <td className="py-1 text-slate-200">
                  {s.name}
                  <div className="text-[11px] text-slate-500">
                    {s.kind} · r {s.radius_km} km
                  </div>
                </td>
                <td className="text-slate-400">{s.district}</td>
                {windows.map((w) => (
                  <td key={w} className={`text-right ${s.counts[w] ? "text-orange-300" : "text-slate-600"}`}>
                    {s.counts[w] ?? "—"}
                  </td>
                ))}
                <td className={`pl-2 ${s.status === "NO_DETECTION" ? "text-slate-500" : "text-orange-300"}`}>{SITE_STATUS_TEXT[s.status]}</td>
                <td className="text-slate-400">{s.last_detection ? timeAgo(s.last_detection) : "none in window"}</td>
                <td className="text-right text-slate-400">{s.nearest_detection ? `${fmt(s.nearest_detection.distance_km, 1)} km` : "—"}</td>
                <td className="text-right text-slate-400">{s.cloud_at_passes?.mean_pct != null ? `${s.cloud_at_passes.mean_pct}%` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-slate-400">{data.limitations}</p>
      <Source>
        {data.sources}. GDACS (shown on the dashboard) reports natural disasters only, not industrial accidents. Click a row to fly to the site.
      </Source>
    </>
  );
}

function ClusterList({ items, selectedId, onSelect, persistent }: { items: FireCluster[]; selectedId: string | null; onSelect: (c: FireCluster) => void; persistent?: boolean }) {
  return (
    <ul className="space-y-1 text-xs">
      {items.map((c) => (
        <li key={c.id}>
          <button
            onClick={() => onSelect(c)}
            className={`w-full rounded border px-2 py-1.5 text-left hover:bg-white/5 ${selectedId === c.id ? "border-amber-400 bg-amber-400/10" : "border-line"}`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-slate-200">{persistent && c.nearest_site ? c.nearest_site.name : c.district}</span>
              {persistent ? (
                <span className="rounded px-1.5 py-0.5 text-[10px]" style={{ color: INDUSTRIAL_COLOR, background: `${INDUSTRIAL_COLOR}22` }}>
                  INDUSTRIAL
                </span>
              ) : (
                <LevelBadge level={c.severity} />
              )}
            </div>
            <p className="text-slate-500">
              {persistent && c.nearest_site ? `${c.district} · ` : ""}
              {c.detections} detections · {c.days_seen} day(s) · {fmt(c.total_frp_mw)} MW · last {timeAgo(c.last_seen)}
            </p>
          </button>
        </li>
      ))}
    </ul>
  );
}

export default function FirePage() {
  const [window, setWindow] = useState<FireWindow>("48h");
  const detections = useAsync(() => getFireDetections(window), [window], 900_000);
  const clusters = useAsync(() => getFireClusters("7d"), [], 900_000);
  const sites = useAsync(getFireIndustrialSites, [], 900_000);
  const danger = useAsync(getFireDanger, [], 3_600_000);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [siteId, setSiteId] = useState<string | null>(null);
  const [resetCount, setResetCount] = useState(0);

  const all = clusters.data?.items ?? [];
  const fires = all.filter((c) => !c.persistent_heat_source);
  const industrial = all.filter((c) => c.persistent_heat_source);
  const selected = all.find((c) => c.id === selectedId) ?? null;
  const site = sites.data?.items.find((s) => s.id === siteId) ?? null;

  const selectCluster = (c: FireCluster) => {
    setSiteId(null);
    setSelectedId(c.id);
  };
  const selectSite = (s: MonitoredSite) => {
    setSelectedId(null);
    setSiteId(s.id);
  };
  const clearSelection = () => {
    setSelectedId(null);
    setSiteId(null);
    setResetCount((n) => n + 1);
  };

  const fly = selected
    ? { key: `c:${selected.id}`, bounds: clusterBounds(selected) }
    : site
      ? { key: `s:${site.id}`, bounds: siteBounds(site) }
      : resetCount
        ? { key: `all:${resetCount}`, bounds: KARNATAKA_BOUNDS }
        : null;

  return (
    <div className="space-y-3">
      <PageHeader
        title="Fire detection & fire-danger forecast"
        subtitle="Active fires detected by NASA's VIIRS and MODIS satellite sensors over Karnataka, grouped into fire events. Persistent industrial heat sources (steel plants, kilns, flares) are shown in violet and kept out of fire alerts. Major industrial sites are monitored for any satellite thermal detection. A fire-danger forecast is computed from the live weather forecast."
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
        <Kpi label="Industrial heat sources" value={clusters.data ? industrial.length : "—"} hint="seen ≥4 days at a fixed site · violet on map, not alerted" color={INDUSTRIAL_COLOR} />
        <Kpi label="Highest danger (7 d)" value={danger.data?.items[0] ? label(danger.data.items[0].peak_level) : "—"} hint={danger.data?.items[0] ? `${danger.data.items[0].name}, FFWI ${fmt(danger.data.items[0].peak_ffwi)}` : undefined} color={DANGER_COLOR[danger.data?.items[0]?.peak_level ?? ""] ?? "#e2e8f0"} />
      </div>
      <div className="grid gap-3 xl:grid-cols-[1fr_420px]">
        <Card
          title="Satellite fire detections"
          actions={
            selected || site || resetCount ? (
              <button className="btn text-xs" onClick={clearSelection}>
                Show all Karnataka
              </button>
            ) : null
          }
        >
          {detections.error ? <ErrorBox message={detections.error} onRetry={detections.reload} /> : null}
          <div className="relative">
            <KarnatakaMap height={560}>
              <DetectionMarkers detections={detections.data?.detections ?? []} />
              <ClusterMarkers clusters={all} onSelect={selectCluster} selectedId={selectedId} />
              {sites.data ? <SiteMarkers sites={sites.data.items} selectedId={siteId} onSelect={selectSite} /> : null}
              {selected ? <SelectedClusterLayer cluster={selected} /> : null}
              <FlyTo targetKey={fly?.key ?? null} bounds={fly?.bounds ?? null} panel={Boolean(selected || site)} />
            </KarnatakaMap>
            {selected ? <EventPanel key={selected.id} cluster={selected} onClose={clearSelection} /> : null}
            {!selected && site && sites.data ? <SitePanel key={site.id} site={site} meta={sites.data} onClose={clearSelection} /> : null}
          </div>
          <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-slate-400">
            <span>
              <span className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-orange-500 align-middle" />
              FIRMS detection ({window})
            </span>
            <span>
              <span className="mr-1 inline-block h-2.5 w-2.5 rounded-full border-2 border-red-500 align-middle" />
              Fire event (7 d, colour = severity)
            </span>
            <span>
              <span className="mr-1 inline-block h-2.5 w-2.5 rounded-full align-middle" style={{ background: INDUSTRIAL_COLOR }} />
              Persistent industrial heat source
            </span>
            <span>
              <span className="mr-1 inline-block h-3 w-3 rounded-full border-[3px] bg-ink align-middle" style={{ borderColor: SITE_COLOR }} />
              Monitored industrial site (orange centre = detection in window)
            </span>
          </div>
          {detections.data ? (
            <Source>
              NASA FIRMS near-real-time feeds: {Object.entries(detections.data.feeds).map(([k, v]) => `${k} ${v}`).join(" · ")}. {detections.data.clipped_by}. Click an event, industrial source or site to zoom to it and see its details.
              {Object.keys(detections.data.feed_errors).length ? ` Feeds unavailable: ${Object.keys(detections.data.feed_errors).join(", ")}.` : ""}
            </Source>
          ) : null}
        </Card>
        <div className="space-y-3">
          <Card title="Fire events (last 7 days)">
            <Async state={clusters}>
              {() =>
                fires.length ? (
                  <div className="max-h-[360px] overflow-auto">
                    <ClusterList items={fires} selectedId={selectedId} onSelect={selectCluster} />
                  </div>
                ) : (
                  <Empty>No vegetation fires detected in Karnataka in the last 7 days.</Empty>
                )
              }
            </Async>
          </Card>
          <Card title="Industrial heat sources (7 days)">
            <Async state={clusters}>
              {() =>
                industrial.length ? (
                  <div className="max-h-[220px] overflow-auto">
                    <ClusterList items={industrial} selectedId={selectedId} onSelect={selectCluster} persistent />
                  </div>
                ) : (
                  <Empty>No persistent industrial heat sources in the last 7 days.</Empty>
                )
              }
            </Async>
          </Card>
        </div>
      </div>
      {selected && !selected.persistent_heat_source ? <ClusterImpact key={selected.id} cluster={selected} /> : null}
      <Card title="Monitored industrial sites — satellite thermal detections">
        <Async state={sites} loadingText="Checking NASA FIRMS detections around each site…">
          {(d) => <SitesTable data={d} selectedId={siteId} onSelect={selectSite} />}
        </Async>
      </Card>
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
