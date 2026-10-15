import { describe, expect, it } from "vitest";
import { polygonAreaKm2 } from "../components/SatelliteOverlayMap";
import { pickBeforeAfter } from "../services/satellite";
import type { SatelliteImageItem } from "../types/api";

function scene(partial: Partial<SatelliteImageItem> & Pick<SatelliteImageItem, "id" | "acquisition_time">): SatelliteImageItem {
  return {
    title: partial.id,
    source: "sentinel-2",
    latitude: 12.82,
    longitude: 75.23,
    bounding_box: { type: "Polygon", coordinates: [] },
    resolution: "10m",
    cloud_cover: 10,
    image_url: "/p",
    thumbnail_url: "/p",
    status: "preview_available",
    provider: "copernicus-stac",
    location_id: "dk",
    metadata: { intersects_selected_aoi: true, footprint_available: true, stac_id: partial.id },
    ...partial,
  };
}

describe("satellite overlay area", () => {
  it("returns a positive area for a polygon", () => {
    const geo = {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          properties: {},
          geometry: {
            type: "Polygon",
            coordinates: [
              [
                [76.5, 9.5],
                [76.54, 9.5],
                [76.54, 9.53],
                [76.5, 9.53],
                [76.5, 9.5],
              ],
            ],
          },
        },
      ],
    } as GeoJSON.GeoJsonObject;
    const area = polygonAreaKm2(geo);
    expect(area).toBeGreaterThan(0);
  });
});

describe("pickBeforeAfter", () => {
  it("uses acquisition dates, not ids containing before/after", () => {
    const items = [
      scene({ id: "sat-flood-after-001", acquisition_time: "2026-05-02T00:00:00Z" }),
      scene({ id: "older-tile", acquisition_time: "2026-05-01T00:00:00Z" }),
      scene({
        id: "outside",
        acquisition_time: "2026-04-01T00:00:00Z",
        metadata: { intersects_selected_aoi: false },
      }),
    ];
    const { before, after } = pickBeforeAfter(items);
    expect(before?.id).toBe("older-tile");
    expect(after?.id).toBe("sat-flood-after-001");
    expect(before?.id).not.toMatch(/before/i);
  });
});
