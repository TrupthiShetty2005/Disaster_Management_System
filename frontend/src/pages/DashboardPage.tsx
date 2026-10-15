import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Breadcrumbs } from "../components/Breadcrumbs";
import { LIVE_REGION } from "../constants/demo";
import { KpiCard } from "../components/KpiCard";
import { DisasterMap } from "../components/DisasterMap";
import { DashboardCharts } from "../components/DashboardCharts";
import { AlertPanel } from "../components/AlertPanel";
import { SelectedAreaPanel } from "../components/SelectedAreaPanel";
import { EmptyState, LoadingState, ErrorState } from "../components/Feedback";

/** Exclusive panel view: never loading+empty, and empty ≠ error. */
export function dashboardLayerView(args: {
  loading: boolean;
  error: string | null;
  hasPayload: boolean;
}): "loading" | "error" | "empty" | "ready" {
  if (args.loading) return "loading";
  if (args.error) return "error";
  if (!args.hasPayload) return "empty";
  return "ready";
}
import { useAsync } from "../hooks/useAsync";
import { fetchDisasters } from "../services/disasters";
import { fetchAlerts } from "../services/ops";
import { fetchWeatherCurrent } from "../services/weather";
import { fetchAnalytics, fetchAnalyticsOverview } from "../services/analytics";
import { fetchGisWithProvenance } from "../services/gis";
import {
  aoiBoundary,
  featureLatLon,
  mergeDashboardCatalog,
  satelliteFootprint,
} from "../utils/dashboardMap";
import { fetchSatelliteImages } from "../services/satellite";
import { fetchFloodEvents } from "../services/flood";
import { fetchAoi } from "../services/region";
import { useDataSources } from "../components/DataModeBadge";
import type { GisFeature } from "../types/gis";

export function DashboardPage() {
  const navigate = useNavigate();
  const aoi = useAsync(fetchAoi, []);
  const disasters = useAsync(fetchDisasters, []);
  const alerts = useAsync(fetchAlerts, []);
  const weather = useAsync(fetchWeatherCurrent, []);
  const analytics = useAsync(fetchAnalytics, []);
  const overview = useAsync(fetchAnalyticsOverview, []);
  const gis = useAsync(fetchGisWithProvenance, []);
  const satellite = useAsync(() => fetchSatelliteImages(), []);
  const flood = useAsync(fetchFloodEvents, []);
  const dataSources = useDataSources();
  const [selected, setSelected] = useState<GisFeature | null>(null);
  const [copiedCoords, setCopiedCoords] = useState<string | null>(null);
  const [focusAlertId, setFocusAlertId] = useState<string | null>(null);

  const demoMode = Boolean(dataSources?.use_mock_providers === true || dataSources?.data_mode === "DEMO DATA");
  const items = disasters.data?.items ?? [];
  const kpis = overview.data?.kpis;
  const floodEvent = flood.data?.items?.[0];
  const latestScene = satellite.data?.items?.[0];
  const catalog = useMemo(
    () =>
      mergeDashboardCatalog({
        osmFeatures: gis.data?.features,
        flood: floodEvent,
        alerts: alerts.data?.items,
        allowKeralaDemo: demoMode,
      }),
    [gis.data?.features, floodEvent, alerts.data?.items, demoMode],
  );
  const mapBoundary = aoiBoundary(
    (aoi.data?.boundary_geojson as GeoJSON.GeoJsonObject | null) ?? null,
    aoi.data?.bbox,
  );
  const mapFootprint = satelliteFootprint(latestScene);
  const mapCenter: [number, number] | undefined = aoi.data
    ? [aoi.data.latitude, aoi.data.longitude]
    : undefined;
  const floodedRaw =
    floodEvent?.newly_flooded_area_km2 ??
    floodEvent?.flooded_area ??
    (typeof kpis?.flooded_area === "number" && Number(kpis.flooded_area) > 0 ? kpis.flooded_area : null);
  const floodedKm = typeof floodedRaw === "number" && floodedRaw > 0 ? floodedRaw : null;
  const weatherObserved = weather.data?.observed_at
    ? new Date(weather.data.observed_at).toISOString()
    : null;
  const weatherView = dashboardLayerView({
    loading: weather.loading,
    error: weather.error,
    hasPayload: Boolean(weather.data),
  });
  const satelliteView = dashboardLayerView({
    loading: satellite.loading,
    error: satellite.error,
    hasPayload: Boolean(latestScene),
  });
  const gisView = dashboardLayerView({
    loading: gis.loading,
    error: gis.error,
    hasPayload: Boolean(gis.data),
  });

  return (
    <div className="space-y-3">
      <Breadcrumbs items={[{ label: "Command dashboard" }]} />
      <p className="text-xs text-slate-400">
        AOI{" "}
        <span className="text-amber-200">{aoi.data?.aoi_name || LIVE_REGION}</span>
        {aoi.data ? (
          <span className="font-mono text-slate-500">
            {" "}
            · {aoi.data.latitude.toFixed(4)}°N {aoi.data.longitude.toFixed(4)}°E
          </span>
        ) : null}
        . Maps, OSM, satellite, and weather use this area. Seeded Kuttanad incidents and rescue inventory are not shown
        as Karnataka operations.
      </p>
      {aoi.error ? <ErrorState message={`AOI: ${aoi.error}`} /> : null}
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <KpiCard
          label="Active disasters"
          value={disasters.error ? "UNAVAILABLE" : String(items.filter((d) => d.status === "active").length)}
          hint={disasters.error ? disasters.error : demoMode ? "Demo incidents" : "Live incident API (seeded rows hidden)"}
        />
        <KpiCard
          label="Critical alerts"
          value={
            alerts.error
              ? "UNAVAILABLE"
              : String(
                  (alerts.data?.items ?? []).filter((a) => {
                    const s = a.severity.toLowerCase();
                    return s === "critical" || s === "severe";
                  }).length,
                )
          }
          hint={alerts.error ? alerts.error : "Alert feed; not IMD unless sourced as IMD"}
        />
        <KpiCard
          label="Population at risk"
          value={demoMode ? String(kpis?.affected_population ?? "—") : "UNAVAILABLE"}
          hint={demoMode ? "SIMULATED demo" : "No census feed"}
        />
        <KpiCard
          label="Newly water-covered"
          value={flood.error || floodedKm == null ? "UNAVAILABLE" : `${floodedKm} km²`}
          hint={
            flood.error
              ? flood.error
              : floodEvent
                ? `${floodEvent.estimate_label ?? "heuristic"} · ${floodEvent.after_date ?? ""}`
                : demoMode
                  ? "SIMULATED demo extent"
                  : "No live flood analysis yet"
          }
        />
        <KpiCard
          label="Damaged buildings"
          value={demoMode ? String(kpis?.damaged_buildings ?? 0) : "UNAVAILABLE"}
          hint={demoMode ? "SIMULATED demo count" : "No damage overlay dataset"}
        />
        <KpiCard
          label="Rescue units / shelters"
          value={demoMode ? String(kpis?.resource_utilization ?? "—") : "UNAVAILABLE"}
          hint={demoMode ? "Demo inventory" : "No live vehicle or shelter feed"}
        />
      </div>

      <div className="grid gap-3 lg:grid-cols-3 text-xs">
        <section className="rounded border border-line bg-panel p-3">
          <h3 className="mb-1 uppercase tracking-widest text-slate-500">Weather (OpenWeather)</h3>
          {weatherView === "loading" ? <LoadingState /> : null}
          {weatherView === "error" ? <p className="text-rose-300">Unavailable: {weather.error}</p> : null}
          {weatherView === "empty" ? <EmptyState message="No observation yet." /> : null}
          {weatherView === "ready" && weather.data ? (
            <>
              <p>
                {weather.data.conditions} · {weather.data.temperature_c}°C · {weather.data.rainfall_mm ?? "—"} mm ·{" "}
                {weather.data.wind_speed_ms} m/s
              </p>
              <p className="text-slate-500">
                {weather.data.source} · {weather.data.record_kind ?? "current_observation"} · observed{" "}
                {weatherObserved ?? "—"} · river gauge UNAVAILABLE
              </p>
            </>
          ) : null}
        </section>
        <section className="rounded border border-line bg-panel p-3">
          <h3 className="mb-1 uppercase tracking-widest text-slate-500">Satellite (Copernicus STAC)</h3>
          {satelliteView === "loading" ? <LoadingState /> : null}
          {satelliteView === "error" ? <p className="text-rose-300">Unavailable: {satellite.error}</p> : null}
          {satelliteView === "empty" ? (
            <EmptyState message="No Sentinel scenes for this AOI/date window." />
          ) : null}
          {satelliteView === "ready" && latestScene ? (
            <>
              <p>{latestScene.title}</p>
              <p className="text-slate-500">
                Acquired {new Date(latestScene.acquisition_time).toISOString()} · cloud {latestScene.cloud_cover}% ·{" "}
                {String(latestScene.metadata?.stac_id || latestScene.id)} · method: catalogue/preview (not real-time)
              </p>
            </>
          ) : null}
        </section>
        <section className="rounded border border-line bg-panel p-3">
          <h3 className="mb-1 uppercase tracking-widest text-slate-500">Infrastructure (OSM Overpass)</h3>
          {gisView === "loading" ? <LoadingState /> : null}
          {gisView === "error" ? <p className="text-rose-300">Unavailable: {gis.error}</p> : null}
          {gisView === "empty" ? <EmptyState message="No OSM layer loaded." /> : null}
          {gisView === "ready" && gis.data ? (
            <>
              <p>
                {gis.data.total} mapped features · {gis.data.data_provenance?.status} ·{" "}
                {gis.data.cache_hit ? `cached ${gis.data.cache_age_sec ?? 0}s` : "fresh"}
              </p>
              <p className="text-slate-500">
                {gis.data.data_provenance?.provider} · retrieved {gis.data.data_provenance?.retrieved_at ?? "—"} ·
                volunteer OSM, not official government infrastructure
              </p>
            </>
          ) : null}
        </section>
      </div>

      <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_300px]">
        <div className="h-[min(62vh,640px)] min-h-[420px]">
          <DisasterMap
            catalog={catalog}
            onSelect={setSelected}
            onFeatureAction={(feature) => {
              const act = feature.properties.clickAction;
              if (act === "copy-coords") {
                const pt = featureLatLon(feature);
                if (pt) {
                  const text = `${pt.lat.toFixed(5)}, ${pt.lon.toFixed(5)}`;
                  void navigator.clipboard?.writeText(text);
                  setCopiedCoords(text);
                }
              } else if (act === "open-flood") {
                navigate("/flood-detection");
              } else if (act === "open-alert") {
                if (feature.properties.alertId) setFocusAlertId(feature.properties.alertId);
              }
            }}
            boundary={mapBoundary}
            footprint={mapFootprint}
            center={mapCenter}
            osmUnavailable={Boolean(gis.error)}
          />
        </div>
        <div className="space-y-3">
          <SelectedAreaPanel feature={selected} note={copiedCoords ? `Copied ${copiedCoords}` : null} />
          <div className="h-[280px]">
            {alerts.error ? (
              <ErrorState message={alerts.error} />
            ) : (
              <AlertPanel items={alerts.data?.items ?? []} highlightedId={focusAlertId} />
            )}
          </div>
        </div>
      </div>

      {analytics.error ? <ErrorState message={`Analytics: ${analytics.error}`} /> : null}
      {analytics.data ? <DashboardCharts data={analytics.data} /> : null}
    </div>
  );
}
