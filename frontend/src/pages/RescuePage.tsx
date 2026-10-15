import { useEffect, useState } from "react";
import { CircleMarker, GeoJSON, Tooltip, useMapEvents } from "react-leaflet";
import { useSearchParams } from "react-router-dom";
import { getAlerts, getRescuePlan } from "../api/endpoints";
import type { RescuePlan } from "../api/types";
import { Card, Empty, ErrorBox, Loading, PageHeader, Source } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { fmt, label } from "../lib/format";
import { KarnatakaMap } from "../maps/KarnatakaMap";

const KIND_COLOR: Record<string, string> = { hospital: "#34d399", fire_station: "#f97316", police: "#38bdf8" };

function ClickToTarget({ onPick }: { onPick: (lat: number, lon: number) => void }) {
  useMapEvents({ click: (e) => onPick(Number(e.latlng.lat.toFixed(5)), Number(e.latlng.lng.toFixed(5))) });
  return null;
}

export default function RescuePage() {
  const [params, setParams] = useSearchParams();
  const lat = params.get("lat") ? Number(params.get("lat")) : null;
  const lon = params.get("lon") ? Number(params.get("lon")) : null;
  const alerts = useAsync(() => getAlerts("open"), []);
  const [plan, setPlan] = useState<{ loading: boolean; data?: RescuePlan; error?: string }>({ loading: false });

  useEffect(() => {
    if (lat === null || lon === null) return;
    setPlan({ loading: true });
    getRescuePlan(lat, lon)
      .then((data) => setPlan({ loading: false, data }))
      .catch((e: Error) => setPlan({ loading: false, error: e.message }));
  }, [lat, lon]);

  const pick = (la: number, lo: number, alert?: string) => setParams(alert ? { lat: String(la), lon: String(lo), alert } : { lat: String(la), lon: String(lo) });
  const located = alerts.data?.items.filter((a) => a.latitude !== null) ?? [];

  return (
    <div className="space-y-3">
      <PageHeader
        title="Rescue planning"
        subtitle="Pick an active alert or click anywhere in Karnataka. The nearest real hospitals, fire stations and police stations from OpenStreetMap are ranked by drive time on the actual road network (OSRM)."
      />
      <div className="grid gap-3 xl:grid-cols-[1fr_400px]">
        <Card title="Response map" actions={<span className="text-[11px] text-slate-500">click the map to set an incident location</span>}>
          <KarnatakaMap height={560} center={lat !== null && lon !== null ? [lat, lon] : undefined} zoom={lat !== null ? 10 : 7} key={lat !== null ? `${lat},${lon}` : "ka"}>
            <ClickToTarget onPick={(la, lo) => pick(la, lo)} />
            {located.map((a) => (
              <CircleMarker key={a.id} center={[a.latitude!, a.longitude!]} radius={6} pathOptions={{ color: "#facc15", fillOpacity: 0.5 }} eventHandlers={{ click: () => pick(a.latitude!, a.longitude!, a.id) }}>
                <Tooltip>{a.title}</Tooltip>
              </CircleMarker>
            ))}
            {plan.data?.responders.map((r) =>
              r.route ? <GeoJSON key={`${r.osm_id}-route`} data={r.route.geometry} style={{ color: KIND_COLOR[r.kind], weight: 3, opacity: 0.8 }} /> : null,
            )}
            {plan.data?.responders.map((r) => (
              <CircleMarker key={r.osm_id} center={[r.latitude, r.longitude]} radius={7} pathOptions={{ color: "#0b1016", weight: 2, fillColor: KIND_COLOR[r.kind], fillOpacity: 1 }}>
                <Tooltip>
                  {r.name} · {r.route ? `${fmt(r.route.duration_min)} min` : "no route"}
                </Tooltip>
              </CircleMarker>
            ))}
            {lat !== null && lon !== null ? <CircleMarker center={[lat, lon]} radius={10} pathOptions={{ color: "#ef4444", weight: 3, fillOpacity: 0.3 }} /> : null}
          </KarnatakaMap>
        </Card>
        <div className="space-y-3">
          <Card title="Active alerts with a location">
            {located.length ? (
              <ul className="max-h-56 space-y-1 overflow-auto text-xs">
                {located.map((a) => (
                  <li key={a.id}>
                    <button className={`w-full rounded border px-2 py-1 text-left hover:bg-white/5 ${params.get("alert") === a.id ? "border-amber-500/60" : "border-line"}`} onClick={() => pick(a.latitude!, a.longitude!, a.id)}>
                      {a.title}
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <Empty>No located alerts open. Click the map to plan for any location.</Empty>
            )}
          </Card>
          <Card title="Nearest responders">
            {lat === null ? <Empty>Select an alert or click the map.</Empty> : null}
            {plan.loading ? <Loading text="Finding facilities and routing on OpenStreetMap roads…" /> : null}
            {plan.error ? <ErrorBox message={plan.error} /> : null}
            {plan.data ? (
              <>
                <ul className="space-y-2 text-sm">
                  {plan.data.responders.map((r) => (
                    <li key={r.osm_id} className="border-l-2 pl-2" style={{ borderColor: KIND_COLOR[r.kind] }}>
                      <p className="text-slate-200">{r.name}</p>
                      <p className="text-[11px] text-slate-400">
                        {label(r.kind)} · {r.route ? `${fmt(r.route.duration_min)} min drive · ${fmt(r.route.distance_km, 1)} km by road` : `route unavailable (${r.route_error ?? "OSRM"})`} · {fmt(r.straight_km, 1)} km straight
                        {r.phone ? ` · ☎ ${r.phone}` : ""}
                      </p>
                    </li>
                  ))}
                </ul>
                <p className="mt-2 text-[11px] text-slate-500">
                  Mapped within 60 km: {Object.entries(plan.data.facilities_found).map(([k, v]) => `${v} ${label(k).toLowerCase()}s`).join(", ")}.
                </p>
                <Source>
                  {plan.data.sources.facilities}; {plan.data.sources.routing}. {plan.data.note}
                </Source>
              </>
            ) : null}
          </Card>
        </div>
      </div>
    </div>
  );
}
