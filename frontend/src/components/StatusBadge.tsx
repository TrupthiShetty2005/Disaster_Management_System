const tone: Record<string, string> = {
  high: "bg-danger/20 text-red-300",
  severe: "bg-danger/30 text-red-200",
  critical: "bg-danger/30 text-red-200",
  medium: "bg-warn/20 text-amber-300",
  moderate: "bg-warn/20 text-amber-300",
  warning: "bg-warn/20 text-amber-300",
  watch: "bg-amber-500/15 text-amber-200",
  low: "bg-ok/20 text-emerald-300",
  info: "bg-sky-500/20 text-sky-300",
  deployed: "bg-ok/20 text-emerald-300",
  available: "bg-ok/20 text-emerald-300",
  busy: "bg-warn/20 text-amber-300",
  maintenance: "bg-slate-700 text-slate-300",
  blocked: "bg-danger/20 text-red-300",
  pending: "bg-sky-500/20 text-sky-300",
  accepted: "bg-ok/20 text-emerald-300",
  modified: "bg-warn/20 text-amber-300",
  rejected: "bg-danger/20 text-red-300",
  acknowledged: "bg-sky-500/20 text-sky-300",
  active: "bg-amber-500/20 text-amber-200",
  resolved: "bg-ok/20 text-emerald-300",
};

export function StatusBadge({ value }: { value: string }) {
  const key = value.toLowerCase().replace(/_/g, " ").trim();
  const cls = tone[key] ?? tone[key.replace(" ", "")] ?? "bg-slate-700 text-slate-300";
  return (
    <span className={`rounded px-2 py-0.5 text-[11px] uppercase tracking-wide ${cls}`}>{value}</span>
  );
}
