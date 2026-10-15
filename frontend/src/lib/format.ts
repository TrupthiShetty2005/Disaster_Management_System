export const LEVEL_COLOR: Record<string, string> = {
  NORMAL: "#34d399",
  CALIBRATING: "#64748b",
  INFO: "#38bdf8",
  WATCH: "#facc15",
  WARNING: "#f97316",
  SEVERE: "#ef4444",
};

export const DANGER_COLOR: Record<string, string> = {
  LOW: "#34d399",
  MODERATE: "#facc15",
  HIGH: "#f97316",
  VERY_HIGH: "#ef4444",
  EXTREME: "#a21caf",
};

export const RAIN_COLOR: Record<string, string> = {
  NO_RAIN: "#1e293b",
  VERY_LIGHT: "#334155",
  LIGHT: "#0ea5e9",
  MODERATE: "#2563eb",
  HEAVY: "#f59e0b",
  VERY_HEAVY: "#f97316",
  EXTREMELY_HEAVY: "#ef4444",
};

export function levelColor(level: string | null | undefined): string {
  return (level && (LEVEL_COLOR[level] ?? DANGER_COLOR[level] ?? RAIN_COLOR[level])) || "#64748b";
}

export function fmt(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toLocaleString("en-IN", { maximumFractionDigits: digits, minimumFractionDigits: 0 });
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(/[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`);
  return d.toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(/[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`);
  const mins = Math.round((Date.now() - d.getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 48) return `${hrs} h ago`;
  return `${Math.round(hrs / 24)} days ago`;
}

export function label(s: string | null | undefined): string {
  return (s ?? "").replace(/_/g, " ").toLowerCase().replace(/^\w/, (c) => c.toUpperCase());
}

export function inr(crore: number | null | undefined): string {
  if (crore === null || crore === undefined) return "—";
  if (crore >= 1) return `₹${fmt(crore, 2)} crore`;
  return `₹${fmt(crore * 100, 1)} lakh`;
}
