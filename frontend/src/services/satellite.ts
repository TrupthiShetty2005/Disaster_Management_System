import type { ListResponse, SatelliteAnalysis, SatelliteImageItem } from "../types/api";
import { apiBase, apiGet, apiPost, isMockMode } from "./apiClient";

const mockImages: SatelliteImageItem[] = [
  {
    id: "sat-flood-before-001",
    title: "Kuttanad pre-event (demo)",
    source: "mock-landsat",
    acquisition_time: "2026-07-04T06:00:00Z",
    latitude: 9.517,
    longitude: 76.522,
    bounding_box: {
      type: "Polygon",
      coordinates: [[[76.49, 9.48], [76.56, 9.48], [76.56, 9.55], [76.49, 9.55], [76.49, 9.48]]],
    },
    resolution: "10m",
    cloud_cover: 11,
    image_url: "/api/v1/satellite/images/sat-flood-before-001/preview",
    thumbnail_url: "/api/v1/satellite/images/sat-flood-before-001/preview",
    status: "ready",
    provider: "mock-landsat",
    location_id: "11111111-1111-4111-8111-111111111111",
  },
  {
    id: "sat-flood-after-001",
    title: "Kuttanad flood event (demo)",
    source: "mock-sentinel2",
    acquisition_time: "2026-07-14T00:00:00Z",
    latitude: 9.517,
    longitude: 76.522,
    bounding_box: {
      type: "Polygon",
      coordinates: [[[76.49, 9.48], [76.56, 9.48], [76.56, 9.55], [76.49, 9.55], [76.49, 9.48]]],
    },
    resolution: "10m",
    cloud_cover: 9.4,
    image_url: "/api/v1/satellite/images/sat-flood-after-001/preview",
    thumbnail_url: "/api/v1/satellite/images/sat-flood-after-001/preview",
    status: "ready",
    provider: "mock-sentinel2",
    location_id: "11111111-1111-4111-8111-111111111111",
  },
  {
    id: "sat-burn-001",
    title: "Burn scar demo",
    source: "mock-sentinel2",
    acquisition_time: "2026-07-10T06:00:00Z",
    latitude: 9.58,
    longitude: 76.9,
    bounding_box: {
      type: "Polygon",
      coordinates: [[[76.86, 9.54], [76.94, 9.54], [76.94, 9.62], [76.86, 9.62], [76.86, 9.54]]],
    },
    resolution: "10m",
    cloud_cover: 4.1,
    image_url: "/api/v1/satellite/images/sat-burn-001/preview",
    thumbnail_url: "/api/v1/satellite/images/sat-burn-001/preview",
    status: "ready",
    provider: "mock-sentinel2",
    location_id: "11111111-1111-4111-8111-111111111111",
  },
];

const mockAnalysis: SatelliteAnalysis = {
  id: "an-demo",
  satellite_image_id: "sat-flood-after-001",
  model_name: "baseline-demo-cv-v0",
  analysis_type: "flood",
  summary: "Prototype flood segmentation on synthetic raster.",
  confidence: 0.62,
  result_geojson: {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: {
          type: "Polygon",
          coordinates: [[[76.50, 9.50], [76.54, 9.50], [76.54, 9.53], [76.50, 9.53], [76.50, 9.50]]],
        },
        properties: { name: "flood" },
      },
    ],
  },
  metrics: { flooded_area_km2: 34.5, percent_affected: 38, estimated_population_affected: 42000 },
  created_at: "2026-07-14T06:00:00Z",
  estimate_label: "Prototype satellite analysis",
};

export const SATELLITE_MIN_START = "2026-05-01";

export async function fetchSatelliteImages(opts?: {
  start?: string;
  end?: string;
  maxCloud?: number;
}): Promise<ListResponse<SatelliteImageItem>> {
  const start = opts?.start ?? SATELLITE_MIN_START;
  const end = opts?.end ?? new Date().toISOString().slice(0, 10);
  if (isMockMode()) {
    const items = mockImages.filter((i) => {
      const d = i.acquisition_time.slice(0, 10);
      return d >= start && d <= end;
    });
    return { items, total: items.length, query: { start, end, live_stream: false } };
  }
  const params = new URLSearchParams({ start, end });
  if (opts?.maxCloud != null) params.set("max_cloud", String(opts.maxCloud));
  return apiGet(`/api/v1/satellite/images?${params.toString()}`);
}

export async function analyzeSatellite(imageId: string, analysisType = "flood"): Promise<SatelliteAnalysis> {
  if (isMockMode()) return { ...mockAnalysis, satellite_image_id: imageId, analysis_type: analysisType };
  return apiPost("/api/v1/satellite/analyze", { image_id: imageId, analysis_type: analysisType });
}

export async function compareSatellite(before: string, after: string): Promise<SatelliteAnalysis> {
  if (isMockMode()) {
    return {
      ...mockAnalysis,
      analysis_type: "comparison",
      metrics: {
        changed_area_fraction: 0.21,
        flood_expansion_fraction: 0.18,
        vegetation_loss_fraction: 0.07,
        urban_change_fraction: 0.02,
        before_image: before,
        after_image: after,
      },
    };
  }
  return apiPost("/api/v1/satellite/compare", { before_image: before, after_image: after });
}

export async function fetchSatelliteSummary(): Promise<{ note: string }> {
  if (isMockMode()) {
    return { note: "Demo Mode: synthetic Sentinel/Landsat stand-ins. No live EO credentials required." };
  }
  return {
    note: "Real Data Mode: Copernicus STAC archive for the selected Karnataka AOI from 1 May 2026. Acquisition dates are not real-time. Only genuine STAC previews are shown.",
  };
}

export function hasGenuinePreview(image: SatelliteImageItem): boolean {
  const meta = image.metadata || {};
  if (meta.preview_available === false) return false;
  if (image.status === "catalogue_only") return false;
  return Boolean(image.image_url);
}

export function previewSrc(image: SatelliteImageItem): string {
  if (!hasGenuinePreview(image)) return "";
  const base = apiBase();
  if (image.image_url.startsWith("http")) return image.image_url;
  return `${base}${image.image_url}`;
}

export function sceneIntersectsSelectedAoi(item: SatelliteImageItem): boolean {
  const meta = item.metadata || {};
  if (meta.intersects_selected_aoi === false) return false;
  if (meta.footprint_available === false) return false;
  return true;
}

/** Oldest intersecting scene = before, newest = after. Never uses id/title “before”/“after”. */
export function pickBeforeAfter(items: SatelliteImageItem[]): {
  before?: SatelliteImageItem;
  after?: SatelliteImageItem;
} {
  const pool = items.filter(sceneIntersectsSelectedAoi);
  const dated = [...pool].sort((a, b) => {
    const ta = Date.parse(String(a.acquisition_time || 0));
    const tb = Date.parse(String(b.acquisition_time || 0));
    return ta - tb;
  });
  if (dated.length < 2) return { before: dated[0], after: dated[1] };
  return { before: dated[0], after: dated[dated.length - 1] };
}
