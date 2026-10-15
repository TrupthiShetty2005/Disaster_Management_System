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
  nearest_site?: { id: string; name: string; distance_km: number } | null;
  members?: FireDetectionRecord[];
}

export interface FireDetectionRecord {
  latitude: number;
  longitude: number;
  acquired_at: string;
  sensor: string;
  satellite?: string | null;
  confidence: string;
  frp_mw: number | null;
  daynight?: string | null;
}

export interface SiteDetection extends FireDetectionRecord {
  distance_km: number;
  nearest_facility: string;
}

export interface MonitoredSite {
  id: string;
  name: string;
  kind: string;
  district_id: string;
  district: string;
  latitude: number;
  longitude: number;
  radius_km: number;
  facilities: { name: string; latitude: number; longitude: number }[];
  status: "DETECTED_24H" | "DETECTED" | "NO_DETECTION";
  counts: Record<string, number>;
  last_detection: string | null;
  days_with_detections: number;
  total_frp_mw: number;
  max_frp_mw: number;
  history: SiteDetection[];
  nearest_detection: SiteDetection | null;
  cloud_at_passes: { mean_pct: number | null; days: { date: string; night_pct: number | null; day_pct: number | null }[] } | null;
  summary: string;
}

export interface IndustrialSitesResponse {
  items: MonitoredSite[];
  coverage: { window: string; from: string | null; to: string | null };
  feeds: Record<string, number>;
  unavailable_windows: Record<string, string>;
  archive: { map_key_configured: boolean; windows: string[]; max_days: number; note: string };
  limitations: string;
  sources: string;
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

export type DamageClass = "newly_flooded" | "burned" | "edge_contact" | "persistent_water" | "none";

export interface BuildingAsset {
  osm_id: string;
  name: string | null;
  building: string | null;
  height_m: number;
  height_source: "osm_height" | "osm_levels" | "estimated_default";
  levels: number | null;
  affected: boolean;
  damage_class: DamageClass;
  overlap_pct: number;
  footprint_m2: number;
}

export interface LineAsset {
  osm_id: string;
  kind: "road" | "railway" | "power_line";
  class: string;
  name: string | null;
  major: boolean;
  voltage?: string;
  affected: boolean;
  damage_class: DamageClass;
  length_km: number;
}

export interface FacilityAsset {
  osm_id: string;
  kind: string;
  name: string;
  affected: boolean;
  damage_class: DamageClass;
}

export interface AnalysisAssets {
  analysis_id: string;
  status: "complete" | "no_hazard_footprint" | "osm_unavailable";
  detail?: string;
  hazard_type?: string;
  generated_at?: string;
  center?: [number, number];
  search_bbox?: BBox;
  buildings?: GeoJSON.FeatureCollection<GeoJSON.Polygon | GeoJSON.MultiPolygon, BuildingAsset>;
  lines?: GeoJSON.FeatureCollection<GeoJSON.LineString, LineAsset>;
  facilities?: GeoJSON.FeatureCollection<GeoJSON.Point, FacilityAsset>;
  summary?: {
    buildings_affected: number;
    buildings_nearby_unaffected: number;
    buildings_edge_contact: number;
    buildings_returned: number;
    buildings_without_outline: number;
    height_sources: Record<string, number>;
    road_km_affected: number;
    railway_km_affected: number;
    power_line_km_affected: number;
    facilities_affected: number;
  };
  limits?: { max_affected_buildings: number; max_context_buildings: number; context_radius_m: number; truncated: boolean };
  method?: { affected_rule: string; damage_classes: Record<string, string>; height: string; flood_depth: string | null };
  source?: string;
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

export interface VisionSummary {
  by_label: Record<string, number>;
  groups: Record<string, number>;
  total: number;
}

export interface VisionJob {
  id: string;
  kind?: "image" | "video";
  filename: string;
  model: string;
  detections: VisionDetection[];
  summary: VisionSummary & Partial<VisionVideoResult>;
  processing_ms: number;
  image_url: string | null;
  video_url?: string;
  created_at: string;
}

export interface VisionTimelinePoint {
  t: number;
  people: number;
  vehicles: number;
  boats: number;
  animals: number;
  total: number;
}

export interface VisionVideoResult {
  codec: string;
  browser_playable: boolean;
  source: { fps: number; frames: number; width: number; height: number; duration_s: number | null };
  processed: { stride: number; fps: number; width: number; height: number; seconds: number; conf: number; tracker: string; min_track_frames?: number };
  frames_processed: number;
  timeline: VisionTimelinePoint[];
  peak: Record<string, number>;
  unique: Record<string, number>;
  unique_by_label: Record<string, number>;
  unique_total: number;
  detections_by_label: Record<string, number>;
  avg_ms: number | null;
  fps: number | null;
  wall_s?: number;
}

export interface VisionImageResult {
  width: number;
  height: number;
  detections: VisionDetection[];
  summary: VisionSummary;
  processing_ms: number;
  conf: number;
  render_conf: number;
}

export interface VisionGalleryItem {
  id: string;
  kind: "image" | "video";
  title: string;
  description: string;
  location: string;
  year: number | null;
  source_url: string;
  author: string;
  licence: string;
  licence_url: string;
  result: VisionImageResult | VisionVideoResult | null;
  error: string | null;
  original_url?: string;
  annotated_url?: string;
}

export interface VisionGalleryBuild {
  status: "idle" | "running" | "ready" | "error";
  done: number;
  total: number;
  current: string | null;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface VisionGallery {
  build: VisionGalleryBuild;
  built_at: string | null;
  model: { name: string; dataset: string; device: string; machine: string; video_codec: string };
  stats: {
    images: number;
    videos: number;
    video_frames: number;
    video_seconds: number;
    objects: number;
    by_label: Record<string, number>;
    groups: Record<string, number>;
    image_avg_ms: number | null;
    image_max_ms: number | null;
    video_avg_ms: number | null;
    video_fps: number | null;
    render_conf: number;
  };
  items: VisionGalleryItem[];
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
