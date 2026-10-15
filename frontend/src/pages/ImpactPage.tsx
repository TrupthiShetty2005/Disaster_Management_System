import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getAnalyses, getAnalysis } from "../api/endpoints";
import type { Analysis } from "../api/types";
import { Async, Card, Empty, ErrorBox, Kpi, Loading, PageHeader } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { fmt, fmtDate, inr } from "../lib/format";
import { AnalysisResult } from "./SatellitePage";

export default function ImpactPage() {
  const [params, setParams] = useSearchParams();
  const list = useAsync(getAnalyses, []);
  const [detail, setDetail] = useState<{ loading: boolean; a?: Analysis; error?: string }>({ loading: false });
  const selected = params.get("analysis");

  useEffect(() => {
    if (!selected) return;
    setDetail({ loading: true });
    getAnalysis(selected)
      .then((a) => setDetail({ loading: false, a }))
      .catch((e: Error) => setDetail({ loading: false, error: e.message }));
  }, [selected]);

  return (
    <div className="space-y-3">
      <PageHeader
        title="Infrastructure losses"
        subtitle="Every flood or burn footprint mapped from Sentinel imagery is intersected with OpenStreetMap buildings, roads, railways, power lines and critical facilities. Losses use transparent, configurable unit costs, and each assumption is shown next to the estimate."
        actions={
          <div className="flex gap-2">
            <Link to="/satellite" className="btn-primary">
              New satellite analysis
            </Link>
            <Link to="/fire" className="btn">
              Fire-event impact
            </Link>
          </div>
        }
      />
      <Async state={list}>
        {(d) => {
          const done = d.items.filter((a) => a.impact?.status === "complete");
          const totalLoss = done.reduce((s, a) => s + (a.impact?.loss?.estimated_loss_crore ?? 0), 0);
          const totalBuildings = done.reduce((s, a) => s + (a.impact?.exposed?.buildings ?? 0), 0);
          const totalRoad = done.reduce((s, a) => s + (a.impact?.exposed?.road_km ?? 0), 0);
          const totalArea = done.reduce((s, a) => s + (a.impact?.hazard_area_km2 ?? 0), 0);
          return (
            <>
              <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
                <Kpi label="Assessed events" value={done.length} hint={`${d.items.length} analyses stored`} />
                <Kpi label="Hazard area mapped" value={`${fmt(totalArea, 1)} km²`} />
                <Kpi label="Buildings / roads exposed" value={fmt(totalBuildings)} hint={`${fmt(totalRoad, 1)} km of road`} color="#f97316" />
                <Kpi label="Estimated loss (all)" value={inr(totalLoss)} color="#ef4444" />
              </div>
              <Card title="Assessments">
                {d.items.length ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead className="text-left text-slate-500">
                        <tr>
                          <th className="py-1">Event</th>
                          <th>Dates</th>
                          <th className="text-right">Footprint km²</th>
                          <th className="text-right">Buildings</th>
                          <th className="text-right">Road km</th>
                          <th className="text-right">Power km</th>
                          <th className="text-right">Loss</th>
                        </tr>
                      </thead>
                      <tbody>
                        {d.items.map((a) => (
                          <tr key={a.id} onClick={() => setParams({ analysis: a.id })} className={`cursor-pointer border-t border-line/50 hover:bg-white/5 ${selected === a.id ? "bg-amber-500/10" : ""}`}>
                            <td className="py-1.5 text-slate-200">
                              {a.kind === "flood" ? "Flood" : "Burn scar"} · {a.area_name}
                            </td>
                            <td className="text-slate-400">
                              {fmtDate(a.before?.date)} → {fmtDate(a.after?.date)}
                            </td>
                            <td className="text-right">{fmt(a.impact?.hazard_area_km2, 2)}</td>
                            <td className="text-right">{a.impact?.status === "complete" ? fmt(a.impact.exposed?.buildings) : a.impact?.status === "osm_unavailable" ? "OSM down" : "—"}</td>
                            <td className="text-right">{fmt(a.impact?.exposed?.road_km, 1)}</td>
                            <td className="text-right">{fmt(a.impact?.exposed?.power_line_km, 1)}</td>
                            <td className="text-right text-red-300">{inr(a.impact?.loss?.estimated_loss_crore)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <Empty>No assessments yet. Run a flood or burn analysis on the Satellite page, or estimate a fire event on the Fire page.</Empty>
                )}
              </Card>
            </>
          );
        }}
      </Async>
      {detail.loading ? <Loading /> : null}
      {detail.error ? <ErrorBox message={detail.error} /> : null}
      {detail.a ? <AnalysisResult a={detail.a} /> : null}
    </div>
  );
}
