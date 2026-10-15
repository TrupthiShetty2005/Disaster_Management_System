import { describe, expect, it } from "vitest";
import { dashboardLayerView } from "./DashboardPage";

describe("dashboardLayerView", () => {
  it("shows loading only while pending, not empty", () => {
    expect(dashboardLayerView({ loading: true, error: null, hasPayload: false })).toBe("loading");
  });

  it("shows empty after a successful response with no records", () => {
    expect(dashboardLayerView({ loading: false, error: null, hasPayload: false })).toBe("empty");
  });

  it("shows error after a failed request, distinct from empty", () => {
    expect(dashboardLayerView({ loading: false, error: "timeout", hasPayload: false })).toBe("error");
  });

  it("shows ready when a payload exists", () => {
    expect(dashboardLayerView({ loading: false, error: null, hasPayload: true })).toBe("ready");
  });

  it("keeps weather/satellite/GIS states independent", () => {
    const weather = dashboardLayerView({ loading: false, error: "wx fail", hasPayload: false });
    const satellite = dashboardLayerView({ loading: true, error: null, hasPayload: false });
    const gis = dashboardLayerView({ loading: false, error: null, hasPayload: true });
    expect(weather).toBe("error");
    expect(satellite).toBe("loading");
    expect(gis).toBe("ready");
  });
});
