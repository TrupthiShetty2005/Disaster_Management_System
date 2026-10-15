import { describe, expect, it } from "vitest";
import { DEMO_INCIDENT_ID } from "../constants/demo";
import { sidebarItems } from "./Sidebar";

describe("sidebarItems", () => {
  it("includes the seeded Kuttanad incident only in Demo Mode", () => {
    const demo = sidebarItems(true);
    expect(demo.some((i) => i.to === `/disasters/${DEMO_INCIDENT_ID}`)).toBe(true);
    expect(demo.some((i) => i.label === "Incident command")).toBe(true);
  });

  it("does not invent a Karnataka incident link in REAL DATA mode", () => {
    const live = sidebarItems(false);
    expect(live.some((i) => i.to.includes(DEMO_INCIDENT_ID))).toBe(false);
    expect(live.some((i) => i.label === "Incident command")).toBe(false);
    expect(live[0].to).toBe("/dashboard");
  });

  it("does not add Incident command in REAL DATA even if an id is supplied", () => {
    const liveId = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
    const live = sidebarItems(false, liveId);
    expect(live.some((i) => i.label === "Incident command")).toBe(false);
    expect(live.some((i) => i.to.includes("/disasters/"))).toBe(false);
  });
});
