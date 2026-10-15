import { describe, expect, it } from "vitest";

export function buildingShare(counts: Record<string, number>): number {
  const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1;
  return Math.round((100 * (total - (counts["NO DAMAGE"] ?? 0))) / total);
}

describe("damage stats", () => {
  it("computes damaged building share", () => {
    expect(buildingShare({ "NO DAMAGE": 25, MINOR: 25, MODERATE: 25, SEVERE: 15, DESTROYED: 10 })).toBe(75);
  });
});
