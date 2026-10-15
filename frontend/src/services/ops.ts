import type { EvacuationCenter, ListResponse, RescueResource } from "../types/api";
import { mockCenters, mockResources } from "../data/mock";
import { apiGet, isMockMode } from "./apiClient";

export { fetchAlerts, generateAlerts, acknowledgeAlert, resolveAlert } from "./alerts";

export async function fetchResources(): Promise<ListResponse<RescueResource>> {
  if (isMockMode()) return { items: mockResources, total: mockResources.length };
  return apiGet("/api/v1/resources");
}

export async function fetchCenters(): Promise<ListResponse<EvacuationCenter>> {
  if (isMockMode()) return { items: mockCenters, total: mockCenters.length };
  return apiGet("/api/v1/evacuation-centers");
}
