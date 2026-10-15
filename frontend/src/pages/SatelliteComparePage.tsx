import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { EstimateCallout } from "../components/EstimateCallout";
import { KpiCard } from "../components/KpiCard";
import { SatelliteOverlayMap } from "../components/SatelliteOverlayMap";
import { DataModeBadge, useDataSources } from "../components/DataModeBadge";
import { ErrorState, LoadingState } from "../components/Feedback";
import { useAsync } from "../hooks/useAsync";
import { isMockMode } from "../services/apiClient";
import {
  compareSatellite,
  fetchSatelliteImages,
  hasGenuinePreview,
  pickBeforeAfter,
  previewSrc,
  SATELLITE_MIN_START,
} from "../services/satellite";
import type { SatelliteAnalysis } from "../types/api";

function fcFeatures(geo: unknown): GeoJSON.Feature[] {
  if (geo && typeof geo === "object" && "features" in geo) {
    return ((geo as { features: unknown[] }).features || []) as GeoJSON.Feature[];
  }
  return [];
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export function SatelliteComparePage() {
  const [start, setStart] = useState(SATELLITE_MIN_START);
  const [end, setEnd] = useState(todayIso());
  const list = useAsync(() => fetchSatelliteImages({ start, end }), [start, end]);
  const dataSources = useDataSources();
  const [result, setResult] = useState<SatelliteAnalysis | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [opacity, setOpacity] = useState(0.45);
  const [showNewly, setShowNewly] = useState(true);
  const [showAfter, setShowAfter] = useState(true);
  const [showBefore, setShowBefore] = useState(false);

  const demoMode =
    isMockMode() || dataSources?.use_mock_providers === true;

  const pair = useMemo(() => pickBeforeAfter(list.data?.items ?? []), [list.data?.items]);
  const before = pair.before;
  const after = pair.after;

  if (list.loading) return <LoadingState />;

  const metrics = result?.metrics || {};
  const overlay = {
    type: "FeatureCollection" as const,
    features: [
      ...(showNewly
        ? fcFeatures(metrics.newly_flooded_geojson).length
          ? fcFeatures(metrics.newly_flooded_geojson)
          : fcFeatures(result?.result_geojson).filter((f) =>
              String((f.properties as { name?: string } | null)?.name || "")
                .toLowerCase()
                .includes("newly"),
            )
        : []),
      ...(showAfter ? fcFeatures(metrics.after_water_geojson) : []),
      ...(showBefore ? fcFeatures(metrics.before_water_geojson) : []),
    ],
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <DataModeBadge />
          <span className="rounded border border-orange-500/40 bg-orange-500/10 px-2 py-1 text-xs text-orange-200">
            Satellite-derived water-change indication — requires validation
          </span>
        </div>
        <Link to="/flood-detection" className="text-xs text-sky-300">
          Flood detection map →
        </Link>
      </div>
      {demoMode ? (
        <EstimateCallout
          title="Demo Mode synthetic before/after"
          kind="SIMULATED DATA"
          value="Uses synthetic rasters. Switch to Real Data Mode for Copernicus Sentinel-2 change detection."
        />
      ) : (
        <EstimateCallout
          title="Satellite-derived water-change indication — requires validation"
          kind="REAL DATA"
          value="Two archive Sentinel-2 previews for the selected Karnataka AOI → water masks → newly water-covered. Preview/RGB heuristic — not a validated flood model and not real-time."
        />
      )}
      <div className="flex flex-wrap items-end gap-2 rounded border border-line bg-panel p-2 text-xs">
        <label className="text-slate-400">
          Start
          <input
            type="date"
            min={SATELLITE_MIN_START}
            value={start}
            onChange={(e) => setStart(e.target.value < SATELLITE_MIN_START ? SATELLITE_MIN_START : e.target.value)}
            className="ml-1 rounded border border-line bg-ink px-1 py-0.5 text-slate-200"
          />
        </label>
        <label className="text-slate-400">
          End
          <input
            type="date"
            min={start}
            max={todayIso()}
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className="ml-1 rounded border border-line bg-ink px-1 py-0.5 text-slate-200"
          />
        </label>
      </div>
      <p className="text-xs text-slate-500">
        Before/after scenes are the oldest and newest STAC items that intersect the selected AOI, ordered by acquisition
        time (not by id names). Permanent water appears in both masks; only the difference is treated as newly
        water-covered. Acquisition dates are not real-time.
      </p>
      {list.error ? <ErrorState message={list.error} /> : null}
      <div className="grid gap-3 md:grid-cols-2">
        <figure className="rounded border border-line bg-panel p-2">
          <figcaption className="mb-1 text-[11px] uppercase tracking-widest text-slate-500">Before preview</figcaption>
          {before && hasGenuinePreview(before) ? (
            <img src={previewSrc(before)} alt="before" className="h-48 w-full object-cover" />
          ) : (
            <p className="text-xs text-slate-500">No genuine preview for the before scene.</p>
          )}
          <p className="mt-1 text-xs text-slate-400">{before?.title}</p>
          <p className="text-[11px] text-slate-500">
            acquired {before?.acquisition_time ? new Date(before.acquisition_time).toISOString() : "—"} ·{" "}
            {String(before?.metadata?.stac_id || before?.id || "—")} · cloud {before?.cloud_cover ?? "—"}%
          </p>
        </figure>
        <figure className="rounded border border-line bg-panel p-2">
          <figcaption className="mb-1 text-[11px] uppercase tracking-widest text-slate-500">After</figcaption>
          {after && hasGenuinePreview(after) ? (
            <img src={previewSrc(after)} alt="after" className="h-48 w-full object-cover" />
          ) : (
            <p className="text-xs text-slate-500">No genuine preview for the after scene.</p>
          )}
          <p className="mt-1 text-xs text-slate-400">{after?.title}</p>
          <p className="text-[11px] text-slate-500">
            acquired {after?.acquisition_time ? new Date(after.acquisition_time).toISOString() : "—"} ·{" "}
            {String(after?.metadata?.stac_id || after?.id || "—")} · cloud {after?.cloud_cover ?? "—"}%
          </p>
        </figure>
      </div>
      <button
        type="button"
        disabled={busy || !before || !after || before.id === after.id}
        className="rounded border border-amber-500/40 px-4 py-2 text-sm text-amber-200"
        onClick={async () => {
          if (!before || !after) return;
          setBusy(true);
          setError(null);
          try {
            setResult(await compareSatellite(before.id, after.id));
          } catch (err) {
            setResult(null);
            setError(err instanceof Error ? err.message : "Compare failed");
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "Detecting water change…" : "Run before/after water change detection"}
      </button>
      {error ? <ErrorState message={error} /> : null}
      {result ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard label="Before water area" value={`${metrics.before_water_area_km2 ?? "—"} km²`} />
          <KpiCard label="After water area" value={`${metrics.after_water_area_km2 ?? "—"} km²`} />
          <KpiCard label="Newly water-covered" value={`${metrics.newly_flooded_area_km2 ?? metrics.flooded_area_km2 ?? "—"} km²`} />
          <KpiCard
            label="New water % / Δ%"
            value={`${metrics.newly_flooded_percentage ?? "—"}% / ${metrics.percentage_change ?? "—"}%`}
          />
        </div>
      ) : null}
      <div className="grid gap-3 lg:grid-cols-[2fr_1fr]">
        <div className="h-[360px]">
          <p className="mb-1 text-[11px] uppercase tracking-widest text-slate-500">Change detection overlay</p>
          <SatelliteOverlayMap
            footprint={(after?.bounding_box as GeoJSON.GeoJsonObject | null) ?? null}
            overlays={overlay as GeoJSON.GeoJsonObject}
            opacity={opacity}
            showFootprint
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
          {result ? <p className="text-xs text-slate-500 whitespace-pre-wrap">{result.summary}</p> : null}
        </div>
      </div>
    </div>
  );
}
