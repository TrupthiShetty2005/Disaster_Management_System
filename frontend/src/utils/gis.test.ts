import { describe, expect, it } from "vitest";
import { DEFAULT_LAYER_VISIBILITY, LAYER_LABELS, searchFeatures, showMapLayerToggle, toggleLayer } from "../types/gis";
import { activeBasemapLabel, IMAGERY_BASEMAP } from "../maps/basemap";
import { filterAlerts, normalizeAlertSeverity } from "../components/AlertPanel";
import type { AlertItem } from "../types/api";
import { catalogFromOverpass, emptyCatalog } from "../services/gis";
import { allGisFeatures } from "../data/gisMock";

describe("GIS layer helpers", () => {
  it("toggles a layer without mutating others", () => {
    const next = toggleLayer(DEFAULT_LAYER_VISIBILITY, "population");
    expect(next.population).toBe(!DEFAULT_LAYER_VISIBILITY.population);
    expect(next.floodCurrent).toBe(DEFAULT_LAYER_VISIBILITY.floodCurrent);
  });

  it("searches named features", () => {
    const hits = searchFeatures(allGisFeatures(), "polder");
    expect(hits.length).toBeGreaterThan(0);
    expect(hits[0].properties.name.toLowerCase()).toContain("polder");
  });

  it("maps OSM Overpass layers without fabricating extras", () => {
    const catalog = catalogFromOverpass([
      {
        type: "Feature",
        geometry: { type: "LineString", coordinates: [[77.59, 12.97], [77.6, 12.98]] },
        properties: { id: "osm-way-1", name: "MG Road", layer: "roads" as const },
      },
    ]);
    expect(catalog.roads.features).toHaveLength(1);
    expect(emptyCatalog().hospitals.features).toHaveLength(0);
    expect(catalog.shelters.features).toHaveLength(0);
    expect(catalog.rescue.features).toHaveLength(0);
    expect(catalog.evacuation.features).toHaveLength(0);
  });

  it("does not treat OSM fire stations as live rescue inventory", () => {
    const catalog = catalogFromOverpass([
      {
        type: "Feature",
        geometry: { type: "Point", coordinates: [75.23, 12.82] },
        properties: { id: "osm-fire-1", name: "Fire station", layer: "fire" as never },
      },
    ]);
    expect(catalog.rescue.features).toHaveLength(0);
  });

  it("hides empty live inventory toggles and does not claim demo satellite tiles", () => {
    expect(LAYER_LABELS.satellite.toLowerCase()).not.toContain("demo tiles");
    expect(LAYER_LABELS.satellite).toContain("Esri World Imagery");
    expect(activeBasemapLabel(true)).toBe(IMAGERY_BASEMAP.label);
    expect(showMapLayerToggle("rescue", true, 0)).toBe(false);
    expect(showMapLayerToggle("evacuation", true, 0)).toBe(false);
    expect(showMapLayerToggle("rescue", false, 0)).toBe(false);
    expect(showMapLayerToggle("roads", true, 0)).toBe(false);
    expect(showMapLayerToggle("roads", true, 4)).toBe(true);
    expect(showMapLayerToggle("satellite", true, 0)).toBe(true);
    expect(showMapLayerToggle("population", true, 0)).toBe(false);
    expect(showMapLayerToggle("floodPredicted", true, 0)).toBe(false);
    expect(showMapLayerToggle("roads", true, 0, true)).toBe(false);
    expect(showMapLayerToggle("hospitals", true, 2, true)).toBe(false);
  });
});

describe("alert filters", () => {
  const items: AlertItem[] = [
    { id: "1", title: "c", severity: "critical", category: "x", message: "", location_id: null, issued_at: "" },
    { id: "2", title: "w", severity: "warning", category: "x", message: "", location_id: null, issued_at: "" },
    { id: "3", title: "i", severity: "info", category: "x", message: "", location_id: null, issued_at: "" },
  ];

  it("normalizes severity", () => {
    expect(normalizeAlertSeverity("severe")).toBe("critical");
    expect(normalizeAlertSeverity("medium")).toBe("watch");
  });

  it("filters by bucket", () => {
    expect(filterAlerts(items, "critical")).toHaveLength(1);
    expect(filterAlerts(items, "all")).toHaveLength(3);
  });
});
