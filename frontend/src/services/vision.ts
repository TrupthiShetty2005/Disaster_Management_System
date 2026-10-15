import type { VisionResult } from "../types/api";
import { ApiError, apiBase, apiGet, apiUpload, isMockMode } from "./apiClient";

export async function fetchVisionHealth(): Promise<{ name?: string; gpu_required?: boolean; note?: string }> {
  return apiGet("/api/v1/vision/health");
}

export function visionAnalyzeFailure(err: unknown): { unavailable: boolean; message: string } {
  if (err instanceof ApiError && err.status === 503) {
    return {
      unavailable: true,
      message:
        err.message ||
        "Live inference unavailable (HTTP 503). Configure YOLO_WEIGHTS_PATH; DemoVisionModel is Demo Mode only.",
    };
  }
  if (err instanceof Error) {
    const unavailable = /503|YOLO_WEIGHTS|unavailable/i.test(err.message);
    return { unavailable, message: err.message };
  }
  return { unavailable: true, message: "Vision API unavailable" };
}

const demo: VisionResult = {
  image_id: "demo-job",
  model_name: "demo-vision-v0",
  backend: "demo",
  overall_severity: "high",
  processing_time_ms: 12,
  gpu_required: false,
  notes: "Client-side fallback. Start the API for annotated JPEGs.",
  annotated_url: "",
  detections: [
    { label: "person", confidence: 0.86, bbox: [20, 40, 60, 120], severity: "medium", specialized: true },
    { label: "damaged_building", confidence: 0.69, bbox: [80, 20, 160, 90], severity: "high", specialized: true },
    { label: "blocked_road", confidence: 0.72, bbox: [10, 130, 200, 170], severity: "high", specialized: true },
    { label: "vehicle", confidence: 0.81, bbox: [90, 100, 150, 140], severity: "medium", specialized: true },
  ],
  incident: {
    counts: { person: 1, damaged_building: 1, blocked_road: 1, vehicle: 1 },
    headline: "1 person detected; 1 damaged building detected; 1 blocked road detected; 1 vehicle detected",
    recommended_actions: [
      "Mark unsafe; keep public 50 m back pending engineer.",
      "Reroute ambulances; request debris/boat alternative.",
    ],
    severity_rationale: "Demo fallback counts.",
    severity_score: 72,
  },
};

export async function analyzeVision(file: File): Promise<VisionResult> {
  try {
    return await apiUpload("/api/v1/vision/analyze", file);
  } catch (err) {
    if (isMockMode()) return demo;
    throw err;
  }
}

export function annotatedSrc(result: VisionResult): string {
  if (!result.annotated_url) return "";
  if (result.annotated_url.startsWith("http")) return result.annotated_url;
  return `${apiBase()}${result.annotated_url}`;
}
