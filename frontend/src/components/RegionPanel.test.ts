import { describe, expect, it } from "vitest";
import { districtSelectPlaceholder } from "./RegionPanel";

describe("districtSelectPlaceholder", () => {
  it("does not show UNAVAILABLE on initial load", () => {
    expect(districtSelectPlaceholder(true, 0, "")).toBe("Loading districts…");
    expect(districtSelectPlaceholder(true, 0, "")).not.toContain("UNAVAILABLE");
  });

  it("shows select prompt after districts arrive", () => {
    expect(districtSelectPlaceholder(false, 3, "LIVE")).toBe("Select district…");
  });

  it("shows UNAVAILABLE only after a failed request with no districts", () => {
    expect(districtSelectPlaceholder(false, 0, "UNAVAILABLE")).toBe("UNAVAILABLE");
  });
});
