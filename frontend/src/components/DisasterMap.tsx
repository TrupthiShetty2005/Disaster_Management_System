import { useEffect, useMemo, useRef, useState } from "react";
import { GeoJSON, MapContainer, TileLayer, useMap, useMapEvents } from "react-leaflet";
import { LIVE_MAP_CENTER } from "../constants/demo";
import { activeBasemapLabel, DARK_BASEMAP, IMAGERY_BASEMAP } from "../maps/basemap";
import type { Layer } from "leaflet";
import L from "leaflet";
import type { GisCollection, GisFeature, LayerId, LayerVisibility } from "../types/gis";
import {
  DEFAULT_LAYER_VISIBILITY,
  INVENTORY_LAYER_IDS,
  LAYER_LABELS,
  inventoryLayerHasFeatures,
  searchFeatures,
  showMapLayerToggle,
  toggleLayer,
} from "../types/gis";
import { layerCountLegend } from "../utils/dashboardMap";
import { useDataSources } from "./DataModeBadge";
import { isMockMode } from "../services/apiClient";
import "leaflet/dist/leaflet.css";

const VECTOR_LAYERS: LayerId[] = [
  "disasters",
  "alerts",
  "floodCurrent",
  "floodPredicted",
  "risk",
  "population",
  "roads",
  "railways",
  "waterways",
  "buildings",
  "evacuation",
  "rescue",
  "hospitals",
  "shelters",
];

const BUILDINGS_MIN_ZOOM = 15;

function riskColor(level?: string) {
  if (level === "critical") return "#ef4444";
  if (level === "high") return "#f97316";
  if (level === "moderate") return "#eab308";
  return "#22c55e";
}

function styleFeature(feature?: GisFeature) {
  const p = feature?.properties;
  const layer = p?.layer;
  if (layer === "floodCurrent") return { color: "#38bdf8", fillColor: "#0ea5e9", fillOpacity: 0.35, weight: 1 };
  if (layer === "floodPredicted") return { color: "#818cf8", fillColor: "#6366f1", fillOpacity: 0.2, weight: 1, dashArray: "4 3" };
  if (layer === "risk") return { color: riskColor(p?.riskLevel), fillColor: riskColor(p?.riskLevel), fillOpacity: 0.28, weight: 1 };
  if (layer === "population") return { color: "#f472b6", fillColor: "#ec4899", fillOpacity: Math.min(0.45, (p?.density ?? 500) / 4000), weight: 0 };
  if (layer === "roads") return { color: p?.status === "blocked" ? "#f87171" : "#94a3b8", weight: 3 };
  if (layer === "railways") return { color: "#a8a29e", weight: 2, dashArray: "6 4" };
  if (layer === "waterways") return { color: "#38bdf8", weight: 2 };
  if (layer === "buildings") return { color: "#cbd5e1", fillColor: "#64748b", fillOpacity: 0.7, weight: 1 };
  return { color: "#e2e8f0", weight: 1 };
}

function pointToLayer(feature: GisFeature, latlng: L.LatLngExpression) {
  const p = feature.properties;
  const layer = p.layer;
  if (layer === "alerts") {
    const color = p.officialWarning ? "#34d399" : "#f59e0b";
    return L.circleMarker(latlng, {
      radius: 8,
      color,
      fillColor: color,
      fillOpacity: 0.9,
      weight: 2,
    });
  }
  const colors: Partial<Record<LayerId, string>> = {
    disasters: "#ef4444",
    evacuation: "#34d399",
    rescue: "#f59e0b",
    hospitals: "#f43f5e",
    shelters: "#a78bfa",
  };
  return L.circleMarker(latlng, {
    radius: layer === "disasters" ? 10 : 7,
    color: colors[layer] ?? "#94a3b8",
    fillOpacity: 0.9,
    weight: 2,
  });
}

function ZoomTracker({ onZoom }: { onZoom: (z: number) => void }) {
  useMapEvents({
    zoomend: (e) => onZoom(e.target.getZoom()),
    zoom: (e) => onZoom(e.target.getZoom()),
  });
  return null;
}

/** Popup text comes from OSM tags and alert fields; never pass it to Leaflet as an HTML string. */
export function popupContent(feature: GisFeature): HTMLElement {
  const p = feature.properties;
  const lines = [`${p.layer}${p.feature_type ? ` · ${p.feature_type}` : ""}`];
  if (p.osm_id != null) lines.push(`OSM ${p.osm_type || "id"} ${p.osm_id}`);
  if (p.source) lines.push(`Source: ${p.source}`);
  if (p.retrieved_at) lines.push(`Retrieved ${p.retrieved_at}`);
  if (p.status) lines[lines.length - 1] += ` · ${p.status}`;
  if (p.description) lines.push(String(p.description));

  const root = document.createElement("div");
  const title = document.createElement("strong");
  title.textContent = String(p.name ?? "");
  root.appendChild(title);
  for (const text of lines) {
    root.appendChild(document.createElement("br"));
    root.appendChild(document.createTextNode(text));
  }
  return root;
}

function bindPopup(feature: GisFeature, layer: Layer) {
  layer.bindPopup(popupContent(feature));
}

function FitControl({
  catalog,
  visible,
  token,
}: {
  catalog: Record<string, GisCollection>;
  visible: LayerVisibility;
  token: number;
}) {
  const map = useMap();
  useEffect(() => {
    const features = VECTOR_LAYERS.filter((id) => visible[id]).flatMap((id) => catalog[id]?.features ?? []);
    if (!features.length) return;
    const layer = L.geoJSON({ type: "FeatureCollection", features } as never);
    const bounds = layer.getBounds();
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [28, 28], maxZoom: 14 });
  }, [catalog, map, token, visible]);
  return null;
}

function FlyTo({ target }: { target: [number, number] | null }) {
  const map = useMap();
  useEffect(() => {
    if (target) map.flyTo(target, 15, { duration: 0.6 });
  }, [map, target]);
  return null;
}

function RecenterAoi({ target }: { target?: [number, number] }) {
  const map = useMap();
  const last = useRef("");
  useEffect(() => {
    if (!target) return;
    const key = `${target[0].toFixed(5)},${target[1].toFixed(5)}`;
    if (key === last.current) return;
    last.current = key;
    map.setView(target, 12);
  }, [map, target]);
  return null;
}

export function DisasterMap({
  catalog,
  onSelect,
  onFeatureAction,
  boundary,
  footprint,
  center,
  osmUnavailable = false,
}: {
  catalog: Record<string, GisCollection>;
  onSelect: (feature: GisFeature | null) => void;
  onFeatureAction?: (feature: GisFeature) => void;
  boundary?: GeoJSON.GeoJsonObject | null;
  footprint?: GeoJSON.GeoJsonObject | null;
  center?: [number, number];
  osmUnavailable?: boolean;
}) {
  const [visible, setVisible] = useState<LayerVisibility>(DEFAULT_LAYER_VISIBILITY);
  const [fitToken, setFitToken] = useState(0);
  const [query, setQuery] = useState("");
  const [fly, setFly] = useState<[number, number] | null>(null);
  const [zoom, setZoom] = useState(12);
  const dataSources = useDataSources();
  const liveMode = dataSources
    ? !(dataSources.use_mock_providers === true || dataSources.data_mode === "DEMO DATA")
    : !isMockMode();

  const allFeatures = useMemo(
    () => VECTOR_LAYERS.flatMap((id) => catalog[id]?.features ?? []),
    [catalog],
  );
  const hits = searchFeatures(allFeatures, query);

  return (
    <div className="relative z-0 isolate h-full min-h-[420px] overflow-hidden rounded border border-line">
      <MapContainer center={center ?? LIVE_MAP_CENTER} zoom={12} className="h-full w-full" scrollWheelZoom={false}>
        {visible.satellite ? (
          <TileLayer attribution={IMAGERY_BASEMAP.attribution} url={IMAGERY_BASEMAP.url} />
        ) : (
          <TileLayer attribution={DARK_BASEMAP.attribution} url={DARK_BASEMAP.url} />
        )}
        {boundary ? (
          <GeoJSON data={boundary as never} style={{ color: "#fbbf24", weight: 2, fillOpacity: 0.06, dashArray: "6 4" }} />
        ) : null}
        {footprint ? (
          <GeoJSON data={footprint as never} style={{ color: "#22d3ee", weight: 2, fillOpacity: 0.04, dashArray: "2 4" }} />
        ) : null}
        {VECTOR_LAYERS.filter((id) => {
          if (!visible[id] || !catalog[id]?.features?.length) return false;
          if (id === "buildings" && zoom < BUILDINGS_MIN_ZOOM) return false;
          if (liveMode && INVENTORY_LAYER_IDS.includes(id) && !(catalog[id].features?.length)) return false;
          return true;
        }).map((id) => (
          <GeoJSON
            key={`${id}-${visible[id]}`}
            data={catalog[id] as never}
            style={(feat) => styleFeature(feat as unknown as GisFeature)}
            pointToLayer={(feat, latlng) => pointToLayer(feat as unknown as GisFeature, latlng)}
            onEachFeature={(feat, layer) => {
              const feature = feat as unknown as GisFeature;
              bindPopup(feature, layer);
              layer.on("click", () => {
                onSelect(feature);
                onFeatureAction?.(feature);
              });
            }}
          />
        ))}
        <ZoomTracker onZoom={setZoom} />
        <FitControl catalog={catalog} visible={visible} token={fitToken} />
        <FlyTo target={fly} />
        <RecenterAoi target={center} />
      </MapContainer>

      <div className="absolute left-3 top-3 z-[1000] w-56 rounded border border-line bg-ink/90 p-2 text-xs backdrop-blur">
        <p className="mb-1 font-medium uppercase tracking-wider text-slate-400">Layers</p>
        {(Object.keys(LAYER_LABELS) as LayerId[]).map((id) => {
          const count = id === "satellite" ? 1 : catalog[id]?.features?.length ?? 0;
          if (!showMapLayerToggle(id, liveMode, count, osmUnavailable)) return null;
          const extra = id === "buildings" && zoom < BUILDINGS_MIN_ZOOM ? " (zoom in)" : "";
          return (
            <label key={id} className="flex cursor-pointer items-center gap-2 py-0.5 text-slate-300">
              <input
                type="checkbox"
                checked={visible[id]}
                onChange={() => setVisible((v) => toggleLayer(v, id))}
              />
              {LAYER_LABELS[id]}
              {id === "satellite" ? "" : ` (${count})`}
              {extra}
            </label>
          );
        })}
        <p className="mt-1 text-[11px] text-slate-500">{activeBasemapLabel(visible.satellite)}</p>
        <button
          className="mt-2 w-full rounded border border-line px-2 py-1 text-amber-300 hover:bg-white/5"
          onClick={() => setFitToken((n) => n + 1)}
        >
          Fit visible layers
        </button>
      </div>

      <div className="absolute right-3 top-3 z-[1000] w-56 rounded border border-line bg-ink/90 p-2 text-xs backdrop-blur">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search location…"
          className="w-full rounded border border-line bg-panel px-2 py-1 text-slate-200 outline-none"
        />
        {hits.map((h) => (
          <button
            key={h.properties.id}
            className="mt-1 block w-full truncate rounded px-2 py-1 text-left text-slate-300 hover:bg-white/10"
            onClick={() => {
              onSelect(h);
              if (h.geometry.type === "Point") {
                const [lng, lat] = h.geometry.coordinates;
                setFly([lat, lng]);
              } else if (h.geometry.type === "Polygon") {
                const [lng, lat] = h.geometry.coordinates[0][0];
                setFly([lat, lng]);
              } else {
                const [lng, lat] = h.geometry.coordinates[0];
                setFly([lat, lng]);
              }
              setQuery("");
            }}
          >
            {h.properties.name}
          </button>
        ))}
        <div className="mt-2 space-y-1 text-[11px] text-slate-400">
          <p className="uppercase tracking-wider">Legend</p>
          <p>{layerCountLegend(catalog)}</p>
          <p><span className="inline-block h-2 w-2 bg-sky-400" /> Current flood</p>
          <p><span className="inline-block h-2 w-2 bg-amber-400" /> Heuristic alert</p>
          <p><span className="inline-block h-2 w-2 bg-emerald-400" /> Official alert</p>
          <p><span className="inline-block h-2 w-2 bg-amber-200" /> AOI boundary</p>
          <p><span className="inline-block h-2 w-2 bg-cyan-400" /> Sentinel footprint</p>
          {inventoryLayerHasFeatures(catalog, "rescue") ? (
            <p><span className="inline-block h-2 w-2 bg-amber-400" /> Rescue unit</p>
          ) : (
            <p>Population / predicted flood / rescue: no live feed</p>
          )}
        </div>
      </div>
    </div>
  );
}
