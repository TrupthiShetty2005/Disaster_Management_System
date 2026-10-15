import type { DamageAssessment, ListResponse } from "../types/api";
import { apiGet, apiPost, isMockMode } from "./apiClient";

const mock: DamageAssessment = {
  id: "dmg-demo-1",
  model_name: "demo-change-v0",
  before_kind: "flood_before",
  after_kind: "flood",
  report: {
    executive_summary: "Prototype change detection on synthetic before/after pair. Not a trained model.",
    affected_area: { flooded_area_km2: 34.5, flood_expansion_fraction: 0.18, estimated_population: 42000 },
    building_statistics: {
      counts: { "NO DAMAGE": 12, MINOR: 4, MODERATE: 6, SEVERE: 5, DESTROYED: 3 },
      damaged_percentage: 60,
      primary: "MODERATE",
    },
    road_statistics: {
      counts: { OPEN: 4, "PARTIALLY BLOCKED": 1, BLOCKED: 3, DESTROYED: 0 },
      destroyed_roads: 0,
      blocked_or_destroyed: 3,
      primary: "BLOCKED",
    },
    flood_statistics: { water_expansion_fraction: 0.18, flooded_area_km2: 34.5 },
    infrastructure_loss: { index: 10, urban_change_fraction: 0.02, crop_destruction_pct: 7 },
    priority_areas: [{ name: "Polder flood expansion", rank: 1, action: "Boat rescue staging" }],
    recommended_actions: ["Boat rescue staging", "Do not treat as official government damage survey"],
    pdf_generation: "not implemented — JSON report only",
  },
  overlay_geojson: {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: {
          type: "Polygon",
          coordinates: [[[76.5, 9.5], [76.54, 9.5], [76.54, 9.53], [76.5, 9.53], [76.5, 9.5]]],
        },
        properties: { name: "flood expansion" },
      },
    ],
  },
  created_at: "2026-07-14T06:00:00Z",
  estimate_label: "Prototype damage assessment",
  pdf_available: false,
};

export async function analyzeDamage(): Promise<DamageAssessment> {
  if (isMockMode()) return mock;
  return apiPost("/api/v1/damage/analyze", { before_kind: "flood_before", after_kind: "flood" });
}

export async function fetchDamageAssessments(): Promise<ListResponse<DamageAssessment>> {
  if (isMockMode()) return { items: [mock], total: 1 };
  return apiGet("/api/v1/damage/assessments");
}

export { fetchDamageSummary } from "./intel";
