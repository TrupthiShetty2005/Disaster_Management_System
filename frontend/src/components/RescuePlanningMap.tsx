import { GeoJSON as LeafletGeoJSON, MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import { DARK_BASEMAP } from "../maps/basemap";
import type { GeoJsonObject } from "geojson";
import "leaflet/dist/leaflet.css";
import type { RescuePlan, RescueResource, EvacuationCenter, GeoJSON as GeoValue } from "../types/api";

function point(geo: GeoValue | undefined): [number, number] | null {
  if (!geo || typeof geo !== "object") return null;
  if ("type" in geo && geo.type === "Point" && "coordinates" in geo) {
    const c = (geo as { coordinates: [number, number] }).coordinates;
    return [c[1], c[0]];
  }
  return null;
}

export function RescuePlanningMap({
  plan,
  resources,
  shelters,
}: {
  plan: RescuePlan | null;
  resources: RescueResource[];
  shelters: EvacuationCenter[];
}) {
  const blocked = plan?.plan.routes.blocked_roads ?? null;
  const evac = plan?.plan.evacuation_route.geojson ?? null;
  const access = plan?.plan.routes.primary_access?.geojson ?? null;
  const hospital = plan?.plan.map.hospital;
  const incident = plan?.plan.map.incident;

  return (
    <MapContainer center={[12.9716, 77.5946]} zoom={12} className="h-full min-h-[360px] w-full rounded border border-line" scrollWheelZoom={false}>
      <TileLayer attribution={DARK_BASEMAP.attribution} url={DARK_BASEMAP.url} />
      {blocked ? <LeafletGeoJSON data={blocked as unknown as GeoJsonObject} style={{ color: "#ef4444", weight: 3, dashArray: "6 4" }} /> : null}
      {access ? <LeafletGeoJSON data={access as unknown as GeoJsonObject} style={{ color: "#38bdf8", weight: 3 }} /> : null}
      {evac ? <LeafletGeoJSON data={evac as unknown as GeoJsonObject} style={{ color: "#34d399", weight: 3 }} /> : null}
      {incident ? (
        <CircleMarker center={[incident.coordinates[1], incident.coordinates[0]]} radius={10} pathOptions={{ color: "#f59e0b" }}>
          <Popup>Incident</Popup>
        </CircleMarker>
      ) : null}
      {hospital ? (
        <CircleMarker center={[hospital.coordinates[1], hospital.coordinates[0]]} radius={8} pathOptions={{ color: "#f472b6" }}>
          <Popup>Hospital (demo)</Popup>
        </CircleMarker>
      ) : null}
      {shelters.map((s) => {
        const c = point(s.geojson);
        if (!c) return null;
        return (
          <CircleMarker key={s.id} center={c} radius={8} pathOptions={{ color: "#34d399" }}>
            <Popup>
              Shelter: {s.name} ({s.occupied}/{s.capacity})
            </Popup>
          </CircleMarker>
        );
      })}
      {resources.map((r) => {
        const c = point(r.geojson) ?? (r.latitude != null && r.longitude != null ? [r.latitude, r.longitude] : null);
        if (!c) return null;
        return (
          <CircleMarker key={r.id} center={c} radius={7} pathOptions={{ color: "#fbbf24" }}>
            <Popup>
              {r.name} · {r.resource_type} · {r.status}
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
