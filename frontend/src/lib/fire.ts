import type { FireCluster, MonitoredSite } from "../api/types";

export type LatLngBounds = [[number, number], [number, number]];

export const INDUSTRIAL_COLOR = "#a78bfa";
export const SITE_COLOR = "#34d399";

/** Map bounds around a fire event's detections, padded so single-pixel events are not over-zoomed. */
export function clusterBounds(c: Pick<FireCluster, "bbox">, padDeg = 0.02): LatLngBounds {
  const [w, s, e, n] = c.bbox;
  return [
    [s - padDeg, w - padDeg],
    [n + padDeg, e + padDeg],
  ];
}

/** Map bounds covering a site's search radius. */
export function siteBounds(s: Pick<MonitoredSite, "latitude" | "longitude" | "radius_km">): LatLngBounds {
  const dLat = (s.radius_km * 1.3) / 110.57;
  const dLon = (s.radius_km * 1.3) / (111.32 * Math.cos((s.latitude * Math.PI) / 180));
  return [
    [s.latitude - dLat, s.longitude - dLon],
    [s.latitude + dLat, s.longitude + dLon],
  ];
}

export const SITE_STATUS_TEXT: Record<MonitoredSite["status"], string> = {
  DETECTED_24H: "Detected in last 24 h",
  DETECTED: "Detected in window",
  NO_DETECTION: "No satellite detection",
};
