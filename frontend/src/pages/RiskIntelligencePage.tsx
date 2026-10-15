import { useMemo, useState } from "react";
import { DisasterMap } from "../components/DisasterMap";
import { Breadcrumbs } from "../components/Breadcrumbs";
import { StatusBadge } from "../components/StatusBadge";
import { EstimateCallout } from "../components/EstimateCallout";
import { LoadingState, ErrorState, EmptyState } from "../components/Feedback";
import { useAsync } from "../hooks/useAsync";
import { fetchRiskZones } from "../services/risk";
import { emptyCatalog, fetchGisCatalog } from "../services/gis";
import { fetchAoi } from "../services/region";
import type { GisFeature } from "../types/gis";
import type { RiskZone } from "../types/api";

export function RiskIntelligencePage() {
  const zones = useAsync(fetchRiskZones, []);
  const gis = useAsync(fetchGisCatalog, []);
  const aoi = useAsync(fetchAoi, []);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const items = useMemo(() => zones.data?.items ?? [], [zones.data]);
  const active: RiskZone | undefined = useMemo(
    () => items.find((z) => z.id === selectedId) ?? items[0],
    [items, selectedId],
  );

  if (zones.loading) return <LoadingState />;
  if (zones.error) return <ErrorState message={zones.error} />;
  if (!items.length) return <EmptyState message="No live risk-zone catalog. Seeded demo zones are not shown in REAL DATA mode." />;
  const mapCenter: [number, number] | undefined = aoi.data
    ? [aoi.data.latitude, aoi.data.longitude]
    : undefined;

  return (
    <div className="space-y-3">
      <Breadcrumbs items={[{ to: "/dashboard", label: "Command dashboard" }, { label: "High-risk zone prediction" }]} />
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
      <div className="h-[560px]">
        {gis.error ? <ErrorState message={`OSM GIS: ${gis.error}`} /> : null}
        <DisasterMap
          catalog={gis.data ?? emptyCatalog()}
          center={mapCenter}
          osmUnavailable={Boolean(gis.error)}
          onSelect={(f: GisFeature | null) => {
            if (!f || f.properties.layer !== "risk") return;
            const hit = items.find(
              (z) =>
                (z.name.toLowerCase().includes("polder") && f.properties.riskLevel === "critical") ||
                (z.name.toLowerCase().includes("hill") && f.properties.riskLevel === "high"),
            );
            setSelectedId(hit?.id ?? items[0]?.id ?? null);
          }}
        />
      </div>
      <div className="space-y-3">
        <div className="flex flex-wrap gap-2">
          {items.map((z) => (
            <button
              key={z.id}
              type="button"
              onClick={() => setSelectedId(z.id)}
              className={`rounded border px-2 py-1 text-xs ${active?.id === z.id ? "border-amber-400 text-amber-200" : "border-line text-slate-400"}`}
            >
              {z.name}
            </button>
          ))}
        </div>
        {active ? (
          <section className="rounded border border-line bg-panel p-3">
            <p className="text-[11px] uppercase tracking-widest text-slate-500">{active.estimate_label ?? "Prototype AI Risk Estimate"}</p>
            <h2 className="font-display text-2xl">{active.name}</h2>
            <div className="mt-2 flex items-center gap-2">
              <StatusBadge value={active.risk_level} />
              <span className="text-sm text-slate-300">Score {active.risk_score}</span>
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
              <dt className="text-slate-500">Probability</dt>
              <dd>{active.flood_probability ?? "—"}%</dd>
              <dt className="text-slate-500">Affected population</dt>
              <dd>
                {active.affected_population == null || active.affected_population === 0
                  ? "UNAVAILABLE"
                  : active.affected_population.toLocaleString("en-IN")}
              </dd>
            </dl>
            <p className="mt-3 text-sm text-amber-200">{active.recommended_action}</p>
            <div className="mt-3">
              <EstimateCallout
                title="Flood risk"
                kind={(active.estimate_label || "").includes("SIMULATED") ? "SIMULATED DATA" : "RULE-BASED ESTIMATE"}
                value={`${active.flood_probability ?? "—"}%`}
                factors={(active.contributing_factors ?? []).map((f) => ({ name: f.name, level: f.level }))}
              />
            </div>
          </section>
        ) : null}
        <section className="rounded border border-line bg-panel p-3">
          <h3 className="text-xs uppercase tracking-widest text-slate-500">Why is this area high risk?</h3>
          <ul className="mt-2 space-y-2 text-sm">
            {(active?.contributing_factors ?? []).map((f) => (
              <li key={f.name} className="flex justify-between border-b border-line pb-1">
                <span className="text-slate-300">{f.name}</span>
                <span className="text-slate-400">
                  {f.level} ({f.value})
                </span>
              </li>
            ))}
          </ul>
        </section>
      </div>
      </div>
    </div>
  );
}
