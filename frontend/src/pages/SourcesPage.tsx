import { API_BASE } from "../api/client";
import { getSources } from "../api/endpoints";
import { Async, Card, PageHeader, Source } from "../components/ui";
import { useAsync } from "../hooks/useAsync";

export default function SourcesPage() {
  const state = useAsync(getSources, [], 300_000);
  return (
    <div className="space-y-3">
      <PageHeader
        title="Data sources"
        subtitle="Live status of every external feed the system uses. Every figure is fetched from these feeds; if a source is down, the affected panels show it as unavailable."
        actions={
          <button className="btn" onClick={state.reload} disabled={state.loading}>
            {state.loading ? "Checking…" : "Re-check"}
          </button>
        }
      />
      <Card title="Feeds">
        <Async state={state} loadingText="Probing all sources…">
          {(d) => (
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-slate-500">
                <tr>
                  <th className="py-1">Source</th>
                  <th>Used for</th>
                  <th>Status</th>
                  <th className="text-right">Latency</th>
                  <th>Last response</th>
                </tr>
              </thead>
              <tbody>
                {d.items.map((s) => (
                  <tr key={s.name} className="border-t border-line/50 align-top">
                    <td className="py-1.5 text-slate-200">{s.name}</td>
                    <td className="text-xs text-slate-400">{s.purpose}</td>
                    <td>
                      <span className={`text-xs font-semibold ${s.ok ? "text-emerald-400" : "text-red-400"}`}>{s.ok ? "LIVE" : "DOWN"}</span>
                    </td>
                    <td className="text-right text-xs text-slate-400">{s.latency_ms} ms</td>
                    <td className="text-xs text-slate-400">{s.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Async>
        <Source>Backend: {API_BASE}. Status is cached for 5 minutes.</Source>
      </Card>
      <Card title="How predictions are made">
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
          <li>
            <strong>Water levels:</strong> GloFAS v4 daily discharge and 30-day ensemble forecast at each dam/gauge. Flood thresholds are 2-, 5- and 20-year return levels fitted (Gumbel) to the river cell's own June–November maxima since 2005.
          </li>
          <li>
            <strong>Rain:</strong> Open-Meteo observed and forecast precipitation per district, classified with IMD 24-hour categories (heavy ≥ 64.5 mm, very heavy ≥ 115.6 mm, extremely heavy ≥ 204.5 mm).
          </li>
          <li>
            <strong>Fire:</strong> NASA FIRMS VIIRS/MODIS detections clipped to Karnataka, clustered within 2 km. Sites active on 4 or more days are classified as industrial. Fire danger uses the Fosberg Fire Weather Index from forecast temperature, humidity and wind, reduced by rain and raised where fires are already burning.
          </li>
          <li>
            <strong>Floods & burn scars:</strong> Sentinel-1 RTC VV backscatter change (radar, works through cloud) or Sentinel-2 NDWI; burn scars by Sentinel-2 dNBR. Every result names the exact scenes used.
          </li>
          <li>
            <strong>Infrastructure losses:</strong> hazard polygons intersected with OpenStreetMap buildings, roads, railways, power lines and facilities. Replacement unit costs × damage ratio, with all assumptions shown.
          </li>
        </ul>
      </Card>
    </div>
  );
}
