import { getModeSnapshot, resolveLocalMock, viteWantsMock } from "./dataMode";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function raiseIfNeeded(res: Response): Promise<void> {
  if (res.ok) return;
  let detail = res.statusText;
  try {
    const body = (await res.json()) as { detail?: unknown };
    const raw = body.detail;
    if (typeof raw === "string") detail = raw;
    else if (Array.isArray(raw)) {
      detail = raw
        .map((item: unknown) => (typeof item === "string" ? item : "Invalid request"))
        .join("; ");
    } else if (raw && typeof raw === "object") {
      detail = "Request failed validation";
    }
  } catch {
    /* ignore */
  }
  throw new ApiError(detail, res.status);
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  await raiseIfNeeded(res);
  return (await res.json()) as T;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  await raiseIfNeeded(res);
  return (await res.json()) as T;
}

export async function apiUpload<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}${path}`, { method: "POST", body: form });
  await raiseIfNeeded(res);
  return (await res.json()) as T;
}

export function apiBase(): string {
  return BASE;
}

export function isMockMode(): boolean {
  const snap = getModeSnapshot();
  return resolveLocalMock(viteWantsMock(), snap.connection, snap.backendUseMock).useLocalMock;
}
