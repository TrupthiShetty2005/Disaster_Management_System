import type { ListResponse, RiskZone } from "../types/api";
import { mockRiskZones } from "../data/mock";
import { apiGet, isMockMode } from "./apiClient";

export async function fetchRiskZones(): Promise<ListResponse<RiskZone>> {
  if (isMockMode()) return { items: mockRiskZones, total: mockRiskZones.length };
  return apiGet("/api/v1/risk-zones");
}

export async function fetchRiskZone(id: string): Promise<RiskZone> {
  if (isMockMode()) return mockRiskZones.find((z) => z.id === id) ?? mockRiskZones[0];
  return apiGet(`/api/v1/risk-zones/${id}`);
}
