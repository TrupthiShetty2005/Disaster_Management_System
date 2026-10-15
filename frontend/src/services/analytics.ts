import type { AnalyticsBundle, WeatherHistoryPoint } from "../types/api";
import { mockAnalytics } from "../data/mock";
import { apiGet, apiBase, isMockMode } from "./apiClient";

export interface AnalyticsOverview {
  incident_id: string | null;
  kpis: Record<string, number | string | boolean | Record<string, number> | null>;
  series: {
    labels: string[];
    disaster_frequency: number[];
    risk_trend: number[];
    affected_population: number[];
    resource_utilization: number[];
    flood_expansion: number[];
    alert_severity: Record<string, number>;
    response_performance: number[];
    damage_by_category: Record<string, number>;
  };
  estimate_label: string;
}

type HistoryList = { items: WeatherHistoryPoint[]; total: number };

/** NASA POWER daily rainfall only — never substitute flood-expansion km² as rain. */
export function rainfallSeriesFromHistory(items: WeatherHistoryPoint[] | undefined): {
  rainfallTrend: Array<number | null>;
  rainfallLabels: string[];
  rainfallAvailable: boolean;
  rainfallSource: string;
} {
  const points = items ?? [];
  const dated = points.filter((p) => Boolean(p.observed_at));
  const values = dated.map((p) => (p.rainfall_mm == null ? null : Number(p.rainfall_mm)));
  const hasValue = values.some((v) => v != null && Number.isFinite(v));
  if (!dated.length || !hasValue) {
    return {
      rainfallTrend: [],
      rainfallLabels: [],
      rainfallAvailable: false,
      rainfallSource: "",
    };
  }
  const source = dated.find((p) => p.source)?.source || "nasa-power";
  return {
    rainfallTrend: values,
    rainfallLabels: dated.map((p) => String(p.observed_at).slice(0, 10)),
    rainfallAvailable: true,
    rainfallSource: source,
  };
}

export function seriesLooksMeasured(values: number[] | undefined): boolean {
  if (!values?.length) return false;
  return values.some((v) => typeof v === "number" && Number.isFinite(v) && v !== 0);
}

export function toBundle(ov: AnalyticsOverview): AnalyticsBundle {
  const sev = ov.series.alert_severity;
  const liveUnavailablePop =
    ov.kpis.population_note === "no live census feed" || ov.kpis.data_class === "REAL_DATA";
  const resourcesLive = ov.kpis.rescue_inventory_available === true;
  const floodMeasured = seriesLooksMeasured(ov.series.flood_expansion);
  const popMeasured = !liveUnavailablePop && seriesLooksMeasured(ov.series.affected_population);
  const utilMeasured = resourcesLive && seriesLooksMeasured(ov.series.resource_utilization);
  const sevMix = [sev.INFO ?? 0, sev.WATCH ?? 0, sev.WARNING ?? 0, sev.CRITICAL ?? 0];
  return {
    labels: ov.series.labels,
    riskTrend: ov.series.risk_trend,
    rainfallTrend: [],
    rainfallLabels: [],
    rainfallAvailable: false,
    rainfallSource: "",
    affectedPopulation: ov.series.affected_population,
    resourceUtilization: ov.series.resource_utilization,
    floodAreaTrend: ov.series.flood_expansion,
    severityMix: sevMix,
    populationAvailable: popMeasured,
    resourceUtilizationAvailable: utilMeasured,
    floodAreaAvailable: floodMeasured,
    severityMixAvailable: sevMix.some((n) => n > 0),
  };
}

export async function fetchAnalyticsOverview(params: Record<string, string> = {}): Promise<AnalyticsOverview> {
  const q = new URLSearchParams(params).toString();
  if (isMockMode()) {
    return {
      incident_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      kpis: {
        total_disasters: 3,
        active_disasters: 1,
        affected_population: 42000,
        flooded_area: 34.5,
        damaged_buildings: 1,
        damaged_roads: 1,
        resource_utilization: 40,
        alert_count: 3,
        average_response_time: 18,
        data_class: "SIMULATED",
        population_note: "SIMULATED",
        rescue_inventory_available: true,
      },
      series: {
        labels: mockAnalytics.labels,
        disaster_frequency: [0, 1, 1, 2, 3],
        risk_trend: mockAnalytics.riskTrend.map((n) => n * 100),
        affected_population: mockAnalytics.affectedPopulation,
        resource_utilization: mockAnalytics.resourceUtilization,
        flood_expansion: mockAnalytics.floodAreaTrend ?? [],
        alert_severity: { INFO: 1, WATCH: 0, WARNING: 1, CRITICAL: 1 },
        response_performance: [40, 48, 55, 62, 70],
        damage_by_category: { buildings: 1, roads: 1, flood: 34.5 },
      },
      estimate_label: "Prototype analytics — SIMULATED demo figures, not official statistics",
    };
  }
  return apiGet(`/api/v1/analytics/overview${q ? `?${q}` : ""}`);
}

export async function fetchAnalytics(): Promise<AnalyticsBundle> {
  const ov = await fetchAnalyticsOverview();
  const bundle = toBundle(ov);
  if (isMockMode()) {
    return {
      ...bundle,
      rainfallTrend: mockAnalytics.rainfallTrend,
      rainfallLabels: mockAnalytics.labels,
      rainfallAvailable: true,
      rainfallSource: "mock",
    };
  }
  try {
    const hist = await apiGet<HistoryList>("/api/v1/weather/history");
    const rain = rainfallSeriesFromHistory(hist.items);
    return { ...bundle, ...rain };
  } catch {
    return bundle;
  }
}

export function exportUrl(dataset: string): string {
  return `${apiBase()}/api/v1/exports/${dataset}`;
}
