import { describe, expect, it } from "vitest";
import { errorFromResponse } from "./client";

const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status, statusText: "err", headers: { "Content-Type": "application/json" } });

describe("errorFromResponse", () => {
  it("names the failing live source on 503", async () => {
    const err = await errorFromResponse(json(503, { error: "source_unavailable", source: "overpass", detail: "All Overpass mirrors failed" }));
    expect(err.status).toBe(503);
    expect(err.source).toBe("overpass");
    expect(err.message).toBe("overpass unavailable: All Overpass mirrors failed");
  });

  it("uses FastAPI string detail", async () => {
    const err = await errorFromResponse(json(404, { detail: "Unknown station" }));
    expect(err.message).toBe("Unknown station");
  });

  it("summarises validation errors", async () => {
    const err = await errorFromResponse(json(422, { detail: [{ loc: ["query", "lat"], msg: "bad" }] }));
    expect(err.message).toBe("Invalid request parameters");
  });

  it("falls back to the status line for non-JSON bodies", async () => {
    const err = await errorFromResponse(new Response("<html>", { status: 502, statusText: "Bad Gateway" }));
    expect(err.message).toBe("502 Bad Gateway");
  });
});
