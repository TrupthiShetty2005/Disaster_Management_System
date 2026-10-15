import { describe, expect, it } from "vitest";
import type { AnalysisAssets, BuildingAsset } from "../api/types";
import { damageBounds, heightNote, tooltipHtml } from "./damage3d";

const building = (osm_id: string, lon: number, affected: boolean, extra: Partial<BuildingAsset> = {}): GeoJSON.Feature<GeoJSON.Polygon, BuildingAsset> => ({
  type: "Feature",
  geometry: {
    type: "Polygon",
    coordinates: [
      [
        [lon, 15],
        [lon + 0.001, 15],
        [lon + 0.001, 15.001],
        [lon, 15],
      ],
    ],
  },
  properties: {
    osm_id,
    name: null,
    building: "house",
    height_m: 3,
    height_source: "estimated_default",
    levels: null,
    affected,
    damage_class: affected ? "newly_flooded" : "none",
    overlap_pct: affected ? 100 : 0,
    footprint_m2: 120,
    ...extra,
  },
});

const assets: AnalysisAssets = {
  analysis_id: "a",
  status: "complete",
  buildings: {
    type: "FeatureCollection",
    features: [building("way/1", 76.0, true), building("way/2", 76.5, false), building("way/3", 76.1, false, { damage_class: "edge_contact", height_source: "osm_levels", height_m: 6 })],
  },
  lines: { type: "FeatureCollection", features: [] },
  facilities: { type: "FeatureCollection", features: [] },
  summary: {
    buildings_affected: 1,
    buildings_nearby_unaffected: 2,
    buildings_edge_contact: 1,
    buildings_returned: 3,
    buildings_without_outline: 0,
    height_sources: { estimated_default: 2, osm_levels: 1 },
    road_km_affected: 0,
    railway_km_affected: 0,
    power_line_km_affected: 0,
    facilities_affected: 0,
  },
};

describe("3D damage helpers", () => {
  it("frames the camera on affected and edge-contact buildings only", () => {
    expect(damageBounds(assets)).toEqual([
      [76.0, 15],
      [76.101, 15.001],
    ]);
  });

  it("returns null when nothing is affected", () => {
    const none = { ...assets, buildings: { type: "FeatureCollection" as const, features: [building("way/2", 76.5, false)] } };
    expect(damageBounds(none)).toBeNull();
  });

  it("labels estimated heights and escapes OSM strings in tooltips", () => {
    const html = tooltipHtml("building", { ...building("way/9", 76, true).properties, name: "<b>Shop</b>" });
    expect(html).toContain("AFFECTED");
    expect(html).toContain("Estimated");
    expect(html).not.toContain("<b>Shop</b>");
    expect(heightNote(assets)).toBe("1 of 3 building heights from OSM tags; 2 estimated (1 storey × 3 m).");
  });
});
