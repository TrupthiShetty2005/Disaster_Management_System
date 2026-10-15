import { describe, expect, it } from "vitest";
import { mockFloodRisk } from "../data/mock";

describe("prototype flood estimate", () => {
  it("is labeled and bounded", () => {
    expect(mockFloodRisk.estimate_label).toContain("Prototype");
    expect(mockFloodRisk.flood_probability).toBeGreaterThanOrEqual(0);
    expect(mockFloodRisk.flood_probability).toBeLessThanOrEqual(100);
  });
});
