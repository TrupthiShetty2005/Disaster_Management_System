import type { AlertItem, FloodEvent, SatelliteImageItem } from "../types/api";
import type { GisCollection, GisFeature, GisGeometry } from "../types/gis";
import { catalogFromOverpass, emptyCatalog } from "../services/gis";
import { alertBucket } from "./alertBuckets";

const KERALA_LAT = 9.517;
const KERALA_LON = 76.522;

export function isKeralaDemoCoordinate(lat: number, lon: number): boolean {
  return Math.abs(lat - KERALA_LAT) < 0.02 && Math.abs(lon - KERALA_LON) < 0.02;
}

export function isPlottableAlertCoordinate(
  lat: number | null | undefined,
  lon: number | null | undefined,
  allowKeralaDemo: boolean,
): boolean {
  if (lat == null || lon == null) return false;
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return false;
  if (Math.abs(lat) > 90 || Math.abs(lon) > 180) return false;
  if (!allowKeralaDemo && isKeralaDemoCoordinate(lat, lon)) return false;
  return true;
}

export function bboxToPolygon(bbox: number[] | undefined | null): GeoJSON.Polygon | null {
  if (!bbox || bbox.length !== 4) return null;
  const [west, south, east, north] = bbox.map(Number);
  if (![west, south, east, north].every((n) => Number.isFinite(n))) return null;
  return {
    type: "Polygon",
    coordinates: [
      [
        [west, south],
        [east, south],
        [east, north],
        [west, north],
        [west, south],
      ],
    ],
  };
}

function asFeatureCollection(geo: unknown): GeoJSON.Feature[] {
  if (!geo || typeof geo !== "object") return [];
  const g = geo as { type?: string; features?: unknown[]; geometry?: unknown; coordinates?: unknown };
  if (g.type === "FeatureCollection" && Array.isArray(g.features)) {
    return g.features.filter((f) => f && typeof f === "object") as GeoJSON.Feature[];
  }
  if (g.type === "Feature") return [g as GeoJSON.Feature];
  if (g.type === "Polygon" || g.type === "MultiPolygon" || g.type === "LineString") {
    return [{ type: "Feature", properties: {}, geometry: g as GeoJSON.Geometry }];
  }
  return [];
}

export function floodOverlayFeatures(event: FloodEvent | undefined): GisFeature[] {
  if (!event) return [];
  const raw = event.newly_flooded_geojson || event.boundary_geojson || event.after_water_geojson;
  return asFeatureCollection(raw).map((f, i) => ({
    type: "Feature" as const,
    geometry: f.geometry as GisGeometry,
    properties: {
      id: `flood-${event.id}-${i}`,
      name: "Newly water-covered (Sentinel heuristic)",
      layer: "floodCurrent" as const,
      description: event.estimate_label || "Satellite-derived water-change — requires validation",
      clickAction: "open-flood" as const,
      source: event.model_name,
    },
  })).filter((f) => f.geometry);
}

export function alertPinFeatures(items: AlertItem[], allowKeralaDemo: boolean): GisFeature[] {
  const out: GisFeature[] = [];
  for (const a of items) {
    if (!isPlottableAlertCoordinate(a.latitude, a.longitude, allowKeralaDemo)) continue;
    const bucket = alertBucket(a);
    out.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: [a.longitude as number, a.latitude as number] },
      properties: {
        id: `alert-${a.id}`,
        name: a.title,
        layer: "alerts",
        severity: a.severity,
        officialWarning: bucket === "official",
        alertId: a.id,
        clickAction: "open-alert",
        description:
          bucket === "official"
            ? "Official warning"
            : bucket === "heuristic"
              ? "Heuristic risk estimate — not an official warning"
              : "Historical / persisted alert",
        source: a.source,
      },
    });
  }
  return out;
}

export function hospitalClickFeatures(features: GisFeature[]): GisFeature[] {
  return features.map((f) => ({
    ...f,
    properties: {
      ...f.properties,
      clickAction: f.properties.layer === "hospitals" ? "copy-coords" : f.properties.clickAction,
    },
  }));
}

export function mergeDashboardCatalog(args: {
  osmFeatures?: GisFeature[];
  flood?: FloodEvent;
  alerts?: AlertItem[];
  allowKeralaDemo: boolean;
}): Record<string, GisCollection> {
  const base = args.osmFeatures?.length ? catalogFromOverpass(args.osmFeatures) : emptyCatalog();
  base.hospitals.features = hospitalClickFeatures(base.hospitals.features);
  base.floodCurrent = { type: "FeatureCollection", features: floodOverlayFeatures(args.flood) };
  base.alerts = { type: "FeatureCollection", features: alertPinFeatures(args.alerts ?? [], args.allowKeralaDemo) };
  return base;
}

export function layerCountLegend(catalog: Record<string, GisCollection>): string {
  const parts = ["alerts", "floodCurrent", "roads", "hospitals", "shelters", "buildings", "railways", "waterways"]
    .map((id) => {
      const n = catalog[id]?.features?.length ?? 0;
      if (!n) return null;
      return `${id === "floodCurrent" ? "flood" : id} ${n}`;
    })
    .filter(Boolean);
  return parts.join(" · ") || "No vector layers loaded";
}

export function aoiBoundary(
  boundary: GeoJSON.GeoJsonObject | null | undefined,
  bbox: number[] | undefined,
): GeoJSON.GeoJsonObject | null {
  return boundary || bboxToPolygon(bbox);
}

export function satelliteFootprint(scene: SatelliteImageItem | undefined): GeoJSON.GeoJsonObject | null {
  const box = scene?.bounding_box;
  if (!box || typeof box !== "object") return null;
  const g = box as { type?: string };
  if (g.type === "Polygon" || g.type === "MultiPolygon" || g.type === "Feature" || g.type === "FeatureCollection") {
    return box as unknown as GeoJSON.GeoJsonObject;
  }
  return null;
}

export function featureLatLon(feature: GisFeature): { lat: number; lon: number } | null {
  const g = feature.geometry;
  if (g.type === "Point") return { lon: g.coordinates[0], lat: g.coordinates[1] };
  if (g.type === "LineString") return { lon: g.coordinates[0][0], lat: g.coordinates[0][1] };
  if (g.type === "Polygon") return { lon: g.coordinates[0][0][0], lat: g.coordinates[0][0][1] };
  return null;
}
