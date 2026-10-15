import { describe, expect, it } from "vitest";
import type { VisionDetection } from "../api/types";
import { groupCounts, groupOf, labelCounts, nearestIndex } from "./vision";

const det = (label: string, confidence: number): VisionDetection => ({ label, confidence, bbox: [0, 0, 1, 1] });

describe("vision helpers", () => {
  const dets = [det("person", 0.9), det("person", 0.3), det("boat", 0.5), det("truck", 0.12), det("airplane", 0.8)];

  it("groups COCO labels", () => {
    expect(groupOf("person")).toBe("people");
    expect(groupOf("bus")).toBe("vehicles");
    expect(groupOf("airplane")).toBe("other");
  });

  it("counts groups at a confidence threshold", () => {
    expect(groupCounts(dets, 0.25)).toEqual({ people: 2, vehicles: 0, boats: 1, animals: 0 });
    expect(groupCounts(dets, 0.1)).toEqual({ people: 2, vehicles: 1, boats: 1, animals: 0 });
    expect(groupCounts(dets, 0.6)).toEqual({ people: 1, vehicles: 0, boats: 0, animals: 0 });
  });

  it("lists label counts in descending order", () => {
    expect(labelCounts(dets, 0.25)).toEqual([
      ["person", 2],
      ["boat", 1],
      ["airplane", 1],
    ]);
  });

  it("finds the nearest timeline sample", () => {
    const times = [0, 0.2, 0.4, 0.6];
    expect(nearestIndex(times, 0.29)).toBe(1);
    expect(nearestIndex(times, 0.31)).toBe(2);
    expect(nearestIndex(times, 5)).toBe(3);
    expect(nearestIndex([], 1)).toBe(-1);
  });
});
