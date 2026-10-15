import { allGisFeatures, gisCatalog } from "../data/gisMock";
import type { GisCollection, GisFeature, LayerId } from "../types/gis";
import { apiGet, isMockMode } from "./apiClient";

export type GisLayerStatus = "mapped" | "not_mapped_in_osm_for_this_query";

export type GisApiResponse = {
  type: "FeatureCollection";
  features: GisFeature[];
  total: number;
  cache_hit?: boolean;
  cache_age_sec?: number;
  freshness?: string;
  empty_result?: boolean;
  skipped_invalid_geometry?: number;
  layer_counts?: Record<string, number>;
  layer_status?: Record<string, GisLayerStatus | string>;
  data_provenance?: {
    status: string;
    provider: string;
    description: string;
    retrieved_at?: string;
    limitations?: string;
    official_government_data?: boolean;
    aoi_name?: string;
    license?: string;
  };
};

const OSM_LAYER_TO_CATALOG: Record<string, LayerId> = {
  roads: "roads",
  bridges: "roads",
  railways: "railways",
  waterways: "waterways",
  buildings: "buildings",
  hospitals: "hospitals",
  community: "shelters",
  shelters: "shelters",
  amenities: "hospitals",
};

export function emptyCatalog(): Record<string, GisCollection> {
  return {
    disasters: { type: "FeatureCollection", features: [] },
    alerts: { type: "FeatureCollection", features: [] },
    floodCurrent: { type: "FeatureCollection", features: [] },
    floodPredicted: { type: "FeatureCollection", features: [] },
    risk: { type: "FeatureCollection", features: [] },
    population: { type: "FeatureCollection", features: [] },
    roads: { type: "FeatureCollection", features: [] },
    railways: { type: "FeatureCollection", features: [] },
    waterways: { type: "FeatureCollection", features: [] },
    buildings: { type: "FeatureCollection", features: [] },
    evacuation: { type: "FeatureCollection", features: [] },
    rescue: { type: "FeatureCollection", features: [] },
    hospitals: { type: "FeatureCollection", features: [] },
    shelters: { type: "FeatureCollection", features: [] },
  };
}

export function catalogFromOverpass(features: GisFeature[]): Record<string, GisCollection> {
  const catalog = emptyCatalog();
  for (const raw of features) {
    const src = String(raw.properties?.layer || raw.properties?.feature_type || "amenities");
    const layer = OSM_LAYER_TO_CATALOG[src] ?? null;
    if (!layer) continue;
    const feature: GisFeature = {
      ...raw,
      properties: {
        ...raw.properties,
        layer,
        description:
          raw.properties?.description ||
          "OpenStreetMap volunteer mapping (ODbL). Not official government infrastructure.",
      },
    };
    catalog[layer].features.push(feature);
  }
  return catalog;
}

export async function fetchGisCatalog(): Promise<Record<string, GisCollection>> {
  if (isMockMode()) return gisCatalog;
  const body = await apiGet<GisApiResponse>("/api/v1/gis/features");
  return catalogFromOverpass(body.features || []);
}

export async function fetchGisFeatures(): Promise<GisFeature[]> {
  if (isMockMode()) return allGisFeatures();
  const body = await apiGet<GisApiResponse>("/api/v1/gis/features");
  return body.features || [];
}

export async function fetchGisWithProvenance(): Promise<GisApiResponse> {
  if (isMockMode()) {
    return {
      type: "FeatureCollection",
      features: allGisFeatures(),
      total: allGisFeatures().length,
      data_provenance: {
        status: "MOCK",
        provider: "frontend gisMock (Demo Mode only)",
        description: "Demo Mode static GIS. Not used on the live operational map.",
        official_government_data: false,
      },
    };
  }
  return apiGet<GisApiResponse>("/api/v1/gis/features");
}

export const dashboardKpis = {
  floodedKm2: 0,
  damagedBuildings: 0,
  availableRescueUnits: 0,
};
