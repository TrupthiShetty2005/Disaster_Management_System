import type {
  AlertItem,
  AnalyticsBundle,
  CycloneRisk,
  Disaster,
  EvacuationCenter,
  FloodRisk,
  MapPoint,
  RainfallAnalysis,
  RescueResource,
  RiskZone,
  WeatherCurrent,
  WeatherForecast,
  WeatherHistoryPoint,
} from "../types/api";

export const mockDisasters: Disaster[] = [
  {
    id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    title: "Kuttanad monsoon inundation (demo)",
    disaster_type: "flood",
    phase: "response",
    severity: "high",
    status: "active",
    people_at_risk: 42000,
    location_id: "11111111-1111-4111-8111-111111111111",
    geojson: { type: "Point", coordinates: [76.522, 9.517] },
    summary: "Fictional demo of prolonged rainfall and embankment stress in Kuttanad polders.",
    started_at: "2026-07-12T06:00:00",
    location: {
      id: "11111111-1111-4111-8111-111111111111",
      name: "Kuttanad Wetlands (demo)",
      district: "Alappuzha",
      state: "Kerala",
      country: "India",
      latitude: 9.517,
      longitude: 76.522,
      geojson: null,
    },
  },
  {
    id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    title: "Guwahati hillslope displacement (demo)",
    disaster_type: "landslide",
    phase: "precaution",
    severity: "medium",
    status: "monitoring",
    people_at_risk: 8500,
    location_id: "22222222-2222-4222-8222-222222222222",
    geojson: { type: "Point", coordinates: [91.752, 26.185] },
    summary: "Demo slope-risk watch. Not an official bulletin.",
    started_at: "2026-07-13T12:00:00",
  },
  {
    id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    title: "Bay of Bengal cyclone track (demo)",
    disaster_type: "cyclone",
    phase: "recovery",
    severity: "severe",
    status: "recovering",
    people_at_risk: 110000,
    location_id: "33333333-3333-4333-8333-333333333333",
    geojson: { type: "Point", coordinates: [85.831, 19.813] },
    summary: "Post-landfall recovery demo.",
    started_at: "2026-07-08T06:00:00",
  },
];

export const mockRiskZones: RiskZone[] = [
  {
    id: "r1",
    name: "Polder A floodplain",
    hazard_type: "flood",
    risk_score: 0.86,
    risk_level: "high",
    location_id: mockDisasters[0].location_id,
    geojson: null,
    flood_probability: 82,
    affected_population: 42000,
    estimate_label: "Prototype AI Risk Estimate",
    recommended_action: "Evacuate remaining low-lying households; boat last-mile only.",
    contributing_factors: [
      { name: "Rainfall", level: "High", value: 80 },
      { name: "River level", level: "High", value: 78 },
      { name: "Historical flood frequency", level: "Medium", value: 62 },
      { name: "Forecast trend", level: "High", value: 71 },
    ],
  },
  {
    id: "r2",
    name: "Hill ward 12",
    hazard_type: "landslide",
    risk_score: 0.71,
    risk_level: "high",
    location_id: "22222222-2222-4222-8222-222222222222",
    geojson: null,
  },
];

export const mockWeather: WeatherCurrent = {
  id: "w1",
  location_id: mockDisasters[0].location_id,
  source: "mock",
  temperature_c: 27.4,
  humidity: 94,
  rainfall_mm: 48.2,
  wind_speed_ms: 6.1,
  pressure_hpa: 1004,
  visibility_km: 4.2,
  river_level_m: 3.1,
  storm_probability: 0.34,
  conditions: "Heavy rain",
  observed_at: "2026-07-14T06:00:00",
  provider_live: false,
};

export const mockForecast: WeatherForecast[] = [0, 1, 2, 3, 4].map((i) => ({
  id: `f${i}`,
  location_id: mockWeather.location_id,
  source: "mock",
  period_start: `2026-07-14T${String(6 + i * 6).padStart(2, "0")}:00:00`,
  period_end: `2026-07-14T${String(12 + i * 6).padStart(2, "0")}:00:00`,
  temperature_c: 26 + i * 0.3,
  rainfall_mm: 12 - i,
  wind_speed_ms: 5 + i * 0.4,
  conditions: i < 3 ? "Rain" : "Showers",
}));

export const mockAlerts: AlertItem[] = [
  {
    id: "a1",
    title: "Heavy rainfall watch (demo)",
    severity: "warning",
    category: "weather",
    message: "40–60 mm / 6h possible over Kuttanad wetlands.",
    location_id: mockWeather.location_id,
    issued_at: "2026-07-14T05:00:00",
    location_name: "Kuttanad Wetlands (demo)",
    recommendation: "Hold flood watch; pre-position pumps at Polder A.",
  },
  {
    id: "a2",
    title: "Road closure — NH demo segment",
    severity: "critical",
    category: "accessibility",
    message: "Inundated carriageway; boats preferred for last-mile access.",
    location_id: mockWeather.location_id,
    issued_at: "2026-07-14T05:20:00",
    location_name: "Alappuzha–Changanassery stretch",
    recommendation: "Reroute ambulances via canal bridge 4; boat unit Delta for hamlets.",
  },
  {
    id: "a3",
    title: "Shelter occupancy update",
    severity: "info",
    category: "shelter",
    message: "Community school at 68% capacity.",
    location_id: mockWeather.location_id,
    issued_at: "2026-07-14T04:40:00",
    location_name: "Community school shelter",
    recommendation: "Keep overflow plan for Parish hall shelter.",
  },
];

export const mockResources: RescueResource[] = [
  {
    id: "res1",
    name: "Boat unit Delta (demo)",
    resource_type: "rescue_boat",
    status: "deployed",
    personnel: 8,
    location_id: mockWeather.location_id,
    geojson: { type: "Point", coordinates: [76.525, 9.519] },
  },
  {
    id: "res2",
    name: "Ambulance 12 (demo)",
    resource_type: "ambulance",
    status: "staging",
    personnel: 3,
    location_id: mockWeather.location_id,
    geojson: { type: "Point", coordinates: [76.535, 9.51] },
  },
];

export const mockCenters: EvacuationCenter[] = [
  {
    id: "c1",
    name: "Community school shelter (demo)",
    capacity: 800,
    occupied: 540,
    status: "open",
    location_id: mockWeather.location_id,
    geojson: { type: "Point", coordinates: [76.54, 9.508] },
  },
];

export const mockMapPoints: MapPoint[] = [
  { id: "d1", kind: "disaster", name: "Kuttanad flood", lat: 9.517, lng: 76.522, severity: "high" },
  { id: "d2", kind: "disaster", name: "Guwahati slope", lat: 26.185, lng: 91.752, severity: "medium" },
  { id: "d3", kind: "disaster", name: "Puri cyclone", lat: 19.813, lng: 85.831, severity: "severe" },
  { id: "e1", kind: "evacuation", name: "School shelter", lat: 9.508, lng: 76.54 },
  { id: "r1", kind: "resource", name: "Boat Delta", lat: 9.519, lng: 76.525 },
  { id: "f1", kind: "flood", name: "Polder water", lat: 9.52, lng: 76.53 },
];

export const mockAnalytics: AnalyticsBundle = {
  labels: ["T-4d", "T-3d", "T-2d", "T-1d", "Now"],
  riskTrend: [0.42, 0.51, 0.66, 0.78, 0.86],
  rainfallTrend: [8, 14, 22, 41, 48],
  affectedPopulation: [8, 14, 21, 33, 42],
  resourceUtilization: [20, 35, 48, 61, 73],
  floodAreaTrend: [6, 11, 18, 28, 34.5],
  severityMix: [1, 1, 3, 1],
};

export const mockHistory: WeatherHistoryPoint[] = [6, 9, 14, 22, 31, 41, 48.2].map((rain, i) => ({
  observed_at: `2026-07-${String(8 + i).padStart(2, "0")}T06:00:00`,
  rainfall_mm: rain,
  temperature_c: 28 - i * 0.2,
  humidity: 80 + i,
  wind_speed_ms: 3.5 + i * 0.3,
  river_level_m: 1.6 + i * 0.25,
  source: "mock",
}));

export const mockRainfall: RainfallAnalysis = {
  cumulative_mm: 171.2,
  intensity_mm_h: 2.01,
  anomaly: 3.02,
  short_term_risk: 88.4,
  label: "Prototype rainfall analysis",
};

export const mockFloodRisk: FloodRisk = {
  flood_probability: 82,
  risk_score: 82,
  risk_level: "critical",
  estimate_label: "Prototype AI Risk Estimate",
  recommended_action: "Evacuate remaining low-lying households; boat last-mile only.",
  factors: mockRiskZones[0].contributing_factors ?? [],
};

export const mockCycloneRisk: CycloneRisk = {
  cyclone_risk: 41,
  severity: "moderate",
  affected_region: "Kuttanad / Alappuzha (demo)",
  recommended_action: "Issue precautionary watch; review boat operations.",
  storm_probability: 0.34,
  estimate_label: "Prototype AI Risk Estimate",
};
