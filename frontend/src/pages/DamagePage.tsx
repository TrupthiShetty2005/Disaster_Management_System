import { useState } from "react";
import { Doughnut } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";
import { Breadcrumbs } from "../components/Breadcrumbs";
import { KpiCard } from "../components/KpiCard";
import { SatelliteOverlayMap } from "../components/SatelliteOverlayMap";
import { StatusBadge } from "../components/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "../components/Feedback";
import { useAsync } from "../hooks/useAsync";
import { analyzeDamage, fetchDamageAssessments } from "../services/damage";
import { fetchFloodEvents } from "../services/flood";
import { fetchSatelliteImages, hasGenuinePreview, pickBeforeAfter, previewSrc } from "../services/satellite";
import { isMockMode } from "../services/apiClient";
import { useDataSources } from "../components/DataModeBadge";
import type { DamageAssessment } from "../types/api";

ChartJS.register(ArcElement, Tooltip, Legend);

const doughnutOpts = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { labels: { color: "#94a3b8", boxWidth: 10, font: { size: 10 } } } },
};

export function DamagePage() {
  const list = useAsync(fetchDamageAssessments, []);
  const scenes = useAsync(fetchSatelliteImages, []);
  const floods = useAsync(fetchFloodEvents, []);
  const dataSources = useDataSources();
  const demoMode = isMockMode() || dataSources?.use_mock_providers === true;
  const [result, setResult] = useState<DamageAssessment | null>(null);
  const [busy, setBusy] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [opacity, setOpacity] = useState(0.4);

  const pair = pickBeforeAfter(scenes.data?.items ?? []);
  const before = pair.before;
  const after = pair.after;
  const current = result ?? list.data?.items[0] ?? null;
  const report = current?.report;
  const building = report?.building_statistics.counts ?? {};
  const roads = report?.road_statistics.counts ?? {};
  const reportWater = Number(report?.flood_statistics.flooded_area_km2);
  const floodWater = Number(
    floods.data?.items?.[0]?.newly_flooded_area_km2 ?? floods.data?.items?.[0]?.flooded_area ?? NaN,
  );
  const waterKm =
    Number.isFinite(reportWater) && reportWater > 0
      ? reportWater
      : Number.isFinite(floodWater) && floodWater > 0
        ? floodWater
        : null;

  return (
    <div className="space-y-4">
      <Breadcrumbs items={[{ to: "/dashboard", label: "Command dashboard" }, { label: "Damage assessment report" }]} />
      <p className="text-xs text-slate-500">
        Before/after change detection on Sentinel previews. Building/road counts are simulated in Demo Mode only. Live
        mode does not invent a damage inventory. JSON report only — PDF generation is not implemented.
      </p>
      <div className="grid gap-3 md:grid-cols-2">
        <figure className="rounded border border-line bg-panel p-2">
          <figcaption className="mb-1 text-[11px] uppercase tracking-widest text-slate-500">Before</figcaption>
          {scenes.loading ? <LoadingState /> : null}
          {before && hasGenuinePreview(before) ? (
            <img src={previewSrc(before)} alt="before" className="h-40 w-full object-cover" />
          ) : (
            <p className="text-xs text-slate-500">No genuine before preview (dates/AOI), not a name match).</p>
          )}
          <p className="mt-1 text-[11px] text-slate-500">
            {before ? `${new Date(before.acquisition_time).toISOString()} · ${before.id}` : "UNAVAILABLE"}
          </p>
        </figure>
        <figure className="rounded border border-line bg-panel p-2">
          <figcaption className="mb-1 text-[11px] uppercase tracking-widest text-slate-500">After</figcaption>
          {after && hasGenuinePreview(after) ? (
            <img src={previewSrc(after)} alt="after" className="h-40 w-full object-cover" />
          ) : (
            <p className="text-xs text-slate-500">No genuine after preview.</p>
          )}
          <p className="mt-1 text-[11px] text-slate-500">
            {after ? `${new Date(after.acquisition_time).toISOString()} · ${after.id}` : "UNAVAILABLE"}
          </p>
        </figure>
      </div>
      <button
        type="button"
        disabled={busy}
        className="rounded border border-amber-500/40 px-4 py-2 text-sm text-amber-200"
        onClick={async () => {
          setBusy(true);
          setRunError(null);
          try {
            setResult(await analyzeDamage());
          } catch (err) {
            setResult(null);
            setRunError(err instanceof Error ? err.message : "Damage assessment unavailable");
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "Assessing…" : "Run damage assessment"}
      </button>
      {runError ? <ErrorState message={runError} /> : null}
      {scenes.error ? <ErrorState message={`Satellite catalogue: ${scenes.error}`} /> : null}
      {list.error ? <ErrorState message={`Damage list: ${list.error}`} /> : null}
      {list.loading ? <LoadingState /> : null}
      {current && report ? (
        <>
          <p className="rounded border border-line bg-panel p-3 text-sm text-slate-300">{report.executive_summary}</p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard
              label="Water-change area"
              value={waterKm == null ? "UNAVAILABLE" : `${waterKm} km²`}
              hint={
                waterKm == null
                  ? "No positive water-change measurement; zeros are not shown as surveyed flood area"
                  : "Heuristic from imagery, not a flood survey"
              }
            />
            <KpiCard
              label="Buildings damaged"
              value={demoMode ? `${report.building_statistics.damaged_percentage}%` : "UNAVAILABLE"}
              hint={demoMode ? "SIMULATED mix" : "No building damage overlay"}
            />
            <KpiCard
              label="Roads destroyed"
              value={demoMode ? String(report.road_statistics.destroyed_roads) : "UNAVAILABLE"}
              hint={demoMode ? "SIMULATED mix" : "No road-status feed"}
            />
            <KpiCard
              label="Crop loss (proxy)"
              value={demoMode ? `${report.infrastructure_loss.crop_destruction_pct}%` : "UNAVAILABLE"}
              hint={demoMode ? "SIMULATED from vegetation index" : "No crop-loss dataset"}
            />
          </div>
          <div className="flex gap-2">
            <StatusBadge value={report.building_statistics.primary} />
            <StatusBadge value={report.road_statistics.primary} />
          </div>
          {demoMode ? (
          <div className="grid gap-3 lg:grid-cols-2">
            <div className="h-56 rounded border border-line bg-panel p-3">
              <p className="mb-2 text-[11px] uppercase tracking-widest text-slate-500">Building damage (SIMULATED)</p>
              <Doughnut
                options={doughnutOpts}
                data={{
                  labels: Object.keys(building),
                  datasets: [{ data: Object.values(building), backgroundColor: ["#22c55e", "#84cc16", "#eab308", "#f97316", "#ef4444"] }],
                }}
              />
            </div>
            <div className="h-56 rounded border border-line bg-panel p-3">
              <p className="mb-2 text-[11px] uppercase tracking-widest text-slate-500">Road accessibility (SIMULATED)</p>
              <Doughnut
                options={doughnutOpts}
                data={{
                  labels: Object.keys(roads),
                  datasets: [{ data: Object.values(roads), backgroundColor: ["#22c55e", "#eab308", "#f97316", "#ef4444"] }],
                }}
              />
            </div>
          </div>
          ) : (
            <EmptyState message="Building and road damage inventories UNAVAILABLE — no trained damage model or overlay in REAL DATA. Zeros are not charted as a survey." />
          )}
          <div className="h-[340px]">
            <p className="mb-1 text-[11px] uppercase tracking-widest text-slate-500">Affected-area map</p>
            <SatelliteOverlayMap
              footprint={null}
              overlays={(current.overlay_geojson as GeoJSON.GeoJsonObject | null) ?? null}
              opacity={opacity}
              showFootprint={false}
              showDetections
            />
          </div>
          <label className="flex items-center gap-2 text-xs text-slate-400">
            Overlay opacity
            <input type="range" min={0.1} max={0.9} step={0.05} value={opacity} onChange={(e) => setOpacity(Number(e.target.value))} />
          </label>
          <section className="rounded border border-line bg-panel p-3">
            <h3 className="text-xs uppercase tracking-widest text-slate-500">Priority zones</h3>
            <ul className="mt-2 space-y-1 text-sm">
              {report.priority_areas.map((z) => (
                <li key={z.name}>
                  {z.rank}. {z.name} — {z.action}
                </li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-slate-500">{report.pdf_generation}</p>
          </section>
        </>
      ) : null}
    </div>
  );
}
