import type { AlertItem, ListResponse } from "../types/api";
import { mockAlerts } from "../data/mock";
import { apiGet, apiPost, isMockMode } from "./apiClient";

function query(params: Record<string, string | undefined>): string {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v) q.set(k, v);
  });
  const s = q.toString();
  return s ? `?${s}` : "";
}

export async function fetchAlerts(filters: {
  severity?: string;
  location_id?: string;
  status?: string;
  disaster_type?: string;
} = {}): Promise<ListResponse<AlertItem>> {
  if (isMockMode()) return { items: mockAlerts, total: mockAlerts.length };
  return apiGet(`/api/v1/alerts${query(filters)}`);
}

export async function generateAlerts(): Promise<ListResponse<AlertItem>> {
  if (isMockMode()) return { items: mockAlerts, total: mockAlerts.length };
  return apiPost("/api/v1/alerts/generate", {});
}

export async function acknowledgeAlert(id: string): Promise<AlertItem> {
  if (isMockMode()) {
    const found = mockAlerts.find((a) => a.id === id) ?? mockAlerts[0];
    return { ...found, status: "ACKNOWLEDGED", acknowledged_by: "ops.demo" };
  }
  return apiPost(`/api/v1/alerts/${id}/acknowledge`, { actor: "ops.demo" });
}

export async function resolveAlert(id: string): Promise<AlertItem> {
  if (isMockMode()) {
    const found = mockAlerts.find((a) => a.id === id) ?? mockAlerts[0];
    return { ...found, status: "RESOLVED" };
  }
  return apiPost(`/api/v1/alerts/${id}/resolve`, { actor: "ops.demo" });
}

export async function pollAlertEvents(since?: string): Promise<{ items: { type: string; id?: string; emitted_at?: string }[] }> {
  if (isMockMode()) return { items: [] };
  const q = since ? `?since=${encodeURIComponent(since)}` : "";
  return apiGet(`/api/v1/alerts/events${q}`);
}
