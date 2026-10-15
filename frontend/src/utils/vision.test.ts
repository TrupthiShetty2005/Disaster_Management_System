import { describe, expect, it } from "vitest";
import { ApiError } from "../services/apiClient";
import { visionAnalyzeFailure } from "../services/vision";

describe("vision incident counts", () => {
  it("summarizes labels", () => {
    const counts = { person: 4, damaged_building: 7, blocked_road: 2, vehicle: 12 };
    expect(counts.vehicle).toBe(12);
    expect(counts.damaged_building).toBe(7);
  });
});

describe("live vision unavailable", () => {
  it("marks HTTP 503 as unavailable without detections", () => {
    const fail = visionAnalyzeFailure(
      new ApiError("YOLO_WEIGHTS_PATH is not set or missing. DemoVisionModel is only available in Demo Mode.", 503),
    );
    expect(fail.unavailable).toBe(true);
    expect(fail.message).toMatch(/YOLO_WEIGHTS_PATH/);
  });
});
