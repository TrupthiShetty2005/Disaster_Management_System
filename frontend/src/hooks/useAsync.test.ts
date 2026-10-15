import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useAsync } from "./useAsync";

describe("useAsync", () => {
  it("starts in loading with no error and no data", () => {
    const { result } = renderHook(() => useAsync(() => new Promise<string>(() => {}), []));
    expect(result.current.loading).toBe(true);
    expect(result.current.error).toBeNull();
    expect(result.current.data).toBeNull();
  });

  it("stores data on success", async () => {
    const { result } = renderHook(() => useAsync(async () => ({ items: [] as string[] }), []));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBeNull();
    expect(result.current.data).toEqual({ items: [] });
  });

  it("stores error on failure without inventing data", async () => {
    const { result } = renderHook(() =>
      useAsync(async () => {
        throw new Error("provider down");
      }, []),
    );
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe("provider down");
    expect(result.current.data).toBeNull();
  });

  it("clears error when a new request starts", async () => {
    let fail = true;
    const { result, rerender } = renderHook(
      ({ n }: { n: number }) =>
        useAsync(async () => {
          if (fail) throw new Error("boom");
          return "ok";
        }, [n]),
      { initialProps: { n: 0 } },
    );
    await waitFor(() => expect(result.current.error).toBe("boom"));
    fail = false;
    await act(async () => {
      rerender({ n: 1 });
    });
    await waitFor(() => expect(result.current.data).toBe("ok"));
    expect(result.current.error).toBeNull();
    expect(result.current.loading).toBe(false);
  });
});
