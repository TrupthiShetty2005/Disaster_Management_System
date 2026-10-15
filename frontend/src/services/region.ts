import { apiBase, apiGet } from "./apiClient";

export type AoiState = {
  country: string;
  state: string;
  district: string | null;
  aoi_name: string;
  latitude: number;
  longitude: number;
  bbox: number[];
  bbox_pad_deg: number;
  boundary_geojson: GeoJSON.GeoJsonObject | null;
  source: string;
  status: string;
  coverage_note?: string;
  display_name?: string;
};

export type DistrictItem = {
  name: string;
  osm_id: number;
  latitude: number;
  longitude: number;
  admin_level?: string;
};

export type IndiaRegions = {
  country: string;
  primary_state: string;
  source: string;
  status: string;
  description?: string;
  india: { status: string; geojson?: GeoJSON.GeoJsonObject | null; bbox?: number[] | null; name?: string };
  karnataka: { status: string; geojson?: GeoJSON.GeoJsonObject | null; bbox?: number[] | null; name?: string };
};

async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = (await res.json()) as { detail?: string };
      if (typeof j.detail === "string") detail = j.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export async function fetchAoi(): Promise<AoiState> {
  return apiGet("/api/v1/gis/aoi");
}

export async function fetchIndiaRegions(): Promise<IndiaRegions> {
  return apiGet("/api/v1/gis/india");
}

export async function fetchKarnatakaDistricts(): Promise<{
  items: DistrictItem[];
  status: string;
  total: number;
  source: string;
}> {
  return apiGet("/api/v1/gis/karnataka/districts");
}

export async function selectDistrict(district: string, bboxPadDeg?: number): Promise<AoiState> {
  return apiPut("/api/v1/gis/aoi", { district, bbox_pad_deg: bboxPadDeg });
}

export async function selectPointAoi(lat: number, lon: number, pad?: number, name?: string): Promise<AoiState> {
  return apiPut("/api/v1/gis/aoi", { latitude: lat, longitude: lon, bbox_pad_deg: pad, aoi_name: name });
}
