export type Level = "NORMAL" | "WATCH" | "WARNING" | "SEVERE" | "CALIBRATING";
export type Severity = "INFO" | "WATCH" | "WARNING" | "SEVERE";
export type BBox = [number, number, number, number];

export interface Live<T> {
  status: "live" | "unavailable";
  data?: T;
  detail?: string;
}

export interface District {
  id: string;
  name: string;
  hq: string;
  latitude: number;
  longitude: number;
  coastal: boolean;
}

export interface Station {
  id: string;
  name: string;
  river: string;
  kind: string;
  district_id: string;
  latitude: number;
  longitude: number;
}

export interface DischargePoint {
  date: string;
  discharge: number | null;
  median: number | null;
  p25: number | null;
  p75: number | null;
  min: number | null;
  max: number | null;
  forecast: boolean;
}

export interface Thresholds {
  q2: number;
  q5: number;
  q20: number;
  record_years: number;
  record_period: string;
  season_median_flow: number;
  record_max: number;
  record_max_year: number;
}

export interface StationReport extends Station {
  district: string;
  glofas_cell: { latitude: number; longitude: number; mean_flow_28d: number };
  current: DischargePoint;
  current_level: Level;
  percent_of_2yr_flood: number | null;
  trend_7d_pct: number | null;
  forecast_peak: Record<"expected" | "upper_p75" | "worst_case", { date: string; discharge: number }>;
  predicted_level: Level;
  predicted_level_upper?: Level;
  status: Level;
  thresholds: Thresholds | null;
  series?: DischargePoint[];
  unit: string;
  source: string;
  method: string;
}

export interface RainDay {
  date: string;
  rain_mm: number;
  probability_pct: number | null;
  forecast: boolean;
}

export interface RainDistrict extends District {
  observed_7d_mm: number;
  observed_30d_mm: number;
  forecast_3d_mm: number;
  forecast_7d_mm: number;
  peak_day: RainDay;
  category: string;
  alert_level: Level;
  series?: RainDay[];
}

export interface RainResponse {
  items: RainDistrict[];
  source: string;
  categories_mm_per_day: Record<string, number>;
  note: string;
}

export interface FireDetection {
  latitude: number;
  longitude: number;
  acquired_at: string;
  sensor: string;
  satellite?: string;
  confidence: string;
  frp_mw: number | null;
  brightness_k?: number | null;
  daynight?: string;
  district_id?: string;
  district: string;
}

export interface DetectionsResponse {
  window: string;
  count: number;
  detections: FireDetection[];
  feeds: Record<string, number>;
  feed_errors: Record<string, string>;
  retrieved_at: string;
  clipped_by: string;
}

export interface FireCluster {
  id: string;
  latitude: number;
  longitude: number;
  bbox: BBox;
  district_id: string;
  district: string;
  detections: number;
  high_confidence: number;
  total_frp_mw: number;
  max_frp_mw: number;
  first_seen: string;
  last_seen: string;
  active_24h: boolean;
  days_seen: number;
  persistent_heat_source: boolean;
  classification: string;
  sensors: string[];
  severity: Severity;
  score: number;
  points: [number, number][];
}

export interface DangerDay {
  date: string;
  ffwi: number;
  level: string;
  temp_max_c: number;
  rh_min_pct: number;
  wind_max_kmh: number;
  rain_mm: number;
}

export interface DangerDistrict {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  active_detections_48h: number;
  days: DangerDay[];
  peak_level: string;
  peak_ffwi: number;
}

export interface DisasterEvent {
  id: string;
  hazard: string;
  name: string;
  description: string;
  alert_level: string;
  is_current: boolean;
  from_date: string;
  to_date: string;
  latitude: number;
  longitude: number;
  severity: string;
  glide: string | null;
  report_url: string | null;
  source: string;
  near_karnataka: boolean;
  inside_karnataka: boolean;
}

export interface Alert {
  id: string;
  key: string;
  hazard: string;
  severity: Severity;
  title: string;
  message: string;
  district: string | null;
  latitude: number | null;
  longitude: number | null;
  source: string;
  source_url: string | null;
  observed_value: number | null;
  threshold: number | null;
  unit: string | null;
  valid_from: string | null;
  valid_until: string | null;
  status: "ACTIVE" | "ACKNOWLEDGED" | "RESOLVED" | "EXPIRED";
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  payload: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface Exposure {
  buildings: number;
  buildings_in_search_area: number;
  road_km: number;
  major_road_km: number;
  minor_road_km: number;
  road_km_by_class: Record<string, number>;
  railway_km: number;
  power_line_km: number;
  facilities: Record<string, number>;
}

export interface Impact {
  status: "complete" | "no_hazard_footprint" | "osm_unavailable";
  hazard_type?: string;
  hazard_area_km2?: number;
  exposed?: Exposure;
  facilities?: { kind: string; name: string; latitude: number; longitude: number }[];
  loss?: {
    currency: string;
    exposed_replacement_value: number;
    damage_ratio: number;
    estimated_loss: number;
    estimated_loss_crore: number;
    by_asset: Record<string, number>;
    assumptions: Record<string, number | string>;
  };
  source?: string;
  detail?: string;
}

export interface Scene {
  key: string;
  collection: string;
  sensor: string;
  date: string;
  datetime: string;
  platform: string;
  cloud_cover: number | null;
  orbit_state: string | null;
  relative_orbit: number | null;
  item_ids: string[];
  coverage: number;
}

export interface ScenesResponse {
  area_name: string;
  bbox: BBox;
  sentinel2: Scene[];
  sentinel1: Scene[];
  source: string;
}

export interface Analysis {
  id: string;
  kind: "flood" | "burn";
  area_name: string;
  bbox: BBox;
  status: string;
  before: Scene;
  after: Scene;
  metrics: Record<string, unknown> & { method?: string };
  geojson?: GeoJSON.FeatureCollection;
  impact: Impact | null;
  images: Record<string, string>;
  image_bounds: BBox | null;
  created_at: string;
}

export interface Overview {
  alerts: { open: number; by_severity: Record<string, number>; by_hazard: Record<string, number> };
  water: Live<{ stations: StationReport[]; by_status: Record<string, number>; highest: StationReport | null }>;
  fire: Live<{
    detections_24h: number;
    detections_24h_points: FireDetection[];
    active_clusters: FireCluster[];
    clusters_7d: number;
    industrial_sources: FireCluster[];
    by_district_24h: Record<string, number>;
  }>;
  rain: Live<{ districts: RainDistrict[]; heavy_forecast: RainDistrict[]; wettest_7d: string | null }>;
  events: Live<DisasterEvent[]>;
  recent_analyses: {
    id: string;
    kind: string;
    area_name: string;
    created_at: string;
    metrics: Record<string, unknown>;
    impact_summary: Exposure | null;
    loss: number | null;
    bbox: BBox;
  }[];
}

export interface Analytics {
  fires: Live<never> & { days?: string[]; vegetation?: number[]; industrial?: number[]; by_district?: Record<string, number> };
  rain: Live<never> & { dates?: string[]; state_mean_mm?: number[]; forecast?: boolean[]; wettest_30d?: { name: string; mm: number }[] };
  rivers: Live<never> & {
    stations?: { id: string; name: string; status: Level; q2: number | null; dates: string[]; discharge: (number | null)[]; forecast_from: string }[];
  };
  alerts: { days: string[]; series: Record<string, number[]>; by_severity: Record<string, number>; total_30d: number };
  fire_history: { times: string[]; detections_24h: number[] };
  analyses: { id: string; kind: string; area_name: string; created_at: string; hazard_km2: number | null; buildings: number; road_km: number; loss_crore: number | null }[];
}

export interface Responder {
  kind: string;
  name: string;
  latitude: number;
  longitude: number;
  phone: string | null;
  straight_km: number;
  osm_id: string;
  route: { distance_km: number; duration_min: number; geometry: GeoJSON.LineString } | null;
  route_error?: string;
}

export interface RescuePlan {
  target: { latitude: number; longitude: number };
  responders: Responder[];
  facilities_found: Record<string, number>;
  sources: Record<string, string>;
  note: string;
}

export interface VisionDetection {
  label: string;
  confidence: number;
  bbox: [number, number, number, number];
}

export interface VisionJob {
  id: string;
  filename: string;
  model: string;
  detections: VisionDetection[];
  summary: { by_label: Record<string, number>; groups: Record<string, number>; total: number };
  processing_ms: number;
  image_url: string;
  created_at: string;
}

export interface SourceStatus {
  name: string;
  purpose: string;
  ok: boolean;
  latency_ms: number;
  detail: string;
}

export interface Weather {
  district: { id: string; name: string; hq: string; latitude: number; longitude: number };
  current: {
    observed_at: number;
    station: string;
    temperature_c: number;
    feels_like_c: number;
    humidity_pct: number;
    pressure_hpa: number;
    wind_speed_ms: number;
    wind_gust_ms: number | null;
    rain_1h_mm: number | null;
    clouds_pct: number;
    condition: string;
    source: string;
  } | null;
  forecast: { time: number; temperature_c: number; humidity_pct: number; wind_speed_ms: number; rain_3h_mm: number; pop: number; condition: string }[] | null;
  hourly: { hourly: { time: string[]; precipitation: number[]; precipitation_probability: number[]; temperature_2m: number[] } } | null;
  unavailable?: Record<string, string>;
}
