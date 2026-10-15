import type { MapPoint } from "../types/api";
import { mockMapPoints } from "../data/mock";
import { apiGet, isMockMode } from "./apiClient";
import { fetchSatelliteSummary as fetchSatNote } from "./satellite";

export async function fetchSatelliteSummary(): Promise<{ note: string }> {
  return fetchSatNote();
}

export async function fetchFloodSummary(): Promise<{ note: string; depthM: number; km2: number }> {
  if (isMockMode()) {
    return { note: "Demo Mode stub flood detector — not a trained model.", depthM: 1.8, km2: 34.5 };
  }
  try {
    const body = await apiGet<{ items: { flooded_area?: number; notes?: string }[]; total: number }>(
      "/api/v1/flood/events",
    );
    const row = body.items[0];
    return {
      note: row?.notes?.includes("Satellite-derived")
        ? "Satellite-derived water-change indication — requires validation (see /flood-detection)."
        : "Flood summary from live analysis API.",
      depthM: 0,
      km2: Number(row?.flooded_area ?? 0),
    };
  } catch {
    return { note: "Flood summary unavailable (live API error).", depthM: 0, km2: 0 };
  }
}

export async function fetchDamageSummary(): Promise<{ note: string; cls: string }> {
  if (isMockMode()) {
    return { note: "Demo Mode stub damage classifier.", cls: "moderate" };
  }
  return { note: "Use /damage-assessment for Sentinel before/after change indication.", cls: "unknown" };
}

export { fetchAnalytics } from "./analytics";

export async function fetchMapPoints(): Promise<MapPoint[]> {
  if (isMockMode()) return mockMapPoints;
  return [];
}
