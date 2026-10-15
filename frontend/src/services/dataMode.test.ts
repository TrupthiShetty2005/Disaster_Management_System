import { describe, expect, it } from "vitest";
import { resolveLocalMock, viteWantsMock } from "./dataMode";

describe("data mode flags", () => {
  it("agrees on REAL DATA: no local mock", () => {
    const r = resolveLocalMock(false, "ok", false);
    expect(r.useLocalMock).toBe(false);
    expect(r.mismatch).toBe(false);
  });

  it("agrees on Demo Mode: local mock allowed", () => {
    const r = resolveLocalMock(true, "ok", true);
    expect(r.useLocalMock).toBe(true);
    expect(r.mismatch).toBe(false);
  });

  it("disagrees when VITE wants mock but backend is REAL DATA: no local mock", () => {
    const r = resolveLocalMock(true, "ok", false);
    expect(r.useLocalMock).toBe(false);
    expect(r.mismatch).toBe(true);
  });

  it("disagrees when VITE is live but backend is Demo: no local mock JSON (use API)", () => {
    const r = resolveLocalMock(false, "ok", true);
    expect(r.useLocalMock).toBe(false);
    expect(r.mismatch).toBe(false);
  });

  it("backend unreachable: never silent mock", () => {
    const withVite = resolveLocalMock(true, "unreachable", null);
    expect(withVite.useLocalMock).toBe(false);
    const pending = resolveLocalMock(true, "pending", null);
    expect(pending.useLocalMock).toBe(false);
  });

  it("treats only the string true as VITE mock", () => {
    expect(viteWantsMock("true")).toBe(true);
    expect(viteWantsMock("false")).toBe(false);
    expect(viteWantsMock(undefined)).toBe(false);
    expect(viteWantsMock("TRUE")).toBe(false);
  });
});
