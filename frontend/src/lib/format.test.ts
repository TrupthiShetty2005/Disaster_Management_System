import { describe, expect, it } from "vitest";
import { fmt, inr, label, levelColor } from "./format";

describe("format helpers", () => {
  it("renders missing numbers as a dash, never zero", () => {
    expect(fmt(null)).toBe("—");
    expect(fmt(undefined)).toBe("—");
    expect(fmt(Number.NaN)).toBe("—");
    expect(fmt(0)).toBe("0");
  });

  it("formats Indian-grouped numbers", () => {
    expect(fmt(1234567)).toBe("12,34,567");
    expect(fmt(3.14159, 2)).toBe("3.14");
  });

  it("expresses rupee losses in crore or lakh", () => {
    expect(inr(2.5)).toBe("₹2.5 crore");
    expect(inr(0.31)).toBe("₹31 lakh");
    expect(inr(null)).toBe("—");
  });

  it("maps levels to colours with a neutral fallback", () => {
    expect(levelColor("SEVERE")).toBe("#ef4444");
    expect(levelColor("EXTREME")).toBe("#a21caf");
    expect(levelColor("HEAVY")).toBe("#f59e0b");
    expect(levelColor("unknown")).toBe("#64748b");
  });

  it("humanises enum labels", () => {
    expect(label("VERY_HEAVY")).toBe("Very heavy");
    expect(label("fire_station")).toBe("Fire station");
  });
});
