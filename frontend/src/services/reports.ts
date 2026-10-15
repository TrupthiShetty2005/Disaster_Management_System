import { apiPost, isMockMode } from "./apiClient";
import { DEMO_INCIDENT_ID } from "../constants/demo";

export async function generateReport(kind: string): Promise<{
  kind?: string;
  pdf_available?: boolean;
  incident_id?: string | null;
  region?: string;
  disclaimer?: string;
}> {
  if (isMockMode()) {
    return { kind, incident_id: DEMO_INCIDENT_ID, pdf_available: false, disclaimer: "Prototype" };
  }
  return apiPost("/api/v1/reports/generate", { kind });
}
