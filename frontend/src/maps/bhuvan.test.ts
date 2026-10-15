import { describe, expect, it } from "vitest";
import { BHUVAN_LULC } from "./bhuvan";

describe("Bhuvan LULC overlay", () => {
  it("points at the national 2024–25 land-cover layer, not the Assam flood-hazard service", () => {
    expect(BHUVAN_LULC.layers).toBe("LULC250K_2425");
    expect(BHUVAN_LULC.url).toContain("LULC250K.exe");
    expect(BHUVAN_LULC.url).not.toContain("hazard.exe");
    expect(BHUVAN_LULC.note.toLowerCase()).toContain("not include");
  });
});
