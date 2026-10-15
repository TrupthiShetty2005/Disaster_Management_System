import type { Impact } from "../api/types";
import { fmt, inr, label } from "../lib/format";
import { Empty, ErrorBox, Kpi, Source } from "./ui";

const ASSET_LABEL: Record<string, string> = {
  buildings: "Buildings",
  major_roads: "Major roads",
  minor_roads: "Minor roads",
  railways: "Railways",
  power_lines: "Power lines",
};

export function ImpactSummary({ impact }: { impact: Impact | null | undefined }) {
  if (!impact) return <Empty>No impact assessment recorded.</Empty>;
  if (impact.status === "no_hazard_footprint") return <Empty>No hazard footprint was detected, so no infrastructure is exposed.</Empty>;
  if (impact.status === "osm_unavailable") return <ErrorBox message={`OpenStreetMap infrastructure could not be fetched: ${impact.detail ?? "Overpass unavailable"}`} />;
  const e = impact.exposed!;
  const loss = impact.loss!;
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <Kpi label="Hazard footprint" value={`${fmt(impact.hazard_area_km2, 2)} km²`} hint={label(impact.hazard_type)} />
        <Kpi label="Buildings exposed" value={fmt(e.buildings)} hint={`of ${fmt(e.buildings_in_search_area)} mapped nearby`} color="#f97316" />
        <Kpi label="Roads exposed" value={`${fmt(e.road_km, 1)} km`} hint={`${fmt(e.major_road_km, 1)} km major · rail ${fmt(e.railway_km, 1)} km · power ${fmt(e.power_line_km, 1)} km`} color="#facc15" />
        <Kpi label="Estimated loss" value={inr(loss.estimated_loss_crore)} hint={`${Math.round(loss.damage_ratio * 100)}% damage of ${inr(loss.exposed_replacement_value / 1e7)} exposed`} color="#ef4444" />
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <table className="w-full text-xs">
          <thead className="text-left text-slate-500">
            <tr>
              <th>Asset</th>
              <th className="text-right">Estimated loss</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(loss.by_asset).map(([k, v]) => (
              <tr key={k} className="border-t border-line/50">
                <td className="py-1 text-slate-300">{ASSET_LABEL[k] ?? label(k)}</td>
                <td className="text-right text-slate-200">{inr(v / 1e7)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="text-xs">
          <p className="mb-1 text-slate-500">Critical facilities inside footprint</p>
          {impact.facilities && impact.facilities.length ? (
            <ul className="max-h-40 space-y-0.5 overflow-auto">
              {impact.facilities.map((f, i) => (
                <li key={`${f.name}-${i}`} className="text-slate-300">
                  <span className="text-amber-300">{label(f.kind)}</span> · {f.name}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-slate-500">None mapped in OpenStreetMap.</p>
          )}
        </div>
      </div>
      <Source>
        Exposure = satellite/FIRMS hazard footprint × {impact.source}. Unit costs: building ₹{fmt(Number(loss.assumptions.building_inr))}, major road ₹{fmt(Number(loss.assumptions.major_road_inr_per_km))}/km, minor road ₹{fmt(Number(loss.assumptions.minor_road_inr_per_km))}/km, rail ₹
        {fmt(Number(loss.assumptions.rail_inr_per_km))}/km, power line ₹{fmt(Number(loss.assumptions.power_line_inr_per_km))}/km. {String(loss.assumptions.note ?? "")}
      </Source>
    </div>
  );
}
