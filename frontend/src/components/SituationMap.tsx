import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import { DARK_BASEMAP } from "../maps/basemap";
import type { MapPoint } from "../types/api";
import "leaflet/dist/leaflet.css";

const colors: Record<string, string> = {
  disaster: "#ef4444",
  flood: "#38bdf8",
  evacuation: "#34d399",
  resource: "#f59e0b",
};

export function SituationMap({ points }: { points: MapPoint[] }) {
  return (
    <MapContainer center={[15.3, 76.5]} zoom={6} className="h-full min-h-[360px] w-full rounded border border-line" scrollWheelZoom={false}>
      <TileLayer attribution={DARK_BASEMAP.attribution} url={DARK_BASEMAP.url} />
      {points.map((p) => (
        <CircleMarker key={p.id} center={[p.lat, p.lng]} radius={9} pathOptions={{ color: colors[p.kind] ?? "#94a3b8" }}>
          <Popup>
            <strong>{p.name}</strong>
            <br />
            {p.kind}
            {p.severity ? ` · ${p.severity}` : ""}
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
