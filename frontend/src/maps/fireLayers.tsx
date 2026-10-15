import type { FitBoundsOptions } from "leaflet";
import { Fragment, useEffect } from "react";
import { Circle, CircleMarker, Tooltip, useMap } from "react-leaflet";
import type { FireCluster, FireDetectionRecord, MonitoredSite } from "../api/types";
import { SITE_COLOR, type LatLngBounds } from "../lib/fire";
import { fmt, fmtDateTime } from "../lib/format";

/**
 * Animate the map to `bounds` whenever `targetKey` changes (e.g. a newly selected event), keeping the
 * target clear of the details panel overlaid at the bottom-left of the map.
 */
export function FlyTo({ targetKey, bounds, panel = true, maxZoom = 12 }: { targetKey: string | null; bounds: LatLngBounds | null; panel?: boolean; maxZoom?: number }) {
  const map = useMap();
  useEffect(() => {
    if (!targetKey || !bounds) return;
    const size = map.getSize();
    const pad: Pick<FitBoundsOptions, "paddingTopLeft" | "paddingBottomRight"> = !panel
      ? { paddingTopLeft: [40, 40], paddingBottomRight: [40, 40] }
      : size.x >= 760
        ? { paddingTopLeft: [400, 40], paddingBottomRight: [40, 40] }
        : { paddingTopLeft: [30, 30], paddingBottomRight: [30, Math.round(size.y * 0.55)] };
    map.flyToBounds(bounds, { ...pad, maxZoom, duration: 0.9 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, targetKey]);
  return null;
}

function DetectionTooltip({ d, extra }: { d: FireDetectionRecord; extra?: string }) {
  return (
    <Tooltip>
      <strong>{d.sensor}</strong> · {fmtDateTime(d.acquired_at)} {d.daynight === "N" ? "(night)" : d.daynight === "D" ? "(day)" : ""}
      <br />
      FRP {fmt(d.frp_mw, 1)} MW · confidence {d.confidence}
      {extra ? (
        <>
          <br />
          {extra}
        </>
      ) : null}
    </Tooltip>
  );
}

export function SelectedClusterLayer({ cluster }: { cluster: FireCluster }) {
  const members = cluster.members ?? cluster.points.map(([lon, lat]) => ({ latitude: lat, longitude: lon, acquired_at: cluster.last_seen, sensor: "", confidence: "", frp_mw: null }));
  return (
    <>
      {members.map((d, i) => (
        <CircleMarker
          key={`${d.latitude}-${d.longitude}-${d.acquired_at}-${i}`}
          center={[d.latitude, d.longitude]}
          radius={6}
          pathOptions={{ color: "#fde047", weight: 2, fillColor: "#fde047", fillOpacity: 0.85 }}
        >
          <DetectionTooltip d={d} />
        </CircleMarker>
      ))}
    </>
  );
}

export function SiteMarkers({ sites, selectedId, onSelect }: { sites: MonitoredSite[]; selectedId?: string | null; onSelect: (s: MonitoredSite) => void }) {
  return (
    <>
      {sites.map((s) => {
        const selected = s.id === selectedId;
        const hit = s.status !== "NO_DETECTION";
        return (
          <Fragment key={s.id}>
            {selected ? <Circle center={[s.latitude, s.longitude]} radius={s.radius_km * 1000} pathOptions={{ color: SITE_COLOR, weight: 2, dashArray: "6 4", fillOpacity: 0.05 }} interactive={false} /> : null}
            <CircleMarker center={[s.latitude, s.longitude]} radius={selected ? 11 : 9} pathOptions={{ color: SITE_COLOR, weight: selected ? 4 : 3, fillColor: "#0b1016", fillOpacity: 0.9 }} eventHandlers={{ click: () => onSelect(s) }}>
              <Tooltip>
                <strong>{s.name}</strong>
                <br />
                {s.kind}
                <br />
                FIRMS within {s.radius_km} km: {Object.entries(s.counts).map(([w, n]) => `${w} ${n}`).join(" · ")}
              </Tooltip>
            </CircleMarker>
            <CircleMarker
              center={[s.latitude, s.longitude]}
              radius={3.5}
              pathOptions={{ color: hit ? "#f97316" : SITE_COLOR, weight: 0, fillColor: hit ? "#f97316" : SITE_COLOR, fillOpacity: 1 }}
              eventHandlers={{ click: () => onSelect(s) }}
            />
            {selected
              ? s.history.map((d, i) => (
                  <CircleMarker key={`${s.id}-${i}`} center={[d.latitude, d.longitude]} radius={5} pathOptions={{ color: "#fde047", weight: 2, fillColor: "#f97316", fillOpacity: 0.9 }}>
                    <DetectionTooltip d={d} extra={`${fmt(d.distance_km, 2)} km from site · nearest: ${d.nearest_facility}`} />
                  </CircleMarker>
                ))
              : null}
          </Fragment>
        );
      })}
    </>
  );
}
