import { DataModeBadge, DataSourcePanel, useDataSources } from "./DataModeBadge";

export const SAFETY_DISCLAIMER =
  "VisionGuard AI is a decision-support prototype and does not replace authorized emergency-management decisions.";

export function SafetyBanner({ compact = false }: { compact?: boolean }) {
  const status = useDataSources();
  const demo = Boolean(status?.use_mock_providers || status?.data_mode?.includes("DEMO"));
  return (
    <div className="space-y-2">
      <p
        role="note"
        className={`rounded border ${
          demo ? "border-amber-500/40 bg-amber-500/10 text-amber-100" : "border-emerald-500/40 bg-emerald-500/10 text-emerald-100"
        } ${compact ? "px-2 py-1 text-[11px]" : "p-3 text-sm"}`}
      >
        <span className="mr-2 inline-block align-middle">
          <DataModeBadge compact />
        </span>
        {SAFETY_DISCLAIMER}{" "}
        {demo ? (
          <>
            Explicit <strong>DEMO MODE</strong> — mock/seeded figures are allowed and labeled.
          </>
        ) : (
          <>
            <strong>LIVE DATA MODE</strong> — each module shows its own provenance (LIVE / DERIVED / SEEDED / MOCK).
            VisionGuard risk scores are <strong>not</strong> IMD official warnings unless IMD status is LIVE.
          </>
        )}
      </p>
      {!compact ? <DataSourcePanel compact /> : null}
    </div>
  );
}
