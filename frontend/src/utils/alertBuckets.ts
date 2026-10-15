import type { AlertItem } from "../types/api";

export type AlertBucket = "official" | "heuristic" | "historical";

export function alertBucket(a: AlertItem): AlertBucket {
  if (a.official_warning === true || a.alert_kind === "official_warning") return "official";
  const src = String(a.source || "").toLowerCase();
  if (src === "imd") return "official";
  if (
    a.alert_kind === "heuristic_risk_estimate" ||
    a.provenance_status === "DERIVED_LIVE" ||
    src.includes("heuristic") ||
    src === "alert_engine" ||
    src === "weather_intel"
  ) {
    return "heuristic";
  }
  return "historical";
}

export function partitionAlerts(items: AlertItem[]): Record<AlertBucket, AlertItem[]> {
  return {
    official: items.filter((a) => alertBucket(a) === "official"),
    heuristic: items.filter((a) => alertBucket(a) === "heuristic"),
    historical: items.filter((a) => alertBucket(a) === "historical"),
  };
}
