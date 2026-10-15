import type { FloodEvent, ListResponse } from "../types/api";
import { apiGet, apiPost, isMockMode } from "./apiClient";

const mockEvent: FloodEvent = {
  id: "flood-demo-1",
  model_name: "demo-flood-seg-v0",
  scene_kind: "flood",
  flooded_area: 34.5,
  flood_percentage: 38,
  severity: "high",
  confidence: 0.58,
  boundary_geojson: {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: {
          type: "Polygon",
          coordinates: [[[76.5, 9.5], [76.54, 9.5], [76.54, 9.53], [76.5, 9.53], [76.5, 9.5]]],
        },
        properties: { name: "flood boundary" },
      },
    ],
  },
  heatmap_geojson: {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: {
          type: "Polygon",
          coordinates: [[[76.5, 9.5], [76.53, 9.5], [76.53, 9.52], [76.5, 9.52], [76.5, 9.5]]],
        },
        properties: { name: "flood heatmap", intensity: 0.7 },
      },
    ],
  },
  affected_population: 42000,
  affected_roads: 3,
  affected_buildings: 18,
  notes: "OpenCV/NumPy water-pixel heuristic. This is not a trained semantic segmentation model.",
  created_at: "2026-07-14T06:00:00Z",
  estimate_label: "Prototype flood extent",
};

export async function analyzeFlood(sceneKind = "flood"): Promise<FloodEvent> {
  if (isMockMode()) {
    return {
      ...mockEvent,
      scene_kind: sceneKind,
      estimate_label: "Prototype flood extent (OpenCV/NumPy demo, not a trained U-Net/DeepLab)",
    };
  }
  return apiPost("/api/v1/flood/analyze", { scene_kind: sceneKind });
}

export async function fetchFloodEvents(): Promise<ListResponse<FloodEvent>> {
  if (isMockMode()) {
    return {
      items: [
        {
          ...mockEvent,
          estimate_label: "Prototype flood extent (OpenCV/NumPy demo, not a trained U-Net/DeepLab)",
        },
      ],
      total: 1,
    };
  }
  // Real Data Mode: never fall back to hard-coded demo 34.5 km² / synthetic extents.
  return apiGet("/api/v1/flood/events");
}

export { fetchFloodSummary } from "./intel";
