import { useState } from "react";
import { Link } from "react-router-dom";
import { SatelliteOverlayMap, polygonAreaKm2 } from "../components/SatelliteOverlayMap";
import { DataTable } from "../components/DataTable";
import { EmptyState, ErrorState, LoadingState } from "../components/Feedback";
import { useAsync } from "../hooks/useAsync";
import { analyzeSatellite, fetchSatelliteImages, hasGenuinePreview, previewSrc, SATELLITE_MIN_START } from "../services/satellite";
import type { SatelliteAnalysis, SatelliteImageItem } from "../types/api";

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export function SatellitePage() {
  const [start, setStart] = useState(SATELLITE_MIN_START);
  const [end, setEnd] = useState(todayIso());
  const [maxCloud, setMaxCloud] = useState(40);
  const list = useAsync(() => fetchSatelliteImages({ start, end, maxCloud }), [start, end, maxCloud]);
  const [selected, setSelected] = useState<SatelliteImageItem | null>(null);
  const [analysis, setAnalysis] = useState<SatelliteAnalysis | null>(null);
  const [busy, setBusy] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const [opacity, setOpacity] = useState(0.4);
  const [showFootprint, setShowFootprint] = useState(true);
  const [showDetections, setShowDetections] = useState(true);

  if (list.loading) return <LoadingState />;
  if (list.error) return <ErrorState message={list.error} />;
  const items = list.data?.items ?? [];
  const current = selected && items.some((i) => i.id === selected.id) ? selected : items[0];
  const area = polygonAreaKm2((analysis?.result_geojson as GeoJSON.GeoJsonObject | null) ?? null);
  const preview = current && hasGenuinePreview(current) ? previewSrc(current) : "";
  const meta = (current?.metadata || {}) as Record<string, unknown>;

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
      <div className="space-y-3">
        <p className="text-xs text-slate-500">
          Copernicus STAC Sentinel-2 for the <strong>selected Karnataka AOI</strong> (region panel). Default window starts{" "}
          <strong>1 May 2026</strong>. Dates are scene acquisition times — not a real-time feed. Only genuine retrieved
          previews are shown; catalogue metadata, preview, downloadable rasters, and processed analysis are separate.
        </p>
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
          <label className="text-slate-400">
            Max cloud %
            <input
              type="number"
              min={0}
              max={100}
              value={maxCloud}
              onChange={(e) => setMaxCloud(Number(e.target.value))}
              className="ml-1 w-16 rounded border border-line bg-ink px-1 py-0.5 text-slate-200"
            />
          </label>
        </div>
        <div className="h-[420px]">
          <SatelliteOverlayMap
            footprint={(current?.bounding_box as GeoJSON.GeoJsonObject | null) ?? null}
            overlays={(analysis?.result_geojson as GeoJSON.GeoJsonObject | null) ?? null}
            opacity={opacity}
            showFootprint={showFootprint}
            showDetections={showDetections}
          />
        </div>
        <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
          <label className="flex items-center gap-2">
            Footprint
            <input type="checkbox" checked={showFootprint} onChange={(e) => setShowFootprint(e.target.checked)} />
          </label>
          <label className="flex items-center gap-2">
            Detections
            <input type="checkbox" checked={showDetections} onChange={(e) => setShowDetections(e.target.checked)} />
          </label>
          <label className="flex items-center gap-2">
            Opacity {opacity.toFixed(2)}
            <input type="range" min={0.1} max={0.9} step={0.05} value={opacity} onChange={(e) => setOpacity(Number(e.target.value))} />
          </label>
          {area != null ? <span>Approx. overlay area {area.toFixed(1)} km²</span> : null}
        </div>
      </div>
      <div className="space-y-3">
        {current ? (
          <div className="rounded border border-line bg-panel p-3">
            {preview ? (
              <img src={preview} alt="STAC preview" className="mb-2 h-28 w-full rounded object-cover" />
            ) : (
              <EmptyState
                message={
                  current.status === "auth_required" || meta.preview_auth_required
                    ? "Preview requires Copernicus OAuth. Asset was not downloaded."
                    : "Catalogue metadata only — no genuine preview on this item."
                }
              />
            )}
            <p className="text-[11px] uppercase tracking-widest text-slate-500">
              {String(meta.layer || "catalogue")} · {current.status}
            </p>
            <h2 className="font-display text-xl">{current.title}</h2>
            <p className="text-xs text-slate-500">
              {current.source} · acquired {new Date(current.acquisition_time).toLocaleString()} · cloud {current.cloud_cover}%
            </p>
            <p className="mt-1 text-[11px] text-slate-500">
              STAC {String(meta.stac_id || "—")} · full raster downloaded: {String(meta.full_raster_downloaded ?? false)}
            </p>
            <button
              type="button"
              disabled={busy || !preview}
              className="mt-2 w-full rounded border border-amber-500/40 py-1.5 text-sm text-amber-200 disabled:opacity-40"
              onClick={async () => {
                setBusy(true);
                setAnalyzeError(null);
                try {
                  setAnalysis(await analyzeSatellite(current.id, "flood"));
                } catch (err) {
                  setAnalyzeError(err instanceof Error ? err.message : "Analysis failed");
                } finally {
                  setBusy(false);
                }
              }}
            >
              {busy ? "Analyzing…" : "Analyze flood / water (preview heuristic)"}
            </button>
            <Link to="/satellite/compare" className="mt-2 block text-center text-xs text-sky-300">
              Open before/after comparison
            </Link>
          </div>
        ) : (
          <EmptyState message="No Sentinel-2 scenes for this AOI and date window." />
        )}
        {analyzeError ? <ErrorState message={analyzeError} /> : null}
        {analysis ? (
          <div className="rounded border border-line bg-panel p-3 text-sm text-slate-300">
            <p className="text-[11px] uppercase tracking-widest text-slate-500">
              processed analysis · {analysis.estimate_label ?? "Prototype satellite analysis"}
            </p>
            <p>{analysis.summary}</p>
            <p className="mt-1 text-xs text-slate-500">
              Flooded {String(analysis.metrics?.flooded_area_km2 ?? "—")} km² · {String(analysis.metrics?.percent_affected ?? "—")}% · pop{" "}
              {String(analysis.metrics?.estimated_population_affected ?? "—")}
            </p>
          </div>
        ) : null}
      </div>
      <div className="xl:col-span-2">
        <DataTable
          columns={["Scene", "STAC id", "Acquired", "Cloud %", "Layer"]}
          rows={items.map((i) => [
            i.title,
            String(i.metadata?.stac_id || "—"),
            i.acquisition_time,
            String(i.cloud_cover),
            String(i.status),
          ])}
        />
        <div className="mt-2 flex flex-wrap gap-2">
          {items.map((i) => (
            <button
              key={i.id}
              type="button"
              onClick={() => {
                setSelected(i);
                setAnalysis(null);
              }}
              className={`rounded border px-2 py-1 text-xs ${current?.id === i.id ? "border-amber-400 text-amber-200" : "border-line text-slate-400"}`}
            >
              {i.title}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
