import { describe, expect, it } from "vitest";
import type { AlertItem, FloodEvent } from "../types/api";
import {
  alertPinFeatures,
  bboxToPolygon,
  floodOverlayFeatures,
  isPlottableAlertCoordinate,
  layerCountLegend,
  mergeDashboardCatalog,
} from "./dashboardMap";

const flood: FloodEvent = {
  id: "fl-1",
  model_name: "sentinel-rgb-water-change-v1",
  scene_kind: "sentinel2-change",
  flooded_area: 12,
  flood_percentage: 8,
  severity: "low",
  confidence: 0.4,
  boundary_geojson: null,
  heatmap_geojson: null,
  affected_population: 0,
  affected_roads: 0,
  affected_buildings: 0,
  notes: "",
  created_at: "2026-10-15T00:00:00Z",
  newly_flooded_geojson: {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        properties: {},
        geometry: {
          type: "Polygon",
          coordinates: [
            [
              [77.53, 12.91],
              [77.55, 12.91],
              [77.55, 12.93],
              [77.53, 12.93],
              [77.53, 12.91],
            ],
          ],
        },
      },
    ],
  },
};

describe("dashboard map assembly", () => {
  it("rejects Kerala demo coordinates in live mode", () => {
    expect(isPlottableAlertCoordinate(9.517, 76.522, false)).toBe(false);
    expect(isPlottableAlertCoordinate(9.517, 76.522, true)).toBe(true);
    expect(isPlottableAlertCoordinate(12.9716, 77.5946, false)).toBe(true);
  });

  it("builds flood overlay from newly_flooded_geojson", () => {
    const feats = floodOverlayFeatures(flood);
    expect(feats).toHaveLength(1);
    expect(feats[0].properties.layer).toBe("floodCurrent");
    expect(feats[0].properties.clickAction).toBe("open-flood");
  });

  it("plots official vs heuristic pins and skips Kerala in live", () => {
    const items: AlertItem[] = [
      {
        id: "o",
        title: "IMD",
        severity: "WARNING",
        category: "weather",
        message: "m",
        location_id: null,
        issued_at: "2026-10-01T00:00:00Z",
        latitude: 12.97,
        longitude: 77.59,
        official_warning: true,
        alert_kind: "official_warning",
      },
      {
        id: "h",
        title: "Heuristic",
        severity: "WATCH",
        category: "weather",
        message: "m",
        location_id: null,
        issued_at: "2026-10-01T00:00:00Z",
        latitude: 12.98,
        longitude: 77.6,
        official_warning: false,
        alert_kind: "heuristic_risk_estimate",
      },
      {
        id: "k",
        title: "Kerala leftover",
        severity: "WATCH",
        category: "weather",
        message: "m",
        location_id: null,
        issued_at: "2026-10-01T00:00:00Z",
        latitude: 9.517,
        longitude: 76.522,
        alert_kind: "heuristic_risk_estimate",
      },
    ];
    const pins = alertPinFeatures(items, false);
    expect(pins.map((p) => p.properties.alertId)).toEqual(["o", "h"]);
    expect(pins[0].properties.officialWarning).toBe(true);
    expect(pins[1].properties.officialWarning).toBe(false);
  });

  it("merges flood into OSM catalog and legend counts", () => {
    const catalog = mergeDashboardCatalog({
      osmFeatures: [
        {
          type: "Feature",
          geometry: { type: "Point", coordinates: [77.59, 12.97] },
          properties: { id: "h1", name: "Hospital", layer: "hospitals" },
        },
      ],
      flood,
      alerts: [],
      allowKeralaDemo: false,
    });
    expect(catalog.floodCurrent.features).toHaveLength(1);
    expect(catalog.hospitals.features[0].properties.clickAction).toBe("copy-coords");
    expect(layerCountLegend(catalog)).toContain("flood 1");
    expect(layerCountLegend(catalog)).toContain("hospitals 1");
  });

  it("builds an AOI polygon from bbox", () => {
    const poly = bboxToPolygon([77.53, 12.91, 77.65, 13.03]);
    expect(poly && "type" in poly && poly.type).toBe("Polygon");
  });
});
