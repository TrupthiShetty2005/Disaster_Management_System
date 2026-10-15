import "maplibre-gl/dist/maplibre-gl.css";
import "./damage3d.css";
import maplibregl, { type ExpressionSpecification, type LngLatBoundsLike, type Map as MlMap, type StyleSpecification } from "maplibre-gl";
import { useEffect, useRef, useState } from "react";
import { getAnalysisAssets } from "../api/endpoints";
import type { Analysis, AnalysisAssets } from "../api/types";
import { Empty, ErrorBox, Kpi, Loading, Source } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { fmt, inr } from "../lib/format";
import { IMAGERY_BASEMAP } from "./basemap";
import { BUILDING_COLORS, buildingColorExpr, damageBounds, focusTargets, HAZARD_COLORS, hazardColorExpr, heightNote, LINE_COLORS, lineColorExpr, tooltipHtml, type HoverKind } from "./damage3d";

const STYLE: StyleSpecification = {
  version: 8,
  sources: {
    imagery: {
      type: "raster",
      tiles: [IMAGERY_BASEMAP.url],
      tileSize: 256,
      maxzoom: 19,
      attribution: IMAGERY_BASEMAP.attribution,
    },
  },
  layers: [
    {
      id: "imagery",
      type: "raster",
      source: "imagery",
      paint: { "raster-brightness-max": 0.75, "raster-saturation": -0.3 },
    },
  ],
};

const HOVER_LAYERS: Record<string, HoverKind> = {
  "buildings-3d": "building",
  facilities: "facility",
  "lines-affected": "line",
  "lines-context": "line",
  "hazard-fill": "hazard",
};

const asBounds = (b: [[number, number], [number, number]]): LngLatBoundsLike => b;
const bboxBounds = (b: number[]): LngLatBoundsLike => [
  [b[0], b[1]],
  [b[2], b[3]],
];

function addLayers(map: MlMap, a: Analysis, assets: AnalysisAssets) {
  const empty: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };
  map.addSource("hazard", { type: "geojson", data: a.geojson ?? empty });
  map.addSource("buildings", { type: "geojson", data: assets.buildings ?? empty });
  map.addSource("lines", { type: "geojson", data: assets.lines ?? empty });
  map.addSource("facilities", { type: "geojson", data: assets.facilities ?? empty });
  map.addLayer({
    id: "hazard-fill",
    type: "fill",
    source: "hazard",
    paint: { "fill-color": hazardColorExpr as ExpressionSpecification, "fill-opacity": 0.38 },
  });
  map.addLayer({
    id: "hazard-line",
    type: "line",
    source: "hazard",
    paint: { "line-color": hazardColorExpr as ExpressionSpecification, "line-width": 1.2 },
  });
  map.addLayer({
    id: "lines-context",
    type: "line",
    source: "lines",
    filter: ["!", ["get", "affected"]],
    paint: { "line-color": "#cbd5e1", "line-opacity": 0.35, "line-width": 1.2 },
  });
  map.addLayer({
    id: "lines-affected",
    type: "line",
    source: "lines",
    filter: ["get", "affected"],
    layout: { "line-cap": "round", "line-join": "round" },
    paint: {
      "line-color": lineColorExpr as ExpressionSpecification,
      "line-width": ["interpolate", ["linear"], ["zoom"], 12, 2, 17, 6],
    },
  });
  map.addLayer({
    id: "buildings-3d",
    type: "fill-extrusion",
    source: "buildings",
    paint: {
      "fill-extrusion-color": buildingColorExpr as ExpressionSpecification,
      "fill-extrusion-height": ["get", "height_m"],
      "fill-extrusion-base": 0,
      "fill-extrusion-opacity": 0.92,
    },
  });
  map.addLayer({
    id: "facilities",
    type: "circle",
    source: "facilities",
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 11, 4, 17, 9],
      "circle-color": ["case", ["get", "affected"], "#ef4444", "#34d399"],
      "circle-stroke-color": "#ffffff",
      "circle-stroke-width": 2,
      "circle-pitch-alignment": "map",
    },
  });
}

function Legend({ flood }: { flood: boolean }) {
  const sw = (c: string, round = false) => <span className={`inline-block h-2.5 w-2.5 ${round ? "rounded-full border border-white" : ""}`} style={{ background: c }} />;
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-300">
      {Object.entries(BUILDING_COLORS)
        .filter(([k]) => flood || k !== "persistent_water")
        .map(([k, v]) => (
          <span key={k} className="flex items-center gap-1">
            {sw(v.color)} {v.label}
          </span>
        ))}
      {Object.entries(HAZARD_COLORS)
        .filter(([k]) => (flood ? k !== "burned" : k === "burned"))
        .map(([k, v]) => (
          <span key={k} className="flex items-center gap-1">
            <span className="inline-block h-2.5 w-2.5 opacity-60" style={{ background: v.color }} /> {v.label} (draped)
          </span>
        ))}
      <span className="flex items-center gap-1">{sw(LINE_COLORS.road)} Affected road</span>
      <span className="flex items-center gap-1">{sw(LINE_COLORS.railway)} Affected railway</span>
      <span className="flex items-center gap-1">{sw(LINE_COLORS.power_line)} Affected power line</span>
      <span className="flex items-center gap-1">{sw("#cbd5e1")} Unaffected line</span>
      <span className="flex items-center gap-1">{sw("#ef4444", true)} Facility affected</span>
      <span className="flex items-center gap-1">{sw("#34d399", true)} Facility nearby</span>
    </div>
  );
}

function Scene({ a, assets }: { a: Analysis; assets: AnalysisAssets }) {
  const el = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const [glError, setGlError] = useState<string | null>(null);
  const [exaggeration, setExaggeration] = useState(1);
  const exaggerationRef = useRef(exaggeration);
  const focus = damageBounds(assets);
  const targets = focusTargets(assets);

  useEffect(() => {
    exaggerationRef.current = exaggeration;
    const map = mapRef.current;
    if (map?.getLayer("buildings-3d")) map.setPaintProperty("buildings-3d", "fill-extrusion-height", ["*", ["get", "height_m"], exaggeration]);
  }, [exaggeration]);

  useEffect(() => {
    if (!el.current) return;
    let map: MlMap;
    try {
      map = new maplibregl.Map({
        container: el.current,
        style: STYLE,
        bounds: focus ? asBounds(focus) : bboxBounds(a.bbox),
        fitBoundsOptions: { padding: 60, maxZoom: 17.5 },
        pitch: 55,
        bearing: -20,
        maxPitch: 80,
        attributionControl: { compact: true },
      });
    } catch (e) {
      setGlError(e instanceof Error ? e.message : "WebGL is not available in this browser");
      return;
    }
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    map.on("load", () => {
      addLayers(map, a, assets);
      map.setPaintProperty("buildings-3d", "fill-extrusion-height", ["*", ["get", "height_m"], exaggerationRef.current]);
    });
    const popup = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
      maxWidth: "280px",
      className: "damage-popup",
    });
    map.on("mousemove", (e) => {
      const layers = Object.keys(HOVER_LAYERS).filter((id) => map.getLayer(id));
      const f = layers.length ? map.queryRenderedFeatures(e.point, { layers })[0] : undefined;
      map.getCanvas().style.cursor = f ? "pointer" : "";
      if (!f) {
        popup.remove();
        return;
      }
      popup
        .setLngLat(e.lngLat)
        .setHTML(tooltipHtml(HOVER_LAYERS[f.layer.id], f.properties ?? {}))
        .addTo(map);
    });
    map.on("mouseout", () => popup.remove());
    return () => {
      popup.remove();
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [a.id, assets]);

  const cam = (fn: (m: MlMap) => void) => () => mapRef.current && fn(mapRef.current);
  const btn = "rounded border border-line bg-ink/80 px-2 py-1 text-[11px] text-slate-200 hover:bg-white/10";
  if (glError) return <ErrorBox message={`3D view unavailable: ${glError}`} />;
  return (
    <div>
      <div className="relative">
        <div ref={el} className="h-[560px] w-full overflow-hidden rounded border border-line" />
        <div className="absolute left-2 right-14 top-2 flex flex-wrap gap-1">
          <button className={btn} onClick={cam((m) => m.easeTo({ pitch: Math.min(m.getPitch() + 15, 80) }))}>
            Tilt +
          </button>
          <button className={btn} onClick={cam((m) => m.easeTo({ pitch: Math.max(m.getPitch() - 15, 0) }))}>
            Tilt −
          </button>
          <button className={btn} onClick={cam((m) => m.easeTo({ bearing: m.getBearing() - 45 }))}>
            ⟲ Rotate
          </button>
          <button className={btn} onClick={cam((m) => m.easeTo({ bearing: m.getBearing() + 45 }))}>
            Rotate ⟳
          </button>
          <button className={btn} onClick={cam((m) => m.easeTo({ pitch: 0, bearing: 0 }))}>
            Top-down
          </button>
          {focus ? (
            <button className={btn} onClick={cam((m) => m.fitBounds(asBounds(focus), { padding: 60, maxZoom: 17.5, pitch: 55 }))}>
              Zoom to damage
            </button>
          ) : null}
          <button className={btn} onClick={cam((m) => m.fitBounds(bboxBounds(a.bbox), { padding: 20, pitch: 45 }))}>
            Whole area
          </button>
          <button className={`${btn} ${exaggeration > 1 ? "border-amber-500/60 text-amber-200" : ""}`} aria-pressed={exaggeration > 1} onClick={() => setExaggeration((x) => (x > 1 ? 1 : 3))}>
            Heights: {exaggeration > 1 ? "×3 (exaggerated)" : "true scale"}
          </button>
        </div>
        <p className="pointer-events-none absolute bottom-9 left-2 rounded bg-ink/80 px-2 py-0.5 text-[10px] text-slate-400">Right-drag / Ctrl-drag to tilt &amp; rotate</p>
      </div>
      {targets.length ? (
        <div className="mt-2 flex flex-wrap items-center gap-1 text-[11px]">
          <span className="text-slate-500">Fly to:</span>
          {targets.map((t) => (
            <button key={t.id} className={btn} onClick={cam((m) => m.flyTo({ center: t.center, zoom: 18.5, pitch: 60 }))}>
              <span className="mr-1 inline-block h-2 w-2" style={{ background: t.color }} />
              {t.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export default function DamageView3D({ a }: { a: Analysis }) {
  const state = useAsync(() => getAnalysisAssets(a.id), [a.id]);
  const assets = state.data;
  if (state.loading && !assets) return <Loading text="Fetching OpenStreetMap building footprints and clipping them to the hazard footprint… (first view of an analysis can take up to a minute)" />;
  if (state.error) return <ErrorBox message={`Could not load 3D assets: ${state.error}`} onRetry={state.reload} />;
  if (!assets) return null;
  if (assets.status === "no_hazard_footprint") return <Empty>No hazard footprint was detected, so there is nothing to show in 3D.</Empty>;
  if (assets.status === "osm_unavailable") return <ErrorBox message={`OpenStreetMap infrastructure could not be fetched: ${assets.detail ?? "Overpass unavailable"}`} onRetry={state.reload} />;
  const s = assets.summary!;
  const loss = a.impact?.loss;
  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
        <Kpi label="Buildings affected" value={fmt(s.buildings_affected)} color="#ef4444" hint={`${fmt(s.buildings_edge_contact)} edge contact · ${fmt(s.buildings_nearby_unaffected)} nearby`} />
        <Kpi label="Roads affected" value={`${fmt(s.road_km_affected, 2)} km`} color={LINE_COLORS.road} hint={`rail ${fmt(s.railway_km_affected, 2)} km`} />
        <Kpi label="Power lines affected" value={`${fmt(s.power_line_km_affected, 2)} km`} color={LINE_COLORS.power_line} />
        <Kpi label="Facilities affected" value={fmt(s.facilities_affected)} color="#f97316" hint={`${fmt(assets.facilities?.features.length ?? 0)} mapped nearby`} />
        <Kpi label="Estimated loss" value={loss ? inr(loss.estimated_loss_crore) : "—"} hint={loss ? `${Math.round(loss.damage_ratio * 100)}% damage ratio (planning assumption)` : undefined} />
      </div>
      {s.buildings_affected === 0 ? (
        <p className="text-xs text-amber-200/80">No mapped building has its centroid inside the hazard footprint. Nearby buildings (within {assets.limits?.context_radius_m} m) are shown grey for context.</p>
      ) : null}
      <Scene a={a} assets={assets} />
      <Legend flood={a.kind === "flood"} />
      <Source>
        Buildings: OpenStreetMap footprints extruded by height — {assets.method?.height} {heightNote(assets)} {assets.method?.affected_rule}
        {assets.method?.flood_depth ? ` Flood depth: ${assets.method.flood_depth}` : ""}{" "}
        {assets.limits?.truncated ? `Display capped at ${fmt(assets.limits.max_affected_buildings)} affected and ${fmt(assets.limits.max_context_buildings)} nearby buildings.` : ""} Basemap:{" "}
        {IMAGERY_BASEMAP.attribution.replace(/&copy;/g, "©")}. {assets.source}.
      </Source>
    </div>
  );
}
