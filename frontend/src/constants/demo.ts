/** Demo-mode incident IDs only (backend seed). Not shown as live operations. */
export const DEMO_INCIDENT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
export const DEMO_LOCATION_ID = "11111111-1111-4111-8111-111111111111";
export const DEMO_REGION = "Kuttanad Wetlands (demo)";
export const DEMO_INCIDENT_TITLE = "Kuttanad monsoon inundation (demo)";

/** Live AOI — Karnataka, India (primary region). */
export const LIVE_REGION = "Karnataka / Bengaluru (India)";
export const LIVE_WEATHER_QUERY = "Bengaluru,IN";
export const LIVE_MAP_CENTER: [number, number] = [12.9716, 77.5946];

/** Simulated figures for explicit Demo Mode only — never used on live operational screens. */
export const DEMO_STATS = {
  floodRiskPct: 82,
  floodedKm2: 34.5,
  affectedPopulation: 42000,
  damagedBuildings: 18,
  blockedRoads: 3,
  dataClass: "SIMULATED" as const,
};
