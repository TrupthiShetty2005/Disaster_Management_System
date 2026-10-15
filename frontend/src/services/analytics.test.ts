import { describe, expect, it } from "vitest";
import { rainfallSeriesFromHistory, toBundle, type AnalyticsOverview } from "./analytics";

const overview: AnalyticsOverview = {
  incident_id: null,
  kpis: { data_class: "REAL_DATA", population_note: "no live census feed", rescue_inventory_available: false },
  series: {
    labels: ["T-4d", "Now"],
    disaster_frequency: [0, 0],
    risk_trend: [1, 2],
    affected_population: [0, 0],
    resource_utilization: [0, 0],
    flood_expansion: [0, 12.5],
    alert_severity: { INFO: 0, WATCH: 0, WARNING: 0, CRITICAL: 0 },
    response_performance: [0, 0],
    damage_by_category: {},
  },
  estimate_label: "live",
};

describe("dashboard rainfall vs flood series", () => {
  it("does not copy flood-expansion km² into rainfallTrend", () => {
    const bundle = toBundle(overview);
    expect(bundle.floodAreaTrend).toEqual([0, 12.5]);
    expect(bundle.rainfallTrend).toEqual([]);
    expect(bundle.rainfallAvailable).toBe(false);
    expect(bundle.populationAvailable).toBe(false);
    expect(bundle.resourceUtilizationAvailable).toBe(false);
  });

  it("uses NASA POWER rainfall only when dates and non-fill values exist", () => {
    const rain = rainfallSeriesFromHistory([
      {
        observed_at: "2026-10-01T00:00:00Z",
        rainfall_mm: null,
        temperature_c: 26,
        humidity: 70,
        wind_speed_ms: 2,
        river_level_m: null,
        source: "nasa-power",
      },
      {
        observed_at: "2026-10-02T00:00:00Z",
        rainfall_mm: 8.5,
        temperature_c: 25,
        humidity: null,
        wind_speed_ms: 2.1,
        river_level_m: null,
        source: "nasa-power",
      },
    ]);
    expect(rain.rainfallAvailable).toBe(true);
    expect(rain.rainfallSource).toBe("nasa-power");
    expect(rain.rainfallLabels).toEqual(["2026-10-01", "2026-10-02"]);
    expect(rain.rainfallTrend).toEqual([null, 8.5]);
  });

  it("marks rainfall unavailable when every PRECTOTCORR value is missing", () => {
    const rain = rainfallSeriesFromHistory([
      {
        observed_at: "2026-10-01T00:00:00Z",
        rainfall_mm: null,
        temperature_c: 26,
        humidity: 70,
        wind_speed_ms: 2,
        river_level_m: null,
        source: "nasa-power",
      },
    ]);
    expect(rain.rainfallAvailable).toBe(false);
    expect(rain.rainfallTrend).toEqual([]);
  });
});
