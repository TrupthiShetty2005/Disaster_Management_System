import { lazy, Suspense, useEffect, useState } from "react";
import { GeoJSON, ImageOverlay, Rectangle } from "react-leaflet";
import { useSearchParams } from "react-router-dom";
import { apiUrl, assetUrl } from "../api/client";
import { getAnalyses, getAnalysis, getDistricts, getScenes, getStations, previewUrl, runAnalysis, type AnalyzeRequest, type AreaQuery } from "../api/endpoints";
import type { Analysis, BBox, Scene } from "../api/types";
import { ImpactSummary } from "../components/ImpactSummary";
import { Async, Card, Empty, ErrorBox, Kpi, Loading, PageHeader, Source } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { fmt, fmtDate, fmtDateTime } from "../lib/format";
import { KarnatakaMap } from "../maps/KarnatakaMap";

const DamageView3D = lazy(() => import("../maps/DamageView3D"));

type Mode = "flood-sar" | "flood-optical" | "burn";
const MODES: { id: Mode; label: string; hint: string }[] = [
  { id: "flood-sar", label: "Flood · Sentinel-1 radar", hint: "Sees through cloud — best during monsoon. Water appears dark in VV backscatter." },
  { id: "flood-optical", label: "Flood · Sentinel-2 optical", hint: "NDWI water index with cloud masking. Needs a clear-sky scene." },
  { id: "burn", label: "Burn scar · Sentinel-2", hint: "dNBR (pre-fire NBR − post-fire NBR), USGS burn-severity classes." },
];

const CLASS_STYLE: Record<string, { color: string; label: string }> = {
  newly_flooded: { color: "#ef4444", label: "Newly flooded" },
  persistent_water: { color: "#38bdf8", label: "Permanent / prior water" },
  burned: { color: "#f97316", label: "Burned area" },
};

const toBounds = (b: BBox): [[number, number], [number, number]] => [
  [b[1], b[0]],
  [b[3], b[2]],
];

function ScenePreview({ scene, bbox, kind }: { scene: Scene; bbox: BBox; kind: "sar" | "truecolor" | "ndwi" | "nbr" }) {
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  return (
    <div className="relative aspect-square w-full overflow-hidden rounded border border-line bg-ink">
      {!loaded && !failed ? <p className="absolute inset-0 flex items-center justify-center text-[11px] text-slate-500">Rendering from Sentinel COG…</p> : null}
      {failed ? <p className="absolute inset-0 flex items-center justify-center p-2 text-center text-[11px] text-red-300">Preview failed</p> : null}
      <img src={apiUrl(previewUrl(scene.key, kind, bbox))} alt={`${scene.sensor} ${scene.date}`} className="h-full w-full object-cover" onLoad={() => setLoaded(true)} onError={() => setFailed(true)} />
    </div>
  );
}

function SceneList({ scenes, bbox, kind, selected, onSelect, previewKind }: { scenes: Scene[]; bbox: BBox; kind: string; selected?: string; onSelect: (k?: string) => void; previewKind: "sar" | "truecolor" }) {
  const [preview, setPreview] = useState<string | null>(null);
  if (!scenes.length) return <Empty>No {kind} scenes over this area in the last 120 days.</Empty>;
  return (
    <div className="space-y-1 text-xs">
      <button className={`w-full rounded border px-2 py-1 text-left ${!selected ? "border-amber-500/60 text-amber-200" : "border-line text-slate-400"}`} onClick={() => onSelect(undefined)}>
        Automatic: latest usable scene
      </button>
      <div className="max-h-72 space-y-1 overflow-auto">
        {scenes.map((s) => (
          <div key={s.key} className={`rounded border px-2 py-1 ${selected === s.key ? "border-amber-500/60" : "border-line"}`}>
            <div className="flex items-center justify-between gap-2">
              <button className="text-left text-slate-200" onClick={() => onSelect(s.key)}>
                {fmtDate(s.date)} · {s.platform}
              </button>
              <button className="text-sky-400" onClick={() => setPreview(preview === s.key ? null : s.key)}>
                {preview === s.key ? "hide" : "preview"}
              </button>
            </div>
            <p className="text-slate-500">
              coverage {Math.round(s.coverage * 100)}%{s.cloud_cover !== null ? ` · cloud ${fmt(s.cloud_cover)}%` : ""}
              {s.orbit_state ? ` · ${s.orbit_state} orbit ${s.relative_orbit}` : ""}
            </p>
            {preview === s.key ? (
              <div className="mt-1">
                <ScenePreview scene={s} bbox={bbox} kind={previewKind} />
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

export function AnalysisResult({ a }: { a: Analysis }) {
  const m = a.metrics as Record<string, number | string | undefined>;
  const severity = (a.metrics.severity_km2 ?? {}) as Record<string, number>;
  const bounds = toBounds(a.image_bounds ?? a.bbox);
  const flood = a.kind === "flood";
  const [params] = useSearchParams();
  const [view, setView] = useState<"2d" | "3d">(params.get("view") === "3d" ? "3d" : "2d");
  const viewToggle = (
    <div className="flex items-center gap-2">
      <div className="flex overflow-hidden rounded border border-line text-xs" role="group" aria-label="Map view">
        {(["2d", "3d"] as const).map((v) => (
          <button key={v} className={`px-2 py-1 ${view === v ? "bg-amber-500/20 text-amber-200" : "text-slate-400 hover:bg-white/5"}`} aria-pressed={view === v} onClick={() => setView(v)}>
            {v === "2d" ? "2D map" : "3D damage view"}
          </button>
        ))}
      </div>
      <span className="text-xs text-slate-500">{fmtDateTime(a.created_at)}</span>
    </div>
  );
  return (
    <div className="space-y-3">
      <Card title={`${flood ? "Flood mapping" : "Burn-scar mapping"} · ${a.area_name}`} actions={viewToggle}>
        <div className="mb-3 grid grid-cols-2 gap-2 md:grid-cols-4">
          {flood ? (
            <>
              <Kpi label="Newly flooded" value={`${fmt(Number(m.newly_flooded_km2), 2)} km²`} color="#ef4444" hint={`${fmtDate(a.before.date)} → ${fmtDate(a.after.date)}`} />
              <Kpi label="Water before" value={`${fmt(Number(m.water_before_km2), 1)} km²`} />
              <Kpi label="Water after" value={`${fmt(Number(m.water_after_km2), 1)} km²`} color="#38bdf8" hint={`${m.water_change_pct !== undefined ? `${Number(m.water_change_pct) > 0 ? "+" : ""}${fmt(Number(m.water_change_pct))}%` : ""}`} />
              <Kpi label="Receded" value={`${fmt(Number(m.receded_km2), 2)} km²`} hint={`valid coverage ${fmt(Number(m.valid_coverage_pct))}%`} />
            </>
          ) : (
            <>
              <Kpi label="Burned area" value={`${fmt(Number(m.burned_area_km2), 2)} km²`} color="#f97316" hint={`${fmtDate(a.before.date)} → ${fmtDate(a.after.date)}`} />
              <Kpi label="High severity" value={`${fmt(severity.high ?? 0, 2)} km²`} color="#ef4444" />
              <Kpi label="Moderate severity" value={`${fmt((severity.moderate_high ?? 0) + (severity.moderate_low ?? 0), 2)} km²`} color="#f59e0b" />
              <Kpi label="Analysed area" value={`${fmt(Number(m.analysed_area_km2))} km²`} hint={`valid ${fmt(Number(m.valid_coverage_pct))}%`} />
            </>
          )}
        </div>
        {view === "3d" ? (
          <div className="mb-3">
            <Suspense fallback={<Loading text="Loading 3D map engine…" />}>
              <DamageView3D a={a} />
            </Suspense>
          </div>
        ) : null}
        <div className={view === "3d" ? "grid gap-3" : "grid gap-3 lg:grid-cols-[1fr_1fr]"}>
          {view === "2d" ? (
            <KarnatakaMap height={420} bounds={bounds} imagery>
              {a.images["change.png"] ? <ImageOverlay url={assetUrl(a.images["change.png"])} bounds={bounds} opacity={0.75} /> : null}
              {a.geojson ? (
                <GeoJSON
                  key={a.id}
                  data={a.geojson}
                  style={(f) => ({ color: CLASS_STYLE[String(f?.properties?.class)]?.color ?? "#facc15", weight: 1, fillOpacity: 0.15 })}
                />
              ) : null}
              <Rectangle bounds={bounds} pathOptions={{ color: "#f59e0b", weight: 1, fill: false, dashArray: "4 4" }} />
            </KarnatakaMap>
          ) : null}
          <div className={view === "3d" ? "grid grid-cols-2 gap-2 md:grid-cols-3" : "grid grid-cols-2 gap-2"}>
            {(["before.png", "after.png"] as const).map((name) =>
              a.images[name] ? (
                <figure key={name}>
                  <img src={assetUrl(a.images[name])} alt={name} className="w-full rounded border border-line" />
                  <figcaption className="mt-1 text-[11px] text-slate-400">
                    {name === "before.png" ? `Before · ${fmtDate(a.before.date)} · ${a.before.platform}` : `After · ${fmtDate(a.after.date)} · ${a.after.platform}`}
                  </figcaption>
                </figure>
              ) : null,
            )}
            {a.images["change.png"] ? (
              <figure className={view === "3d" ? "col-span-2 md:col-span-1" : "col-span-2"}>
                <img src={assetUrl(a.images["change.png"])} alt="change map" className="w-full rounded border border-line bg-black" />
                <figcaption className="mt-1 flex flex-wrap gap-3 text-[11px] text-slate-400">
                  {Object.entries(CLASS_STYLE)
                    .filter(([k]) => (flood ? k !== "burned" : k === "burned"))
                    .map(([k, v]) => (
                      <span key={k} className="flex items-center gap-1">
                        <span className="h-2.5 w-2.5" style={{ background: v.color }} /> {v.label}
                      </span>
                    ))}
                </figcaption>
              </figure>
            ) : null}
          </div>
        </div>
        <Source>
          {String(m.method ?? "")} Scenes: {a.before.item_ids?.[0]} → {a.after.item_ids?.[0]} (Microsoft Planetary Computer). Pixel size ≈ {fmt(Number(m.pixel_size_m))} m.
        </Source>
      </Card>
      <Card title="Infrastructure losses inside the mapped footprint">
        <ImpactSummary impact={a.impact} />
      </Card>
    </div>
  );
}

export default function SatellitePage() {
  const [params, setParams] = useSearchParams();
  const districts = useAsync(() => getDistricts(false), []);
  const stations = useAsync(getStations, []);
  const [area, setArea] = useState<string>(params.get("area") ?? "station:almatti");
  const [mode, setMode] = useState<Mode>("flood-sar");
  const [baseline, setBaseline] = useState<"dry_season" | "previous">("dry_season");
  const [afterKey, setAfterKey] = useState<string | undefined>();
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [result, setResult] = useState<Analysis | null>(null);
  const history = useAsync(getAnalyses, [result?.id]);

  const [kind, id] = area.split(":");
  const areaQuery: AreaQuery = kind === "district" ? { district: id } : { station: id };
  const scenes = useAsync(() => getScenes(areaQuery), [area]);

  useEffect(() => setAfterKey(undefined), [area, mode]);
  useEffect(() => {
    const aid = params.get("analysis");
    if (aid) getAnalysis(aid).then(setResult).catch(() => undefined);
  }, [params]);

  const run = () => {
    const body: AnalyzeRequest =
      mode === "burn"
        ? { kind: "burn", area: areaQuery, after_key: afterKey }
        : { kind: "flood", area: areaQuery, method: mode === "flood-sar" ? "sar" : "optical", baseline, after_key: afterKey };
    setRunning(true);
    setRunError(null);
    runAnalysis(body)
      .then((a) => {
        setResult(a);
        setParams({ analysis: a.id }, { replace: true });
      })
      .catch((e: Error) => setRunError(e.message))
      .finally(() => setRunning(false));
  };

  const sceneKind = mode === "flood-sar" ? "sentinel1" : "sentinel2";
  return (
    <div className="space-y-3">
      <PageHeader
        title="Satellite analysis"
        subtitle="Real Sentinel-1 radar and Sentinel-2 optical scenes over Karnataka, read directly from Microsoft Planetary Computer. Detect new flood water or burned land between two dates, then measure exposed buildings, roads and power lines."
      />
      <div className="grid gap-3 xl:grid-cols-[380px_1fr]">
        <div className="space-y-3">
          <Card title="1 · Area of interest">
            <select className="w-full rounded border border-line bg-ink px-2 py-1.5 text-sm" value={area} onChange={(e) => setArea(e.target.value)}>
              <optgroup label="Dams & river stations">
                {stations.data?.items.map((s) => (
                  <option key={s.id} value={`station:${s.id}`}>
                    {s.name} ({s.river})
                  </option>
                ))}
              </optgroup>
              <optgroup label="District headquarters">
                {districts.data?.items.map((d) => (
                  <option key={d.id} value={`district:${d.id}`}>
                    {d.name} ({d.hq})
                  </option>
                ))}
              </optgroup>
            </select>
            {scenes.data ? <p className="mt-1 text-[11px] text-slate-500">{scenes.data.area_name} · bbox {scenes.data.bbox.map((v) => v.toFixed(2)).join(", ")}</p> : null}
          </Card>
          <Card title="2 · Analysis">
            <div className="space-y-1">
              {MODES.map((m) => (
                <label key={m.id} className={`block cursor-pointer rounded border px-2 py-1.5 text-sm ${mode === m.id ? "border-amber-500/60" : "border-line"}`}>
                  <input type="radio" className="mr-2" checked={mode === m.id} onChange={() => setMode(m.id)} />
                  {m.label}
                  <span className="block text-[11px] text-slate-500">{m.hint}</span>
                </label>
              ))}
            </div>
            {mode !== "burn" ? (
              <div className="mt-2 text-sm">
                <label className="text-slate-400" htmlFor="baseline">
                  Compare against
                </label>
                <select id="baseline" className="ml-2 rounded border border-line bg-ink px-2 py-1" value={baseline} onChange={(e) => setBaseline(e.target.value as "dry_season" | "previous")}>
                  <option value="dry_season">Dry-season baseline (Mar–May)</option>
                  <option value="previous">Previous scene (10–90 days earlier)</option>
                </select>
              </div>
            ) : null}
          </Card>
          <Card title={`3 · "After" scene (${sceneKind === "sentinel1" ? "Sentinel-1" : "Sentinel-2"})`}>
            <Async state={scenes} loadingText="Searching the Sentinel catalogue…">
              {(s) => <SceneList scenes={s[sceneKind]} bbox={s.bbox} kind={sceneKind === "sentinel1" ? "Sentinel-1" : "Sentinel-2"} selected={afterKey} onSelect={setAfterKey} previewKind={sceneKind === "sentinel1" ? "sar" : "truecolor"} />}
            </Async>
          </Card>
          <button className="btn-primary w-full py-3 text-base" onClick={run} disabled={running}>
            {running ? "Processing Sentinel imagery…" : "Run analysis"}
          </button>
          {running ? <Loading text="Reading cloud-optimised GeoTIFFs, mosaicking both dates, classifying change and intersecting with OpenStreetMap. This takes 30 s – 2 min." /> : null}
          {runError ? <ErrorBox message={runError} /> : null}
        </div>
        <div className="space-y-3">
          {result ? <AnalysisResult a={result} /> : <Empty>Choose an area and run an analysis. Results are stored and listed below.</Empty>}
          <Card title="Previous analyses">
            <Async state={history}>
              {(h) =>
                h.items.length ? (
                  <ul className="grid gap-1 text-xs md:grid-cols-2">
                    {h.items.map((a) => (
                      <li key={a.id}>
                        <button className={`w-full rounded border px-2 py-1 text-left hover:bg-white/5 ${result?.id === a.id ? "border-amber-500/60" : "border-line"}`} onClick={() => getAnalysis(a.id).then(setResult)}>
                          <span className="text-slate-200">{a.kind === "flood" ? "Flood" : "Burn"} · {a.area_name}</span>
                          <span className="block text-slate-500">
                            {fmtDate(a.before?.date)} → {fmtDate(a.after?.date)} · run {fmtDateTime(a.created_at)}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <Empty>No analyses yet.</Empty>
                )
              }
            </Async>
          </Card>
        </div>
      </div>
    </div>
  );
}
