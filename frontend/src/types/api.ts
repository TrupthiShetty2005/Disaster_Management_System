export type GeoJSON = Record<string, unknown> | null;

export interface Location {
  id: string;
  name: string;
  district: string;
  state: string;
  country: string;
  latitude: number;
  longitude: number;
  geojson: GeoJSON;
}

export interface Disaster {
  id: string;
  title: string;
  disaster_type: string;
  phase: string;
  severity: string;
  status: string;
  people_at_risk: number;
  location_id: string;
  geojson: GeoJSON;
  summary: string;
  started_at: string;
  location?: Location | null;
}

export interface ListResponse<T> {
  items: T[];
  total: number;
  query?: Record<string, unknown> | null;
}

export interface RiskFactor {
  name: string;
  level: string;
  value: number;
}

export interface RiskZone {
  id: string;
  name: string;
  hazard_type: string;
  risk_score: number;
  risk_level: string;
  location_id: string;
  geojson: GeoJSON;
  flood_probability?: number;
  affected_population?: number;
  contributing_factors?: RiskFactor[];
  recommended_action?: string;
  estimate_label?: string;
}

export interface WeatherCurrent {
  id: string;
  location_id: string;
  source: string;
  temperature_c: number;
  humidity: number;
  rainfall_mm: number | null;
  wind_speed_ms: number;
  pressure_hpa: number;
  visibility_km?: number | null;
  river_level_m?: number | null;
  storm_probability?: number | null;
  conditions: string;
  observed_at: string;
  provider_live: boolean;
  aoi_name?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  record_kind?: string;
  units?: Record<string, string> | null;
}

export interface WeatherHistoryPoint {
  observed_at: string;
  rainfall_mm: number | null;
  temperature_c: number | null;
  humidity: number | null;
  wind_speed_ms: number | null;
  river_level_m: number | null;
  source: string;
  record_kind?: string;
  spatial_resolution?: string | null;
  missing_fields?: string[] | null;
}

export interface RainfallAnalysis {
  cumulative_mm: number;
  intensity_mm_h: number;
  anomaly: number;
  short_term_risk: number;
  label: string;
}

export interface FloodRisk {
  flood_probability: number;
  risk_score: number;
  risk_level: string;
  factors: RiskFactor[];
  recommended_action: string;
  estimate_label: string;
}

export interface CycloneRisk {
  cyclone_risk: number;
  severity: string;
  affected_region: string;
  recommended_action: string;
  storm_probability: number;
  estimate_label: string;
}

export interface WeatherAlertsPayload {
  items: AlertItem[];
  total: number;
  flood_probability: number;
  cyclone_risk: number;
  dispatch: string;
  imd_status?: string;
  imd_source_status?: "NOT_CONFIGURED" | "UNAVAILABLE" | "LIVE" | "LIVE_EMPTY" | "MOCK" | string;
}

export interface WeatherForecast {
  id: string;
  location_id: string;
  source: string;
  period_start: string;
  period_end: string;
  temperature_c: number;
  rainfall_mm: number | null;
  wind_speed_ms: number;
  humidity?: number | null;
  pressure_hpa?: number | null;
  conditions: string;
  record_kind?: string;
}

export interface AlertItem {
  id: string;
  title: string;
  severity: string;
  category: string;
  message: string;
  location_id: string | null;
  issued_at: string;
  location_name?: string;
  recommendation?: string;
  alert_type?: string;
  latitude?: number;
  longitude?: number;
  risk_score?: number;
  expires_at?: string | null;
  status?: string;
  recommended_action?: string;
  source?: string;
  acknowledged_at?: string | null;
  acknowledged_by?: string;
  reason?: string;
  disclaimer?: string;
  official_warning?: boolean;
  provenance_status?: string;
  alert_kind?: string;
}

export interface RescueResource {
  id: string;
  name: string;
  resource_type: string;
  status: string;
  personnel: number;
  capacity?: number;
  latitude?: number;
  longitude?: number;
  assigned_incident?: string | null;
  location_id: string;
  geojson: GeoJSON;
  current_location?: GeoJSON;
}

export interface RescuePriorityItem {
  id: string;
  disaster_id: string;
  title: string;
  priority: number;
  people_affected: number;
  status: string;
  score: number;
  level: string;
  factors?: Record<string, number> | null;
  geojson: GeoJSON;
  estimate_label?: string;
}

export interface RescuePlan {
  id: string;
  disaster_id: string;
  priority_id: string | null;
  decision: string;
  override_notes: string;
  plan: {
    incident: { id: string; title: string; type: string; severity: string };
    priority: { id: string | null; title: string; score: number | null; level: string | null };
    affected_population: number;
    required_resources: { type: string; count: number; reason: string }[];
    available_resources: { id: string; name: string; type: string; status: string }[];
    recommended_allocation: { resource_id: string; name: string; type: string; action: string }[];
    unmet_need: Record<string, number>;
    evacuation_route: { path: string[]; geojson: GeoJSON; estimated_minutes: number };
    routes: {
      blocked_roads: GeoJSON;
      primary_access?: { geojson: GeoJSON };
      medical?: { geojson: GeoJSON };
      estimated_response_time_min: number;
      note: string;
    };
    estimated_response_time: number;
    warnings: string[];
    reasoning: string[];
    estimate_label: string;
    map: {
      incident: { type: string; coordinates: [number, number] };
      hospital: { type: string; coordinates: [number, number] };
      shelter: { type: string; coordinates: [number, number] };
    };
  };
  created_at: string;
  estimate_label?: string;
}

export interface EvacuationCenter {
  id: string;
  name: string;
  capacity: number;
  occupied: number;
  status: string;
  location_id: string;
  geojson: GeoJSON;
}

export interface MapPoint {
  id: string;
  kind: string;
  name: string;
  lat: number;
  lng: number;
  severity?: string;
}

export interface AnalyticsBundle {
  riskTrend: number[];
  rainfallTrend: Array<number | null>;
  rainfallLabels?: string[];
  rainfallAvailable?: boolean;
  rainfallSource?: string;
  affectedPopulation: number[];
  resourceUtilization: number[];
  labels: string[];
  floodAreaTrend?: number[];
  severityMix?: number[];
  populationAvailable?: boolean;
  resourceUtilizationAvailable?: boolean;
  floodAreaAvailable?: boolean;
  severityMixAvailable?: boolean;
}

export interface SatelliteImageItem {
  id: string;
  source: string;
  acquisition_time: string;
  latitude: number | null;
  longitude: number | null;
  bounding_box: GeoJSON;
  resolution: string;
  cloud_cover: number;
  image_url: string;
  thumbnail_url: string;
  status: string;
  metadata?: Record<string, unknown> | null;
  title: string;
  provider: string;
  location_id: string;
}

export interface SatelliteAnalysis {
  id: string;
  satellite_image_id: string;
  model_name: string;
  analysis_type: string;
  summary: string;
  confidence: number;
  result_geojson: { type: string; features: unknown[] } | null;
  metrics: Record<string, number | string | object | null> | null;
  created_at: string;
  estimate_label?: string;
}

export interface VisionDetection {
  label: string;
  confidence: number;
  bbox: number[];
  severity: string;
  specialized: boolean;
}

export interface VisionResult {
  image_id: string;
  model_name: string;
  backend: string;
  overall_severity: string;
  processing_time_ms: number;
  detections: VisionDetection[];
  incident: {
    counts: Record<string, number>;
    headline: string;
    recommended_actions: string[];
    severity_rationale?: string;
    severity_score?: number;
  } | null;
  notes: string;
  annotated_url: string;
  gpu_required: boolean;
}

export interface FloodEvent {
  id: string;
  model_name: string;
  scene_kind: string;
  flooded_area: number;
  flood_percentage: number;
  severity: string;
  confidence: number;
  boundary_geojson: GeoJSON;
  heatmap_geojson: GeoJSON;
  affected_population: number;
  affected_roads: number;
  affected_buildings: number;
  notes: string;
  created_at: string;
  estimate_label?: string;
  before_water_area_km2?: number | null;
  after_water_area_km2?: number | null;
  newly_flooded_area_km2?: number | null;
  newly_flooded_percentage?: number | null;
  percentage_change?: number | null;
  before_image_id?: string | null;
  after_image_id?: string | null;
  before_stac_id?: string | null;
  after_stac_id?: string | null;
  before_date?: string | null;
  after_date?: string | null;
  before_cloud?: number | null;
  after_cloud?: number | null;
  before_preview_url?: string | null;
  after_preview_url?: string | null;
  before_water_geojson?: GeoJSON | null;
  after_water_geojson?: GeoJSON | null;
  newly_flooded_geojson?: GeoJSON | null;
  change_metrics?: Record<string, number | string> | null;
  analysis_status?: string | null;
  processing_method?: string | null;
  spatial_resolution?: string | null;
  validated_flood_boundary?: boolean;
  impact_stats_available?: boolean;
}

export interface DamageReportPayload {
  executive_summary: string;
  affected_area: Record<string, number>;
  building_statistics: { counts: Record<string, number>; damaged_percentage: number; primary: string };
  road_statistics: { counts: Record<string, number>; destroyed_roads: number; blocked_or_destroyed: number; primary: string };
  flood_statistics: Record<string, number>;
  infrastructure_loss: Record<string, number>;
  priority_areas: { name: string; rank: number; action: string }[];
  recommended_actions: string[];
  pdf_generation?: string;
}

export interface DamageAssessment {
  id: string;
  model_name: string;
  before_kind: string;
  after_kind: string;
  report: DamageReportPayload;
  overlay_geojson: GeoJSON;
  created_at: string;
  estimate_label?: string;
  pdf_available: boolean;
}
