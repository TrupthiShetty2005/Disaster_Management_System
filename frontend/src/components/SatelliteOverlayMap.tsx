import { useMemo } from "react";
import { GeoJSON, MapContainer, TileLayer } from "react-leaflet";
import { LIVE_MAP_CENTER } from "../constants/demo";
import { DARK_BASEMAP } from "../maps/basemap";
import "leaflet/dist/leaflet.css";

function layerStyle(name: string | undefined, opacity: number, intensity?: number) {
  const n = (name || "").toLowerCase();
  if (n.includes("newly") || n.includes("expansion")) {
    return { color: "#f97316", fillColor: "#ea580c", fillOpacity: intensity != null ? Math.min(0.9, opacity * (0.4 + intensity)) : opacity, weight: 1 };
  }
  if (n.includes("after")) {
    return { color: "#38bdf8", fillColor: "#0ea5e9", fillOpacity: intensity != null ? Math.min(0.7, opacity * 0.55) : opacity * 0.55, weight: 1 };
  }
  if (n.includes("before")) {
    return { color: "#a78bfa", fillColor: "#8b5cf6", fillOpacity: intensity != null ? Math.min(0.55, opacity * 0.4) : opacity * 0.35, weight: 1 };
  }
  const fill = intensity != null && !Number.isNaN(intensity) ? Math.min(0.85, opacity * (0.35 + intensity)) : opacity;
  return { color: "#38bdf8", fillColor: "#0ea5e9", fillOpacity: fill, weight: intensity != null ? 0 : 1 };
}

export function SatelliteOverlayMap({
  footprint,
  overlays,
  opacity,
  showFootprint,
  showDetections,
}: {
  footprint: GeoJSON.GeoJsonObject | null;
  overlays: GeoJSON.GeoJsonObject | null;
  opacity: number;
  showFootprint: boolean;
  showDetections: boolean;
}) {
  const center = useMemo<[number, number]>(() => LIVE_MAP_CENTER, []);
  return (
    <MapContainer center={center} zoom={12} className="h-full min-h-[280px] w-full rounded border border-line" scrollWheelZoom={false}>
      <TileLayer attribution={DARK_BASEMAP.attribution} url={DARK_BASEMAP.url} />
      {showFootprint && footprint ? (
        <GeoJSON data={footprint} style={{ color: "#f59e0b", weight: 1, fillOpacity: 0.08 }} />
      ) : null}
      {showDetections && overlays ? (
        <GeoJSON
          data={overlays}
          style={(feat) => {
            const props = (feat?.properties || {}) as { intensity?: number; name?: string };
            const intensity = props.intensity != null ? Number(props.intensity) : undefined;
            return layerStyle(props.name, opacity, intensity);
          }}
          onEachFeature={(feat, layer) => {
            const label = document.createElement("span");
            label.textContent = (feat.properties as { name?: string } | null)?.name ?? "detection";
            layer.bindPopup(label);
          }}
        />
      ) : null}
    </MapContainer>
  );
}

export function polygonAreaKm2(geo: GeoJSON.GeoJsonObject | null): number | null {
  if (!geo || geo.type !== "FeatureCollection") return null;
  const fc = geo as GeoJSON.FeatureCollection;
  const feat = fc.features[0];
  if (!feat || feat.geometry.type !== "Polygon") return null;
  const ring = feat.geometry.coordinates[0];
  let sum = 0;
  for (let i = 0; i < ring.length - 1; i += 1) {
    const [x1, y1] = ring[i];
    const [x2, y2] = ring[i + 1];
    sum += x1 * y2 - x2 * y1;
  }
  const deg2 = Math.abs(sum / 2);
  return deg2 * 111.32 * 110.57;
}
