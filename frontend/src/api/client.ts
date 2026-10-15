export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public source?: string,
  ) {
    super(message);
  }
}

export async function errorFromResponse(res: Response): Promise<ApiError> {
  let message = `${res.status} ${res.statusText}`;
  let source: string | undefined;
  try {
    const body = (await res.json()) as { detail?: unknown; source?: string; error?: string };
    source = body.source;
    if (typeof body.detail === "string") message = body.detail;
    else if (Array.isArray(body.detail)) message = "Invalid request parameters";
    if (body.error === "source_unavailable" && source) message = `${source} unavailable: ${message}`;
  } catch {
    /* non-JSON error body */
  }
  return new ApiError(message, res.status, source);
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) throw await errorFromResponse(res);
  return (await res.json()) as T;
}

export function apiUrl(path: string): string {
  return `${API_BASE}/api/v1${path}`;
}

export async function apiGet<T>(path: string): Promise<T> {
  return handle<T>(await fetch(apiUrl(path)));
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return handle<T>(
    await fetch(apiUrl(path), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  );
}

export async function apiUpload<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  return handle<T>(await fetch(apiUrl(path), { method: "POST", body: form }));
}

/** Absolute URL for a backend-relative path such as `/api/v1/analyses/{id}/images/after.png`. */
export function assetUrl(path: string): string {
  return path.startsWith("http") ? path : `${API_BASE}${path}`;
}
