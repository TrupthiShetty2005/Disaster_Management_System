/** Backend `/api/v1/health` is the source of truth for REAL DATA vs Demo Mode. No secrets. */

export type ConnectionState = "pending" | "ok" | "unreachable";

export type ModeSnapshot = {
  connection: ConnectionState;
  backendUseMock: boolean | null;
  dataMode: string | null;
  mismatch: boolean;
};

export type HealthMode = {
  use_mock_providers: boolean;
  data_mode: string;
};

const EMPTY: ModeSnapshot = {
  connection: "pending",
  backendUseMock: null,
  dataMode: null,
  mismatch: false,
};

let snapshot: ModeSnapshot = { ...EMPTY };

export function viteWantsMock(viteValue: string | boolean | undefined = import.meta.env.VITE_USE_MOCK): boolean {
  return viteValue === true || viteValue === "true";
}

/**
 * Local mock JSON is allowed only when BOTH flags explicitly enable Demo Mode
 * AND the backend was reached. Unreachable backend never falls back to mock.
 */
export function resolveLocalMock(
  viteUseMock: boolean,
  connection: ConnectionState,
  backendUseMock: boolean | null,
): { useLocalMock: boolean; mismatch: boolean; connection: ConnectionState } {
  if (connection !== "ok" || backendUseMock == null) {
    return { useLocalMock: false, mismatch: false, connection };
  }
  const mismatch = viteUseMock && backendUseMock === false;
  const useLocalMock = viteUseMock && backendUseMock === true;
  return { useLocalMock, mismatch, connection };
}

export function applyHealth(health: HealthMode | null, unreachable: boolean, viteUseMock = viteWantsMock()): ModeSnapshot {
  if (unreachable) {
    snapshot = { connection: "unreachable", backendUseMock: null, dataMode: null, mismatch: false };
    return getModeSnapshot();
  }
  const backendUseMock = Boolean(health?.use_mock_providers);
  const resolved = resolveLocalMock(viteUseMock, "ok", backendUseMock);
  snapshot = {
    connection: "ok",
    backendUseMock,
    dataMode: health?.data_mode ?? (backendUseMock ? "DEMO DATA" : "REAL DATA"),
    mismatch: resolved.mismatch,
  };
  return getModeSnapshot();
}

export function resetDataModeForTests(): void {
  snapshot = { ...EMPTY };
}

export function getModeSnapshot(): ModeSnapshot {
  return { ...snapshot };
}

export function isBackendUnreachable(): boolean {
  return snapshot.connection === "unreachable";
}

export function backendIsDemoMode(): boolean {
  return snapshot.connection === "ok" && snapshot.backendUseMock === true;
}
