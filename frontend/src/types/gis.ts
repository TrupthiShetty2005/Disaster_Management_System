export type LayerId =
  | "satellite"
  | "disasters"
  | "alerts"
  | "floodCurrent"
  | "floodPredicted"
  | "risk"
  | "population"
  | "roads"
  | "railways"
  | "waterways"
  | "buildings"
  | "evacuation"
  | "rescue"
  | "hospitals"
  | "shelters";

export type GisGeometry =
  | { type: "Point"; coordinates: [number, number] }
  | { type: "LineString"; coordinates: [number, number][] }
  | { type: "Polygon"; coordinates: [number, number][][] };

export interface GisProperties {
  id: string;
  name: string;
  layer: LayerId;
  kind?: string;
  severity?: string;
  riskLevel?: "low" | "moderate" | "high" | "critical";
  riskScore?: number;
  probability?: number;
  affectedPopulation?: number;
  rainfallMm?: number;
  waterLevelM?: number;
  evacuationRecommendation?: string;
  status?: string;
  density?: number;
  description?: string;
  osm_id?: number | string;
  osm_type?: string;
  source?: string;
  retrieved_at?: string;
  feature_type?: string;
  tags?: Record<string, string>;
  clickAction?: "copy-coords" | "open-flood" | "open-alert";
  alertId?: string;
  officialWarning?: boolean;
}

export interface GisFeature {
  type: "Feature";
  geometry: GisGeometry;
  properties: GisProperties;
}

export interface GisCollection {
  type: "FeatureCollection";
  features: GisFeature[];
}

export type LayerVisibility = Record<LayerId, boolean>;

export const DEFAULT_LAYER_VISIBILITY: LayerVisibility = {
  satellite: false,
  disasters: true,
  alerts: true,
  floodCurrent: true,
  floodPredicted: false,
  risk: true,
  population: false,
  roads: true,
  railways: true,
  waterways: true,
  buildings: false,
  evacuation: false,
  rescue: false,
  hospitals: true,
  shelters: true,
};

export const INVENTORY_LAYER_IDS: LayerId[] = ["evacuation", "rescue"];

export const LAYER_LABELS: Record<LayerId, string> = {
  satellite: "Esri World Imagery (basemap tiles, not Sentinel)",
  disasters: "Disaster markers",
  alerts: "Alerts",
  floodCurrent: "Current flood",
  floodPredicted: "Predicted flood",
  risk: "Risk zones",
  population: "Population density",
  roads: "OSM roads / bridges",
  railways: "OSM railways",
  waterways: "OSM waterways",
  buildings: "OSM buildings",
  evacuation: "Evacuation centers",
  rescue: "Rescue units",
  hospitals: "OSM hospitals / medical",
  shelters: "OSM shelters (mapped only)",
};

export function inventoryLayerHasFeatures(
  catalog: Record<string, GisCollection> | undefined,
  id: LayerId,
): boolean {
  return (catalog?.[id]?.features?.length ?? 0) > 0;
}

const OSM_LAYER_IDS: LayerId[] = ["roads", "railways", "waterways", "buildings", "hospitals", "shelters"];

/** Hide dead checkboxes (count 0). Satellite basemap is always togglable. */
export function showMapLayerToggle(
  id: LayerId,
  liveMode: boolean,
  featureCount: number,
  osmUnavailable = false,
): boolean {
  if (id === "satellite") return true;
  if (featureCount <= 0) return false;
  if (osmUnavailable && OSM_LAYER_IDS.includes(id)) return false;
  if (liveMode && (id === "evacuation" || id === "rescue" || id === "population" || id === "floodPredicted")) {
    return featureCount > 0;
  }
  return true;
}

export function toggleLayer(current: LayerVisibility, id: LayerId): LayerVisibility {
  return { ...current, [id]: !current[id] };
}

export function searchFeatures(features: GisFeature[], query: string): GisFeature[] {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  return features.filter((f) => f.properties.name.toLowerCase().includes(q)).slice(0, 8);
}
