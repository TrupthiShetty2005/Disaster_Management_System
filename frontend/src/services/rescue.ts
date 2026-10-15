import type { ListResponse, RescuePlan, RescuePriorityItem } from "../types/api";
import { apiGet, apiPost, isMockMode } from "./apiClient";
import { mockResources } from "../data/mock";

const mockPriorities: RescuePriorityItem[] = [
  {
    id: "prio1",
    disaster_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    title: "Isolate polder hamlet cluster",
    priority: 1,
    people_affected: 1200,
    status: "in_progress",
    score: 72,
    level: "HIGH",
    geojson: { type: "Point", coordinates: [76.527, 9.522] },
    estimate_label: "Prototype rescue priority (not guaranteed optimal)",
  },
];

const mockPlan: RescuePlan = {
  id: "plan-demo",
  disaster_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  priority_id: "prio1",
  decision: "PENDING",
  override_notes: "",
  created_at: "2026-07-14T06:00:00Z",
  estimate_label: "Prototype decision-support recommendation — not a guaranteed optimal allocation",
  plan: {
    incident: { id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", title: "Kuttanad flood (demo)", type: "flood", severity: "high" },
    priority: { id: "prio1", title: "Isolate polder hamlet cluster", score: 72, level: "HIGH" },
    affected_population: 18400,
    required_resources: [
      { type: "RESCUE_BOAT", count: 1, reason: "High flood + population" },
      { type: "AMBULANCE", count: 1, reason: "Medical urgency" },
    ],
    available_resources: mockResources.map((r) => ({
      id: r.id,
      name: r.name,
      type: r.resource_type.toUpperCase(),
      status: r.status.toUpperCase(),
    })),
    recommended_allocation: [{ resource_id: "res2", name: "Ambulance 12 (demo)", type: "AMBULANCE", action: "recommend_deploy" }],
    unmet_need: { RESCUE_BOAT: 1 },
    evacuation_route: {
      path: ["incident", "junction_east", "amb_base", "shelter"],
      estimated_minutes: 18,
      geojson: {
        type: "Feature",
        geometry: { type: "LineString", coordinates: [[76.527, 9.522], [76.538, 9.516], [76.54, 9.508]] },
        properties: {},
      },
    },
    routes: {
      note: "Graph-based demo routing. Not Google Maps.",
      estimated_response_time_min: 18,
      blocked_roads: {
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            geometry: { type: "LineString", coordinates: [[76.527, 9.522], [76.515, 9.518]] },
            properties: {},
          },
        ],
      },
      primary_access: {
        geojson: {
          type: "Feature",
          geometry: { type: "LineString", coordinates: [[76.525, 9.519], [76.527, 9.522]] },
          properties: {},
        },
      },
    },
    estimated_response_time: 18,
    warnings: ["Primary road blocked — use alternate route planning (demo graph, not Google Maps)."],
    reasoning: ["High flood with large population → rescue boats for last-mile access."],
    estimate_label: "Prototype decision-support recommendation — not a guaranteed optimal allocation",
    map: {
      incident: { type: "Point", coordinates: [76.527, 9.522] },
      hospital: { type: "Point", coordinates: [76.548, 9.512] },
      shelter: { type: "Point", coordinates: [76.54, 9.508] },
    },
  },
};

export async function fetchRescuePriorities(): Promise<ListResponse<RescuePriorityItem>> {
  if (isMockMode()) return { items: mockPriorities, total: 1 };
  return apiGet("/api/v1/rescue/priorities");
}

export async function generateRescuePlan(): Promise<RescuePlan> {
  if (isMockMode()) return mockPlan;
  return apiPost("/api/v1/rescue/plan", {});
}

export async function decideRescuePlan(planId: string, action: string, notes = ""): Promise<RescuePlan> {
  const decision = { accept: "ACCEPTED", modify: "MODIFIED", reject: "REJECTED" }[action] ?? action.toUpperCase();
  if (isMockMode()) return { ...mockPlan, id: planId, decision, override_notes: notes };
  return apiPost(`/api/v1/rescue/plans/${planId}/decision`, { action, notes });
}
