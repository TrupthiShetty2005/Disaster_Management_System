import { describe, expect, it } from "vitest";
import { clusterBounds, siteBounds } from "./fire";

describe("fire map bounds", () => {
  it("pads a single-pixel event into a non-degenerate box in [lat, lon] order", () => {
    const b = clusterBounds({ bbox: [74.84, 12.98, 74.84, 12.98] });
    expect(b[0][0]).toBeCloseTo(12.96);
    expect(b[0][1]).toBeCloseTo(74.82);
    expect(b[1][0]).toBeCloseTo(13.0);
    expect(b[1][1]).toBeCloseTo(74.86);
  });

  it("covers the site search radius", () => {
    const [[s, w], [n, e]] = siteBounds({ latitude: 12.9856, longitude: 74.8429, radius_km: 4 });
    expect((n - s) * 110.57).toBeGreaterThan(8);
    expect((e - w) * 111.32 * Math.cos((12.9856 * Math.PI) / 180)).toBeGreaterThan(8);
  });
});
