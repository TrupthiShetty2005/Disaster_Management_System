import { useEffect, useState } from "react";
import { apiGet, isMockMode } from "../services/apiClient";
import { backendIsDemoMode, getModeSnapshot, isBackendUnreachable } from "../services/dataMode";

export type ProvenanceStatus =
  | "LIVE"
  | "DERIVED_LIVE"
  | "STATIC_EXTERNAL"
  | "SEEDED"
  | "MOCK"
  | "UNAVAILABLE"
  | "NOT_CONFIGURED";

export type ModuleStatus = {
  source?: string;
  category?: string;
  status: ProvenanceStatus | string;
  provider: string;
  description: string;
  is_live?: boolean;
  is_mock?: boolean;
  is_seeded?: boolean;
  last_updated?: string | null;
  method?: string | null;
  limitations?: string | null;
};

export type DataSourcesStatus = {
  data_mode: string;
  use_mock_providers: boolean;
  checked_at?: string;
  summary?: Record<string, number>;
  modules?: Record<string, ModuleStatus>;
  openweather?: { configured?: boolean; active?: boolean; note?: string; status?: string; query?: string };
  nasa_power?: { configured?: boolean; active?: boolean; note?: string; status?: string };
  imd?: { configured?: boolean; available?: boolean; note?: string; status?: string };
  copernicus?: { available?: boolean; note?: string; status?: string; scene_count?: number };
};

const STATUS_STYLE: Record<string, string> = {
  LIVE: "border-emerald-500/50 bg-emerald-500/10 text-emerald-200",
  DERIVED_LIVE: "border-amber-400/50 bg-amber-400/10 text-amber-100",
  STATIC_EXTERNAL: "border-sky-500/50 bg-sky-500/10 text-sky-200",
  SEEDED: "border-orange-500/50 bg-orange-500/10 text-orange-200",
  MOCK: "border-rose-500/50 bg-rose-500/10 text-rose-200",
  UNAVAILABLE: "border-slate-500/50 bg-slate-500/10 text-slate-300",
  NOT_CONFIGURED: "border-slate-600/50 bg-slate-800 text-slate-400",
};

const STATUS_DOT: Record<string, string> = {
  LIVE: "bg-emerald-400",
  DERIVED_LIVE: "bg-amber-300",
  STATIC_EXTERNAL: "bg-sky-400",
  SEEDED: "bg-orange-400",
  MOCK: "bg-rose-400",
  UNAVAILABLE: "bg-slate-400",
  NOT_CONFIGURED: "bg-slate-600",
};

const STATUS_LABEL: Record<string, string> = {
  LIVE: "LIVE DATA",
  DERIVED_LIVE: "DERIVED FROM LIVE DATA",
  STATIC_EXTERNAL: "STATIC EXTERNAL DATA",
  SEEDED: "SEEDED DATA",
  MOCK: "MOCK DATA",
  UNAVAILABLE: "UNAVAILABLE",
  NOT_CONFIGURED: "NOT CONFIGURED",
};

export function statusLabel(status: string): string {
  return STATUS_LABEL[status] || status;
}

export function useDataSources() {
  const [status, setStatus] = useState<DataSourcesStatus | null>(null);

  useEffect(() => {
    if (isBackendUnreachable()) {
      setStatus({
        data_mode: "UNAVAILABLE",
        use_mock_providers: false,
        openweather: { note: "Backend unreachable. Mock JSON was not used.", status: "UNAVAILABLE" },
        modules: {
          weather: {
            status: "UNAVAILABLE",
            provider: "unknown",
            description: "Backend unreachable — UI did not fall back to local mock data.",
          },
        },
      });
      return;
    }
    if (isMockMode()) {
      setStatus({
        data_mode: "DEMO DATA",
        use_mock_providers: true,
        modules: {
          weather: {
            status: "MOCK",
            provider: "frontend mock.ts",
            description: "Explicit Demo Mode (backend USE_MOCK_PROVIDERS=true and VITE_USE_MOCK=true).",
            is_mock: true,
          },
        },
      });
      return;
    }
    let cancelled = false;
    apiGet<DataSourcesStatus>("/api/v1/data-sources/status?probe=true")
      .then((data) => {
        if (!cancelled) setStatus(data);
      })
      .catch(() => {
        if (!cancelled) {
          setStatus({
            data_mode: "UNAVAILABLE",
            use_mock_providers: false,
            openweather: { note: "Could not reach /api/v1/data-sources/status.", status: "UNAVAILABLE" },
            modules: {
              weather: {
                status: "UNAVAILABLE",
                provider: "unknown",
                description: "Backend data-sources endpoint unreachable.",
              },
            },
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return status;
}

export function DataModeBadge({ compact = false }: { compact?: boolean }) {
  const status = useDataSources();
  const snap = getModeSnapshot();
  if (!status) {
    return (
      <span className={`inline-flex items-center gap-1 rounded border border-line px-2 py-1 text-slate-400 ${compact ? "text-[10px]" : "text-xs"}`}>
        …
      </span>
    );
  }
  if (snap.connection === "unreachable") {
    return (
      <span
        title="API not reachable. Local mock JSON is disabled."
        className={`inline-flex items-center gap-1 rounded border border-rose-500/40 bg-rose-500/10 px-2 py-1 font-medium text-rose-200 ${compact ? "text-[10px]" : "text-xs"}`}
      >
        <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-rose-400" />
        BACKEND UNAVAILABLE
      </span>
    );
  }
  const demo = Boolean(status.use_mock_providers) || backendIsDemoMode() || status.data_mode === "DEMO DATA";
  const label = demo ? "DEMO MODE" : "LIVE DATA MODE";
  return (
    <span
      title={
        snap.mismatch
          ? "VITE_USE_MOCK=true ignored — backend reports REAL DATA. Calling the API, not local mock JSON."
          : demo
            ? "Explicit Demo Mode — mocks allowed"
            : "LIVE DATA MODE — module badges show per-source truth"
      }
      className={`inline-flex items-center gap-1 rounded border px-2 py-1 font-medium ${
        demo ? "border-amber-500/40 bg-amber-500/10 text-amber-200" : "border-emerald-500/40 bg-emerald-500/10 text-emerald-200"
      } ${compact ? "text-[10px]" : "text-xs"}`}
    >
      <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${demo ? "bg-amber-400" : "bg-emerald-400"}`} />
      {label}
      {snap.mismatch ? <span className="text-[10px] text-amber-100">· VITE_USE_MOCK ignored</span> : null}
    </span>
  );
}

export function DataSourceBadge({
  status,
  provider,
  compact = false,
}: {
  status: string;
  provider?: string;
  compact?: boolean;
}) {
  const style = STATUS_STYLE[status] || STATUS_STYLE.NOT_CONFIGURED;
  const dot = STATUS_DOT[status] || STATUS_DOT.NOT_CONFIGURED;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 font-medium ${style} ${compact ? "text-[10px]" : "text-xs"}`}
      title={provider || status}
    >
      <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${dot}`} />
      {statusLabel(status)}
      {provider && !compact ? <span className="text-[10px] opacity-80">· {provider}</span> : null}
    </span>
  );
}

export function ModuleProvenance({
  moduleKey,
  title,
}: {
  moduleKey: string;
  title?: string;
}) {
  const status = useDataSources();
  const mod = status?.modules?.[moduleKey];
  const [open, setOpen] = useState(false);
  if (!mod) {
    return (
      <div className="rounded border border-line bg-panel/60 px-3 py-2 text-xs text-slate-500">
        {title || moduleKey}: provenance loading…
      </div>
    );
  }
  return (
    <div className="rounded border border-line bg-panel/60 px-3 py-2 text-xs">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-slate-200">{title || moduleKey}</span>
          <DataSourceBadge status={mod.status} provider={mod.provider} />
        </div>
        <button type="button" className="text-sky-300" onClick={() => setOpen((v) => !v)}>
          {open ? "Hide why" : "Why this data?"}
        </button>
      </div>
      {open ? (
        <dl className="mt-2 space-y-1 text-slate-400">
          <div className="flex justify-between gap-2">
            <dt>Provider</dt>
            <dd className="text-slate-300">{mod.provider}</dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt>Status</dt>
            <dd className="text-slate-300">{statusLabel(mod.status)}</dd>
          </div>
          {mod.last_updated ? (
            <div className="flex justify-between gap-2">
              <dt>Checked</dt>
              <dd className="text-slate-300">{mod.last_updated}</dd>
            </div>
          ) : null}
          {mod.method ? (
            <div className="flex justify-between gap-2">
              <dt>Method</dt>
              <dd className="text-right text-slate-300">{mod.method}</dd>
            </div>
          ) : null}
          <p className="pt-1 text-slate-500">{mod.description}</p>
          {mod.limitations ? <p className="text-amber-200/80">Limitations: {mod.limitations}</p> : null}
        </dl>
      ) : (
        <p className="mt-1 text-slate-500">{mod.description}</p>
      )}
    </div>
  );
}

export function DataSourcePanel({ compact = false }: { compact?: boolean }) {
  const status = useDataSources();
  if (!status?.modules) return null;
  const keys = [
    "weather",
    "weather_history",
    "satellite",
    "flood_analysis",
    "imd",
    "gis",
    "resources",
    "alerts",
    "notifications",
    "vision",
  ];
  return (
    <div className={`rounded border border-line bg-panel ${compact ? "p-2" : "p-3"}`}>
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-[11px] uppercase tracking-widest text-slate-500">Data provenance</p>
        <DataModeBadge compact />
      </div>
      <ul className="grid gap-1 sm:grid-cols-2 lg:grid-cols-3">
        {keys.map((key) => {
          const mod = status.modules?.[key];
          if (!mod) return null;
          return (
            <li key={key} className="flex items-center justify-between gap-2 rounded border border-line/60 px-2 py-1 text-[11px]">
              <span className="capitalize text-slate-400">{key.replace(/_/g, " ")}</span>
              <DataSourceBadge status={mod.status} compact />
            </li>
          );
        })}
      </ul>
    </div>
  );
}
