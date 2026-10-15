import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const pollAlertEvents = vi.fn();
vi.mock("../services/alerts", () => ({ pollAlertEvents: (...args: unknown[]) => pollAlertEvents(...args) }));
vi.mock("../services/apiClient", () => ({ apiBase: () => "http://api", isMockMode: () => false }));

import { useAlertStream } from "./useAlertStream";

class FakeEventSource {
  static last: FakeEventSource | null = null;
  onmessage: (() => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn();
  constructor() {
    FakeEventSource.last = this;
  }
}

describe("useAlertStream", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal("EventSource", FakeEventSource);
    pollAlertEvents.mockReset();
    pollAlertEvents.mockResolvedValue({ items: [{ emitted_at: "t1" }] });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("falls back to polling after the SSE stream drops", async () => {
    const onEvent = vi.fn();
    renderHook(() => useAlertStream(onEvent));
    const es = FakeEventSource.last!;

    es.onmessage?.();
    await vi.advanceTimersByTimeAsync(8000);
    expect(pollAlertEvents).not.toHaveBeenCalled();

    es.onerror?.();
    await vi.advanceTimersByTimeAsync(8000);
    expect(pollAlertEvents).toHaveBeenCalledTimes(1);
    expect(onEvent).toHaveBeenCalledTimes(2);
  });
});
