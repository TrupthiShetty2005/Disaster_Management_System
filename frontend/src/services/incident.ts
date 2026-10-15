import type { Disaster } from "../types/api";
import { apiGet, isMockMode } from "./apiClient";
import { DEMO_INCIDENT_ID, DEMO_LOCATION_ID, DEMO_REGION } from "../constants/demo";
import { mockDisasters } from "../data/mock";

export interface IncidentPicture {
  incident: Disaster;
  region: string;
  location_id: string;
  narrative: string[];
  weather: { conditions: string; rainfall_mm: number; temperature_c: number };
  risk_zones: { id: string; name: string; risk_level: string; risk_score: number }[];
  flood: { extent_km2: number; water_depth_m: number };
  infrastructure: { name: string; category: string; status: string }[];
  roads: { name: string; accessibility: string }[];
  buildings: { name: string; damage_class: string }[];
  resources: { id: string; name: string; type: string; status: string }[];
  alerts: { id: string; title: string; severity: string; status: string }[];
  priorities: { title: string; level: string | null; score: number | null; people_affected: number }[];
  rescue_plan: { id: string; decision: string } | null;
  audit: { action: string; entity_type: string; details: string; created_at: string | null }[];
  timeline: { t: string; event: string }[];
  links: Record<string, string>;
}

const mockPicture: IncidentPicture = {
  incident: mockDisasters[0],
  region: DEMO_REGION,
  location_id: DEMO_LOCATION_ID,
  narrative: [
    "Severe rainfall over Kuttanad polders (demo weather observation).",
    "Flood risk engine raises a prototype high-risk score for Polder A.",
    "High-risk zone is shown on the GIS command map.",
    "Satellite before/after comparison estimates flood expansion.",
    "Flood detection marks inundated extent and blocked roads.",
    "Damage assessment classifies buildings and road accessibility.",
    "Affected population and rescue priorities are scored.",
    "Resource recommendations (boats, medical, food) are proposed.",
    "Alert engine posts dashboard watches/warnings (not official warnings).",
    "Command dashboard and incident page refresh from the same incident ID.",
  ],
  weather: { conditions: "Heavy rain", rainfall_mm: 48.2, temperature_c: 27.4 },
  risk_zones: [{ id: "r1", name: "Polder A floodplain", risk_level: "high", risk_score: 0.86 }],
  flood: { extent_km2: 34.5, water_depth_m: 1.8 },
  infrastructure: [{ name: "Kuttanad pump house (demo)", category: "waterworks", status: "degraded" }],
  roads: [{ name: "Alappuzha–Changanassery stretch (demo)", accessibility: "blocked" }],
  buildings: [{ name: "Panchayat hall (demo)", damage_class: "minor" }],
  resources: [{ id: "res1", name: "Boat unit Delta (demo)", type: "RESCUE_BOAT", status: "DEPLOYED" }],
  alerts: [{ id: "a2", title: "Road closure — NH demo segment", severity: "CRITICAL", status: "ACTIVE" }],
  priorities: [{ title: "Isolate polder hamlet cluster", level: "HIGH", score: 72, people_affected: 1200 }],
  rescue_plan: null,
  audit: [],
  timeline: [
    { t: "2026-07-12T06:00:00", event: "Severe rainfall over Kuttanad polders (demo weather observation)." },
  ],
  links: {
    flood_map: "/flood-detection",
    damage_report: "/damage-assessment",
    risk: "/risk-intelligence",
    rescue: "/rescue-planning",
    satellite_compare: "/satellite/compare",
    alerts: "/alerts",
    analytics: "/analytics",
    vision: "/computer-vision",
  },
};

export async function fetchIncidentPicture(id: string = DEMO_INCIDENT_ID): Promise<IncidentPicture> {
  if (isMockMode()) return { ...mockPicture, incident: { ...mockPicture.incident, id } };
  return apiGet(`/api/v1/incidents/${id}`);
}
