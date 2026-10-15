import { Link } from "react-router-dom";
import type { GisFeature } from "../types/gis";

export function SelectedAreaPanel({ feature, note }: { feature: GisFeature | null; note?: string | null }) {
  if (!feature) {
    return (
      <section className="rounded border border-line bg-panel p-3 text-sm text-slate-500">
        Select a map feature for details. Hospitals copy coordinates. Flood polygons open Flood Detection. Alert pins
        open Alerts.
        {note ? <p className="mt-2 text-xs text-emerald-300">{note}</p> : null}
      </section>
    );
  }
  const p = feature.properties;
  return (
    <section className="rounded border border-line bg-panel p-3 text-sm">
      <p className="text-[11px] uppercase tracking-widest text-slate-500">Selected area</p>
      <h3 className="font-display text-xl text-slate-100">{p.name}</h3>
      <p className="text-xs text-slate-500">
        {p.layer}
        {p.feature_type ? ` · ${p.feature_type}` : ""}
        {p.source ? ` · ${p.source}` : ""}
      </p>
      {p.osm_id != null ? (
        <p className="text-[11px] text-slate-500">
          OSM {p.osm_type || "feature"} {p.osm_id}
          {p.retrieved_at ? ` · retrieved ${p.retrieved_at}` : ""}
        </p>
      ) : null}
      {p.riskScore != null ? (
        <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-slate-300">
          <dt className="text-slate-500">Risk score</dt>
          <dd>{p.riskScore.toFixed(2)}</dd>
          <dt className="text-slate-500">Probability</dt>
          <dd>{((p.probability ?? 0) * 100).toFixed(0)}%</dd>
          <dt className="text-slate-500">Affected population</dt>
          <dd>{(p.affectedPopulation ?? 0).toLocaleString("en-IN")}</dd>
          <dt className="text-slate-500">Rainfall</dt>
          <dd>{p.rainfallMm ?? "—"} mm</dd>
          <dt className="text-slate-500">Water level</dt>
          <dd>{p.waterLevelM ?? "—"} m</dd>
        </dl>
      ) : (
        <p className="mt-2 text-xs text-slate-400">{p.description ?? p.status ?? "Feature selected."}</p>
      )}
      {p.evacuationRecommendation ? (
        <p className="mt-2 border-t border-line pt-2 text-xs text-amber-200">{p.evacuationRecommendation}</p>
      ) : null}
      {p.clickAction === "copy-coords" ? (
        <p className="mt-2 text-[11px] text-sky-300">Click copies latitude, longitude.</p>
      ) : null}
      {p.clickAction === "open-flood" ? (
        <p className="mt-2 text-[11px] text-sky-300">Opens Flood Detection for this overlay.</p>
      ) : null}
      {p.clickAction === "open-alert" ? (
        <p className="mt-2 text-[11px] text-sky-300">
          Highlighted in the alert list.{" "}
          <Link className="underline" to="/alerts">
            Open Alerts page
          </Link>
        </p>
      ) : null}
      {note ? <p className="mt-2 text-xs text-emerald-300">{note}</p> : null}
    </section>
  );
}
