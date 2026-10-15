import { useState } from "react";
import { DisasterMap } from "../components/DisasterMap";
import { Breadcrumbs } from "../components/Breadcrumbs";
import { DataTable } from "../components/DataTable";
import { ModuleProvenance } from "../components/DataModeBadge";
import { SelectedAreaPanel } from "../components/SelectedAreaPanel";
import { useAsync } from "../hooks/useAsync";
import { fetchDisasters } from "../services/disasters";
import { emptyCatalog, fetchGisCatalog, fetchGisWithProvenance } from "../services/gis";
import { fetchAoi, fetchIndiaRegions } from "../services/region";
import { LoadingState, ErrorState } from "../components/Feedback";
import type { GisFeature } from "../types/gis";

export function SituationPage() {
  const gis = useAsync(fetchGisCatalog, []);
  const osm = useAsync(fetchGisWithProvenance, []);
  const disasters = useAsync(fetchDisasters, []);
  const aoi = useAsync(fetchAoi, []);
  const india = useAsync(fetchIndiaRegions, []);
  const [selected, setSelected] = useState<GisFeature | null>(null);
  const mapCenter: [number, number] | undefined = aoi.data
    ? [aoi.data.latitude, aoi.data.longitude]
    : undefined;
  if (gis.loading && disasters.loading && aoi.loading) return <LoadingState />;
  const boundary =
    aoi.data?.boundary_geojson ||
    (india.data?.karnataka?.status === "STATIC_EXTERNAL" ? india.data.karnataka.geojson : null) ||
    null;
  return (
    <div className="space-y-3">
      <Breadcrumbs items={[{ to: "/dashboard", label: "Command dashboard" }, { label: "Live situation" }]} />
      <ModuleProvenance moduleKey="gis" title="GIS / map layers" />
      <ModuleProvenance moduleKey="incidents" title="Disaster incidents table" />
      <p className="text-xs text-slate-500">
        India-wide exploration uses OSM Nominatim. Analysis is Karnataka-first. Map infrastructure is OpenStreetMap
        volunteer data (ODbL) for the selected AOI — not official government infrastructure. Empty OSM layers mean
        nothing was mapped in that query, not that facilities are confirmed absent. Timeouts are UNAVAILABLE.
      </p>
      {india.data?.status === "UNAVAILABLE" ? (
        <p className="text-xs text-rose-300">India/Karnataka admin polygons UNAVAILABLE: {india.data.description}</p>
      ) : null}
      {gis.error ? <ErrorState message={`OSM GIS: ${gis.error}`} /> : null}
      {osm.error ? <ErrorState message={`OSM Overpass: ${osm.error}`} /> : null}
      {osm.data?.data_provenance ? (
        <p className="text-xs text-sky-300">
          OSM {osm.data.total} features · {osm.data.data_provenance.status} · {osm.data.data_provenance.provider}
          {osm.data.data_provenance.retrieved_at ? ` · ${osm.data.data_provenance.retrieved_at}` : ""}
          {osm.data.cache_hit ? ` · cached snapshot ${osm.data.cache_age_sec ?? 0}s old (not live)` : " · fresh fetch"}
          {osm.data.empty_result ? " · query succeeded with zero mapped features" : ""}
        </p>
      ) : null}
      {osm.data?.layer_status ? (
        <p className="text-[11px] text-slate-500">
          Layer coverage:{" "}
          {Object.entries(osm.data.layer_status)
            .map(([k, v]) => `${k}: ${v}`)
            .join(" · ")}
        </p>
      ) : null}
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="h-[520px]">
          {gis.data ? (
            <DisasterMap
              catalog={gis.data}
              onSelect={setSelected}
              boundary={boundary}
              center={mapCenter}
              osmUnavailable={Boolean(gis.error || osm.error)}
            />
          ) : (
            <DisasterMap
              catalog={emptyCatalog()}
              onSelect={setSelected}
              boundary={boundary}
              center={mapCenter}
              osmUnavailable={Boolean(gis.error || osm.error)}
            />
          )}
        </div>
        <div className="space-y-3">
          <SelectedAreaPanel feature={selected} />
          <DataTable
            columns={["Event", "Phase", "Severity", "People"]}
            rows={(disasters.data?.items ?? []).map((d) => [d.title, d.phase, d.severity, String(d.people_at_risk)])}
          />
          {osm.data?.features?.length ? (
            <DataTable
              columns={["OSM feature", "Layer"]}
              rows={osm.data.features.slice(0, 12).map((f) => [
                String(f.properties?.name ?? "—"),
                String(f.properties?.feature_type ?? f.properties?.layer ?? "—"),
              ])}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}
