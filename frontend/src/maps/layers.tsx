import { CircleMarker, Popup, Tooltip } from "react-leaflet";
import type { DisasterEvent, FireCluster, FireDetection, StationReport } from "../api/types";
import { INDUSTRIAL_COLOR } from "../lib/fire";
import { fmt, fmtDate, fmtDateTime, label, levelColor } from "../lib/format";

export function StationMarkers({ stations, onSelect }: { stations: StationReport[]; onSelect?: (id: string) => void }) {
  return (
    <>
      {stations.map((s) => (
        <CircleMarker
          key={s.id}
          center={[s.latitude, s.longitude]}
          radius={8}
          pathOptions={{ color: "#0b1016", weight: 2, fillColor: levelColor(s.status), fillOpacity: 0.95 }}
          eventHandlers={onSelect ? { click: () => onSelect(s.id) } : undefined}
        >
          <Tooltip>
            <strong>{s.name}</strong> ({s.river})
            <br />
            Now {fmt(s.current?.discharge)} {s.unit} · {label(s.status)}
          </Tooltip>
          {onSelect ? null : (
            <Popup>
              <strong>{s.name}</strong> — {s.river}
              <br />
              Discharge {fmt(s.current?.discharge)} {s.unit} ({fmt(s.percent_of_2yr_flood)}% of 2-yr flood)
              <br />
              Predicted peak {fmt(s.forecast_peak?.expected?.discharge)} on {fmtDate(s.forecast_peak?.expected?.date)}
              <br />
              Status: {label(s.status)}
            </Popup>
          )}
        </CircleMarker>
      ))}
    </>
  );
}

export function DetectionMarkers({ detections }: { detections: FireDetection[] }) {
  return (
    <>
      {detections.map((d, i) => (
        <CircleMarker
          key={`${d.latitude}-${d.longitude}-${i}`}
          center={[d.latitude, d.longitude]}
          radius={Math.min(9, 3 + Math.sqrt(d.frp_mw ?? 1))}
          pathOptions={{ color: "#ef4444", weight: 1, fillColor: "#f97316", fillOpacity: 0.8 }}
        >
          <Popup>
            <strong>{d.sensor}</strong> fire detection
            <br />
            {fmtDateTime(d.acquired_at)} · {d.district}
            <br />
            FRP {fmt(d.frp_mw, 1)} MW · confidence {d.confidence}
          </Popup>
        </CircleMarker>
      ))}
    </>
  );
}

export function ClusterMarkers({ clusters, onSelect, selectedId }: { clusters: FireCluster[]; onSelect?: (c: FireCluster) => void; selectedId?: string | null }) {
  return (
    <>
      {clusters.map((c) => (
        <CircleMarker
          key={c.id}
          center={[c.latitude, c.longitude]}
          radius={Math.min(18, (c.persistent_heat_source ? 8 : 6) + Math.sqrt(c.detections) * 1.5)}
          pathOptions={{
            ...(c.persistent_heat_source
              ? { color: INDUSTRIAL_COLOR, weight: 2.5, fillColor: INDUSTRIAL_COLOR, fillOpacity: 0.5 }
              : { color: levelColor(c.severity), weight: 2, fillColor: levelColor(c.severity), fillOpacity: 0.35 }),
            ...(c.id === selectedId ? { color: "#fde047", weight: 4 } : {}),
          }}
          eventHandlers={onSelect ? { click: () => onSelect(c) } : undefined}
        >
          <Tooltip>
            <strong>{c.classification}</strong> — {c.district}
            <br />
            {c.detections} detections over {c.days_seen} day(s) · {fmt(c.total_frp_mw)} MW total
            <br />
            Last seen {fmtDateTime(c.last_seen)}
            {onSelect ? " · click for details" : ""}
          </Tooltip>
        </CircleMarker>
      ))}
    </>
  );
}

const GDACS_COLOR: Record<string, string> = { Green: "#34d399", Orange: "#f97316", Red: "#ef4444" };

export function EventMarkers({ events }: { events: DisasterEvent[] }) {
  return (
    <>
      {events.map((e) => (
        <CircleMarker key={e.id} center={[e.latitude, e.longitude]} radius={11} pathOptions={{ color: GDACS_COLOR[e.alert_level] ?? "#38bdf8", weight: 3, fillOpacity: 0.1 }}>
          <Popup>
            <strong>{e.name}</strong> ({e.alert_level})
            <br />
            {fmtDate(e.from_date)} – {fmtDate(e.to_date)} {e.is_current ? "· ongoing" : ""}
            <br />
            {e.report_url ? (
              <a href={e.report_url} target="_blank" rel="noreferrer">
                GDACS report
              </a>
            ) : null}
          </Popup>
        </CircleMarker>
      ))}
    </>
  );
}
