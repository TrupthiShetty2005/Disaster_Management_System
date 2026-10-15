import { describe, expect, it } from "vitest";
import { popupContent } from "./DisasterMap";
import type { GisFeature } from "../types/gis";

function feature(properties: Record<string, unknown>): GisFeature {
  return {
    type: "Feature",
    geometry: { type: "Point", coordinates: [77.59, 12.97] },
    properties: { id: "f1", layer: "hospitals", ...properties },
  } as GisFeature;
}

describe("popupContent", () => {
  it("renders OSM/alert text as text, never as HTML", () => {
    const el = popupContent(
      feature({
        name: '<img src=x onerror="alert(1)">',
        description: "<script>alert(2)</script>",
        source: "<b>osm</b>",
      }),
    );
    expect(el.querySelector("img, script, b")).toBeNull();
    expect(el.textContent).toContain('<img src=x onerror="alert(1)">');
    expect(el.textContent).toContain("<script>alert(2)</script>");
  });

  it("keeps the original line layout", () => {
    const el = popupContent(
      feature({ name: "City Hospital", feature_type: "hospital", source: "OSM", retrieved_at: "2026-10-16", status: "LIVE" }),
    );
    expect(el.querySelector("strong")?.textContent).toBe("City Hospital");
    expect(el.textContent).toBe("City Hospitalhospitals · hospitalSource: OSMRetrieved 2026-10-16 · LIVE");
    expect(el.querySelectorAll("br")).toHaveLength(3);
  });
});
