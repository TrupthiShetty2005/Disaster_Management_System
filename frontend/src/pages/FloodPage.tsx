import { useState } from "react";
import { Link } from "react-router-dom";
import { Breadcrumbs } from "../components/Breadcrumbs";
import { DEMO_STATS, LIVE_REGION } from "../constants/demo";
import { DataModeBadge, ModuleProvenance, useDataSources } from "../components/DataModeBadge";
import { EstimateCallout } from "../components/EstimateCallout";
import { KpiCard } from "../components/KpiCard";
import { SatelliteOverlayMap } from "../components/SatelliteOverlayMap";
import { StatusBadge } from "../components/StatusBadge";
import { LoadingState, EmptyState, ErrorState } from "../components/Feedback";
import { useAsync } from "../hooks/useAsync";
import { analyzeFlood, fetchFloodEvents } from "../services/flood";
import { apiBase, isMockMode } from "../services/apiClient";
import type { FloodEvent } from "../types/api";

function previewUrl(path: string | null | undefined): string {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${apiBase()}${path}`;
}

function fcFeatures(geo: unknown): GeoJSON.Feature[] {
  if (geo && typeof geo === "object" && "features" in geo) {
    return ((geo as { features: unknown[] }).features || []) as GeoJSON.Feature[];
  }
  return [];
}

export function FloodPage() {
  const list = useAsync(fetchFloodEvents, []);
  const dataSources = useDataSources();
  const [event, setEvent] = useState<FloodEvent | null>(null);
  const [busy, setBusy] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [opacity, setOpacity] = useState(0.45);
  const [showNewly, setShowNewly] = useState(true);
  const [showAfter, setShowAfter] = useState(true);
  const [showBefore, setShowBefore] = useState(false);
  const [showHeat, setShowHeat] = useState(false);

  const demoMode = isMockMode() || dataSources?.use_mock_providers === true;

  if (list.loading) return <LoadingState />;
  if (list.error) return <ErrorState message={list.error} />;
  const current = event ?? list.data?.items[0] ?? null;
  const isChange =
    Boolean(current?.estimate_label?.toLowerCase().includes("water-change")) ||
    Boolean(current?.estimate_label?.toLowerCase().includes("flood change")) ||
    Boolean(current?.notes?.toLowerCase().includes("requires validation")) ||
    current?.scene_kind === "sentinel2-change" ||
    current?.newly_flooded_area_km2 != null;

  const overlay = {
    type: "FeatureCollection" as const,
    features: [
      ...(showNewly ? fcFeatures(current?.newly_flooded_geojson ?? (isChange ? current?.boundary_geojson : null)) : []),
      ...(showAfter ? fcFeatures(current?.after_water_geojson) : []),
      ...(showBefore ? fcFeatures(current?.before_water_geojson) : []),
      ...(showHeat ? fcFeatures(current?.heatmap_geojson) : []),
      ...(!isChange && showNewly ? fcFeatures(current?.boundary_geojson) : []),
    ],
  };

  const newlyKm2 = current?.newly_flooded_area_km2 ?? current?.flooded_area;
  const newlyPct = current?.newly_flooded_percentage ?? current?.flood_percentage;

  return (
    <div className="space-y-4">
      <Breadcrumbs items={[{ to: "/dashboard", label: "Command dashboard" }, { label: `Flood detection · ${LIVE_REGION}` }]} />
      <div className="flex flex-wrap items-center gap-2">
        <DataModeBadge />
        {isChange ? (
          <span className="rounded border border-orange-500/40 bg-orange-500/10 px-2 py-1 text-xs text-orange-200">
            Satellite-derived water-change indication — requires validation
          </span>
        ) : null}
        <Link to="/satellite/compare" className="text-xs text-sky-300">
          Open satellite compare →
        </Link>
      </div>
      <ModuleProvenance moduleKey="flood_analysis" title="Flood change analysis" />
      <ModuleProvenance moduleKey="satellite" title="Sentinel catalogue / previews" />
      {demoMode ? (
        <EstimateCallout
          title="Canonical demo flood KPIs (Demo Mode only)"
          kind="SIMULATED DATA"
          value={`${DEMO_STATS.floodedKm2} km² · ${DEMO_STATS.affectedPopulation.toLocaleString("en-IN")} people · ${DEMO_STATS.blockedRoads} blocked roads`}
        />
      ) : (
        <EstimateCallout
          title="REAL SENTINEL DATA — HEURISTIC ANALYSIS"
          kind="REAL DATA"
          value="Genuine Sentinel-2 STAC previews for the selected Karnataka AOI. RGB heuristic water change — not a trained flood model, not a validated flood boundary."
        />
      )}
      <p className="text-xs text-slate-500">
        Two Sentinel-2 previews → water mask (heuristic) → newly water-covered = after and not before. Permanent water,
        clouds, and seasonal/date gaps are not treated as confirmed flood. Population, buildings, roads, and economic
        loss are not shown unless a reliable overlay exists.
      </p>
      <button
        type="button"
        disabled={busy}
        className="rounded border border-amber-500/40 px-4 py-2 text-sm text-amber-200"
        onClick={async () => {
          setBusy(true);
          setRunError(null);
          try {
            setEvent(await analyzeFlood("flood"));
          } catch (err) {
            setRunError(err instanceof Error ? err.message : "Flood analysis failed");
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "Comparing Sentinel scenes…" : "Run before/after flood change analysis"}
      </button>
      {runError ? <ErrorState message={runError} /> : null}
      {current ? (
        <>
          {!demoMode && (current.before_preview_url || current.after_preview_url) ? (
            <div className="grid gap-3 md:grid-cols-2">
              <figure className="rounded border border-line bg-panel p-2">
                <figcaption className="mb-1 text-[11px] uppercase tracking-widest text-slate-500">Before</figcaption>
                {current.before_preview_url ? (
                  <img src={previewUrl(current.before_preview_url)} alt="before sentinel" className="h-44 w-full object-cover" />
                ) : null}
                <p className="mt-1 text-xs text-slate-400">
                  {current.before_stac_id || "—"} · {current.before_date || "—"} · cloud {current.before_cloud ?? "—"}%
                </p>
              </figure>
              <figure className="rounded border border-line bg-panel p-2">
                <figcaption className="mb-1 text-[11px] uppercase tracking-widest text-slate-500">After</figcaption>
                {current.after_preview_url ? (
                  <img src={previewUrl(current.after_preview_url)} alt="after sentinel" className="h-44 w-full object-cover" />
                ) : null}
                <p className="mt-1 text-xs text-slate-400">
                  {current.after_stac_id || "—"} · {current.after_date || "—"} · cloud {current.after_cloud ?? "—"}%
                </p>
              </figure>
            </div>
          ) : null}
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard label="Before water area" value={`${current.before_water_area_km2 ?? "—"} km²`} />
            <KpiCard label="After water area" value={`${current.after_water_area_km2 ?? "—"} km²`} />
            <KpiCard label="Newly water-covered" value={`${newlyKm2 ?? "—"} km²`} />
            <KpiCard label="New water % of AOI" value={`${newlyPct ?? "—"}%`} />
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard label="Relative water change" value={`${current.percentage_change ?? "—"}%`} />
            <KpiCard label="Primary KPI (new water vs before)" value={`${current.flooded_area} km²`} />
            {demoMode ? (
              <>
                <KpiCard label="Population (demo estimate)" value={String(current.affected_population)} />
                <KpiCard label="Roads / buildings (demo)" value={`${current.affected_roads} / ${current.affected_buildings}`} />
              </>
            ) : (
              <>
                <KpiCard label="Impact overlays" value="UNAVAILABLE" hint="No census/asset dataset wired" />
                <KpiCard label="Validated flood boundary" value="No" hint={current.spatial_resolution || "preview GSD"} />
              </>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge value={current.severity} />
            <span className="text-xs text-slate-400">
              {current.estimate_label ?? "Satellite-derived water-change indication — requires validation"}
            </span>
          </div>
          <div className="grid gap-3 lg:grid-cols-[2fr_1fr]">
            <div className="h-[380px]">
              <SatelliteOverlayMap
                footprint={null}
                overlays={overlay as GeoJSON.GeoJsonObject}
                opacity={opacity}
                showFootprint={false}
                showDetections
              />
            </div>
            <div className="space-y-3 rounded border border-line bg-panel p-3">
              <label className="flex items-center gap-2 text-xs text-slate-400">
                <input type="checkbox" checked={showNewly} onChange={(e) => setShowNewly(e.target.checked)} />
                Newly flooded / newly water-covered
              </label>
              <label className="flex items-center gap-2 text-xs text-slate-400">
                <input type="checkbox" checked={showAfter} onChange={(e) => setShowAfter(e.target.checked)} />
                After water mask
              </label>
              <label className="flex items-center gap-2 text-xs text-slate-400">
                <input type="checkbox" checked={showBefore} onChange={(e) => setShowBefore(e.target.checked)} />
                Before water mask
              </label>
              <label className="flex items-center gap-2 text-xs text-slate-400">
                <input type="checkbox" checked={showHeat} onChange={(e) => setShowHeat(e.target.checked)} />
                Change heatmap
              </label>
              <label className="block text-xs text-slate-400">
                Overlay opacity
                <input
                  type="range"
                  className="mt-1 w-full"
                  min={0.1}
                  max={0.9}
                  step={0.05}
                  value={opacity}
                  onChange={(e) => setOpacity(Number(e.target.value))}
                />
              </label>
              <p className="text-[11px] text-slate-500">
                Orange = newly water-covered · Cyan = after water · Violet = before water. Permanent wetlands appear in
                before/after masks but not necessarily in the newly covered layer.
              </p>
              <p className="text-sm text-slate-300">Confidence {current.confidence}</p>
              <p className="text-xs text-slate-500 whitespace-pre-wrap">{current.notes}</p>
            </div>
          </div>
        </>
      ) : (
        <EmptyState message="No flood change event yet. Run analysis when two suitable Sentinel-2 scenes are available." />
      )}
    </div>
  );
}
