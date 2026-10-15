import { describe, expect, it } from "vitest";
import { dashboardLayerView } from "../pages/DashboardPage";

export function decisionLabel(action: string): string {
  const map: Record<string, string> = { accept: "ACCEPTED", modify: "MODIFIED", reject: "REJECTED" };
  return map[action] ?? action.toUpperCase();
}

describe("rescue override", () => {
  it("maps human override actions", () => {
    expect(decisionLabel("accept")).toBe("ACCEPTED");
    expect(decisionLabel("reject")).toBe("REJECTED");
  });
});

describe("independent rescue inventory views", () => {
  it("does not treat one unavailable feed as a global spinner", () => {
    const resources = dashboardLayerView({ loading: false, error: "no inventory", hasPayload: false });
    const centers = dashboardLayerView({ loading: true, error: null, hasPayload: false });
    const priorities = dashboardLayerView({ loading: false, error: null, hasPayload: true });
    expect(resources).toBe("error");
    expect(centers).toBe("loading");
    expect(priorities).toBe("ready");
  });
});
