import type { ReactNode } from "react";
import { label, levelColor } from "../lib/format";

export function Card({ title, actions, children, className = "" }: { title?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded border border-line bg-panel ${className}`}>
      {title || actions ? (
        <header className="flex items-center justify-between gap-2 border-b border-line px-3 py-2">
          <h2 className="font-display text-lg tracking-wide text-slate-200">{title}</h2>
          {actions}
        </header>
      ) : null}
      <div className="p-3">{children}</div>
    </section>
  );
}

export function Kpi({ label: name, value, hint, color }: { label: string; value: ReactNode; hint?: ReactNode; color?: string }) {
  return (
    <div className="rounded border border-line bg-panel px-3 py-2">
      <p className="text-[11px] uppercase tracking-wider text-slate-500">{name}</p>
      <p className="font-display text-3xl" style={{ color: color ?? "#e2e8f0" }}>
        {value}
      </p>
      {hint ? <p className="text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}

export function LevelBadge({ level, text }: { level: string | null | undefined; text?: string }) {
  const c = levelColor(level);
  return (
    <span className="inline-block whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-semibold" style={{ color: c, background: `${c}22`, border: `1px solid ${c}55` }}>
      {text ?? label(level)}
    </span>
  );
}

export function Loading({ text = "Fetching live data…" }: { text?: string }) {
  return (
    <p className="animate-pulse text-sm text-slate-500" role="status" aria-live="polite">
      {text}
    </p>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-start justify-between gap-3 rounded border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300" role="alert">
      <span>{message}</span>
      {onRetry ? (
        <button className="btn shrink-0" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="rounded border border-line bg-ink/40 p-3 text-sm text-slate-500">{children}</p>;
}

export function Source({ children }: { children: ReactNode }) {
  return <p className="mt-2 text-[11px] leading-snug text-slate-500">{children}</p>;
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
      <div>
        <h1 className="font-display text-3xl tracking-wide">{title}</h1>
        {subtitle ? <p className="max-w-4xl text-sm text-slate-400">{subtitle}</p> : null}
      </div>
      {actions}
    </div>
  );
}

export function Async<T>({ state, children, loadingText }: { state: { data: T | null; error: string | null; loading: boolean; reload?: () => void }; children: (data: T) => ReactNode; loadingText?: string }) {
  if (state.data) return <>{children(state.data)}</>;
  if (state.error) return <ErrorBox message={state.error} onRetry={state.reload} />;
  return <Loading text={loadingText} />;
}
