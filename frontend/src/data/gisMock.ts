import type { GisCollection, GisFeature } from "../types/gis";

function poly(coords: [number, number][]): GisFeature["geometry"] {
  return { type: "Polygon", coordinates: [[...coords, coords[0]]] };
}

const disasters: GisFeature[] = [
  {
    type: "Feature",
    geometry: { type: "Point", coordinates: [76.522, 9.517] },
    properties: {
      id: "dis-kuttanad",
      name: "Kuttanad inundation (demo)",
      layer: "disasters",
      kind: "flood",
      severity: "high",
      description: "Active flood response in polder belt. Demo incident.",
    },
  },
];

const floodCurrent: GisFeature[] = [
  {
    type: "Feature",
    geometry: poly([
      [76.505, 9.505],
      [76.538, 9.508],
      [76.542, 9.528],
      [76.512, 9.532],
    ]),
    properties: {
      id: "flood-now",
      name: "Current inundation — Polder A",
      layer: "floodCurrent",
      waterLevelM: 1.8,
      affectedPopulation: 18400,
      description: "Observed water (stub analysis). Not a live satellite product.",
    },
  },
];

const floodPredicted: GisFeature[] = [
  {
    type: "Feature",
    geometry: poly([
      [76.498, 9.498],
      [76.548, 9.502],
      [76.552, 9.538],
      [76.502, 9.542],
    ]),
    properties: {
      id: "flood-pred",
      name: "Predicted extent +12h",
      layer: "floodPredicted",
      waterLevelM: 2.3,
      rainfallMm: 62,
      affectedPopulation: 27600,
      description: "Hydrology stub forecast for demo ops.",
    },
  },
];

const risk: GisFeature[] = [
  {
    type: "Feature",
    geometry: poly([
      [76.51, 9.51],
      [76.528, 9.511],
      [76.529, 9.522],
      [76.51, 9.521],
    ]),
    properties: {
      id: "risk-critical",
      name: "Polder A — critical",
      layer: "risk",
      riskLevel: "critical",
      riskScore: 0.92,
      probability: 0.81,
      affectedPopulation: 12000,
      rainfallMm: 48.2,
      waterLevelM: 1.8,
      evacuationRecommendation: "Move remaining households to Community school shelter via boat corridor Delta.",
    },
  },
  {
    type: "Feature",
    geometry: poly([
      [76.528, 9.508],
      [76.545, 9.51],
      [76.546, 9.522],
      [76.53, 9.52],
    ]),
    properties: {
      id: "risk-high",
      name: "Embankment east — high",
      layer: "risk",
      riskLevel: "high",
      riskScore: 0.78,
      probability: 0.64,
      affectedPopulation: 8600,
      rainfallMm: 41,
      waterLevelM: 1.4,
      evacuationRecommendation: "Pre-stage boats; evacuate ground-floor occupancy if water exceeds 1.6 m.",
    },
  },
  {
    type: "Feature",
    geometry: poly([
      [76.5, 9.528],
      [76.518, 9.53],
      [76.52, 9.542],
      [76.502, 9.54],
    ]),
    properties: {
      id: "risk-moderate",
      name: "Canal belt — moderate",
      layer: "risk",
      riskLevel: "moderate",
      riskScore: 0.54,
      probability: 0.41,
      affectedPopulation: 4200,
      rainfallMm: 28,
      waterLevelM: 0.9,
      evacuationRecommendation: "Hold in place; keep access to higher ground open.",
    },
  },
  {
    type: "Feature",
    geometry: poly([
      [76.538, 9.528],
      [76.552, 9.53],
      [76.553, 9.54],
      [76.54, 9.538],
    ]),
    properties: {
      id: "risk-low",
      name: "Ridge hamlet — low",
      layer: "risk",
      riskLevel: "low",
      riskScore: 0.28,
      probability: 0.18,
      affectedPopulation: 900,
      rainfallMm: 18,
      waterLevelM: 0.2,
      evacuationRecommendation: "No movement required. Monitor rainfall watch.",
    },
  },
];

const population: GisFeature[] = [
  {
    type: "Feature",
    geometry: poly([
      [76.512, 9.514],
      [76.522, 9.514],
      [76.522, 9.524],
      [76.512, 9.524],
    ]),
    properties: { id: "pop-1", name: "Ward cluster dense", layer: "population", density: 2100, affectedPopulation: 8400 },
  },
  {
    type: "Feature",
    geometry: poly([
      [76.522, 9.514],
      [76.532, 9.514],
      [76.532, 9.524],
      [76.522, 9.524],
    ]),
    properties: { id: "pop-2", name: "Ward cluster medium", layer: "population", density: 980, affectedPopulation: 3900 },
  },
];

const roads: GisFeature[] = [
  {
    type: "Feature",
    geometry: {
      type: "LineString",
      coordinates: [
        [76.5, 9.512],
        [76.522, 9.518],
        [76.548, 9.516],
      ],
    },
    properties: {
      id: "road-blocked",
      name: "Alappuzha–Changanassery (demo)",
      layer: "roads",
      status: "blocked",
      description: "Inundated carriageway. Boat last-mile preferred.",
    },
  },
  {
    type: "Feature",
    geometry: {
      type: "LineString",
      coordinates: [
        [76.515, 9.5],
        [76.525, 9.535],
      ],
    },
    properties: { id: "bridge-ok", name: "Canal bridge 4 (demo)", layer: "roads", status: "open", kind: "bridge" },
  },
];

const buildings: GisFeature[] = [
  {
    type: "Feature",
    geometry: poly([
      [76.519, 9.515],
      [76.521, 9.515],
      [76.521, 9.517],
      [76.519, 9.517],
    ]),
    properties: { id: "bldg-1", name: "Panchayat hall (demo)", layer: "buildings", status: "minor", kind: "public" },
  },
  {
    type: "Feature",
    geometry: poly([
      [76.526, 9.519],
      [76.5285, 9.519],
      [76.5285, 9.521],
      [76.526, 9.521],
    ]),
    properties: { id: "bldg-2", name: "Dwelling cluster 7", layer: "buildings", status: "moderate", kind: "residential" },
  },
];

const points = (
  layer: GisFeature["properties"]["layer"],
  items: (Omit<GisFeature["properties"], "layer"> & { lon: number; lat: number })[],
): GisFeature[] =>
  items.map(({ lon, lat, ...properties }) => ({
    type: "Feature",
    geometry: { type: "Point", coordinates: [lon, lat] },
    properties: { ...properties, layer },
  }));

const evacuation = points("evacuation", [
  {
    id: "evac-school",
    name: "Community school shelter",
    lon: 76.54,
    lat: 9.508,
    status: "open",
    description: "Capacity 800 · occupied 540",
  },
]);

const rescue = points("rescue", [
  { id: "boat-delta", name: "Boat unit Delta", lon: 76.525, lat: 9.519, status: "deployed", kind: "rescue_boat" },
  { id: "amb-12", name: "Ambulance 12", lon: 76.535, lat: 9.51, status: "staging", kind: "ambulance" },
]);

const hospitals = points("hospitals", [
  { id: "hosp-1", name: "Taluk hospital (demo)", lon: 76.548, lat: 9.502, status: "operational", kind: "hospital" },
]);

const shelters = points("shelters", [
  { id: "shelter-church", name: "Parish hall shelter", lon: 76.512, lat: 9.498, status: "open", kind: "shelter" },
]);

export const gisCatalog: Record<string, GisCollection> = {
  alerts: { type: "FeatureCollection", features: [] },
  disasters: { type: "FeatureCollection", features: disasters },
  floodCurrent: { type: "FeatureCollection", features: floodCurrent },
  floodPredicted: { type: "FeatureCollection", features: floodPredicted },
  risk: { type: "FeatureCollection", features: risk },
  population: { type: "FeatureCollection", features: population },
  roads: { type: "FeatureCollection", features: roads },
  buildings: { type: "FeatureCollection", features: buildings },
  evacuation: { type: "FeatureCollection", features: evacuation },
  rescue: { type: "FeatureCollection", features: rescue },
  hospitals: { type: "FeatureCollection", features: hospitals },
  shelters: { type: "FeatureCollection", features: shelters },
};

export function allGisFeatures(): GisFeature[] {
  return Object.values(gisCatalog).flatMap((c) => c.features);
}
