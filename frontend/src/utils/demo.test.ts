import { describe, expect, it } from "vitest";
import { DEMO_INCIDENT_ID, DEMO_LOCATION_ID } from "../constants/demo";

describe("demo incident identity", () => {
  it("uses the seeded Kuttanad flood UUID", () => {
    expect(DEMO_INCIDENT_ID).toBe("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa");
    expect(DEMO_LOCATION_ID).toBe("11111111-1111-4111-8111-111111111111");
  });
});
