import type { Disaster, ListResponse } from "../types/api";
import { mockDisasters } from "../data/mock";
import { apiGet, isMockMode } from "./apiClient";

export async function fetchDisasters(): Promise<ListResponse<Disaster>> {
  if (isMockMode()) return { items: mockDisasters, total: mockDisasters.length };
  return apiGet<ListResponse<Disaster>>("/api/v1/disasters");
}

export async function fetchDisaster(id: string): Promise<Disaster> {
  if (isMockMode()) {
    const found = mockDisasters.find((d) => d.id === id) ?? mockDisasters[0];
    return found;
  }
  return apiGet<Disaster>(`/api/v1/disasters/${id}`);
}
