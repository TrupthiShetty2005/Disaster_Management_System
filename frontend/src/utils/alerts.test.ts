import { describe, expect, it } from "vitest";
import { partitionAlerts } from "./alertBuckets";
import type { AlertItem } from "../types/api";
import { SAFETY_DISCLAIMER } from "../components/SafetyBanner";
import { normalizeAlertSeverity } from "../components/AlertPanel";

describe("alert stream contract", () => {
  it("keeps prototype disclaimer text", () => {
    expect(SAFETY_DISCLAIMER).toContain("decision-support prototype");
  });

  it("orders critical first via rank helper", () => {
    expect(normalizeAlertSeverity("CRITICAL")).toBe("critical");
    expect(normalizeAlertSeverity("WATCH")).toBe("watch");
  });
});

describe("alert provenance buckets", () => {
  const base = {
    title: "t",
    severity: "WARNING",
    category: "weather",
    message: "m",
    location_id: null,
    issued_at: "2026-10-01T00:00:00Z",
  };
  const items: AlertItem[] = [
    { ...base, id: "o", official_warning: true, alert_kind: "official_warning", source: "imd" },
    { ...base, id: "h", official_warning: false, alert_kind: "heuristic_risk_estimate", provenance_status: "DERIVED_LIVE", source: "visionguard_heuristic" },
    { ...base, id: "p", official_warning: false, provenance_status: "UNKNOWN", source: "engine", status: "RESOLVED" },
  ];
  it("separates official, heuristic, and historical rows", () => {
    const p = partitionAlerts(items);
    expect(p.official.map((a) => a.id)).toEqual(["o"]);
    expect(p.heuristic.map((a) => a.id)).toEqual(["h"]);
    expect(p.historical.map((a) => a.id)).toEqual(["p"]);
  });
});
