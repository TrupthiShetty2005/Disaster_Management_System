import { useEffect, useState } from "react";
import {
  fetchAoi,
  fetchKarnatakaDistricts,
  selectDistrict,
  selectPointAoi,
  type AoiState,
  type DistrictItem,
} from "../services/region";
import { isMockMode } from "../services/apiClient";

export function districtSelectPlaceholder(loading: boolean, count: number, status: string): string {
  if (loading) return "Loading districts…";
  if (count > 0) return "Select district…";
  return status || "UNAVAILABLE";
}

export function RegionPanel() {
  const [aoi, setAoi] = useState<AoiState | null>(null);
  const [districts, setDistricts] = useState<DistrictItem[]>([]);
  const [districtStatus, setDistrictStatus] = useState<string>("");
  const [districtsLoading, setDistrictsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pad, setPad] = useState(0.08);
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");

  useEffect(() => {
    if (isMockMode()) return;
    fetchAoi()
      .then((a) => {
        setAoi(a);
        setLat(String(a.latitude));
        setLon(String(a.longitude));
        setPad(a.bbox_pad_deg || 0.08);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "AOI unavailable"));
    fetchKarnatakaDistricts()
      .then((d) => {
        setDistricts(d.items || []);
        setDistrictStatus(d.status);
      })
      .catch((e) => {
        setDistricts([]);
        setDistrictStatus("UNAVAILABLE");
        setError(e instanceof Error ? e.message : "District catalog unavailable");
      })
      .finally(() => setDistrictsLoading(false));
  }, []);

  if (isMockMode()) return null;

  async function onDistrict(name: string) {
    if (!name) return;
    setBusy(true);
    setError(null);
    try {
      const next = await selectDistrict(name, pad);
      setAoi(next);
      setLat(String(next.latitude));
      setLon(String(next.longitude));
    } catch (e) {
      setError(e instanceof Error ? e.message : "District boundary unavailable");
    } finally {
      setBusy(false);
    }
  }

  async function onPoint() {
    const la = Number(lat);
    const lo = Number(lon);
    if (!Number.isFinite(la) || !Number.isFinite(lo)) {
      setError("Enter valid latitude and longitude.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const next = await selectPointAoi(la, lo, pad, "Custom Karnataka AOI");
      setAoi(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "AOI update failed");
    } finally {
      setBusy(false);
    }
  }

  const bbox = aoi?.bbox;

  return (
    <div className="space-y-2 rounded border border-line bg-panel p-2 text-xs text-slate-300">
      <p className="font-medium uppercase tracking-wider text-slate-500">India / Karnataka AOI</p>
      {aoi ? (
        <p>
          <span className="text-amber-200">{aoi.country}</span>
          {" · "}
          <span className="text-amber-200">{aoi.state}</span>
          {aoi.district ? (
            <>
              {" · district "}
              <span className="text-emerald-200">{aoi.district}</span>
            </>
          ) : null}
          <span className="ml-2 text-slate-500">{aoi.aoi_name}</span>
        </p>
      ) : (
        <p className="text-slate-500">Loading operational region…</p>
      )}
      {aoi ? (
        <p className="font-mono text-[11px] text-slate-400">
          {aoi.latitude.toFixed(4)}°N {aoi.longitude.toFixed(4)}°E
          {bbox && bbox.length === 4
            ? ` · bbox W${bbox[0].toFixed(3)} S${bbox[1].toFixed(3)} E${bbox[2].toFixed(3)} N${bbox[3].toFixed(3)}`
            : ""}
          {" · "}
          <span className="uppercase">{aoi.status}</span>
          {" · "}
          {aoi.source}
        </p>
      ) : null}
      {aoi?.coverage_note ? <p className="text-slate-500">{aoi.coverage_note}</p> : null}
      {aoi && !aoi.boundary_geojson && aoi.district ? (
        <p className="text-rose-300">District polygon UNAVAILABLE — outline not drawn.</p>
      ) : null}

      <div className="flex flex-wrap items-end gap-2">
        <label className="flex flex-col gap-1">
          Karnataka district (OSM)
          <select
            className="rounded border border-line bg-ink px-2 py-1"
            disabled={busy || districtsLoading || !districts.length}
            value={aoi?.district || ""}
            onChange={(e) => onDistrict(e.target.value)}
          >
            <option value="">{districtSelectPlaceholder(districtsLoading, districts.length, districtStatus)}</option>
            {districts.map((d) => (
              <option key={d.osm_id} value={d.name}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          Satellite pad (°)
          <input
            type="number"
            step="0.02"
            min="0.02"
            max="0.4"
            className="w-24 rounded border border-line bg-ink px-2 py-1"
            value={pad}
            onChange={(e) => setPad(Number(e.target.value))}
          />
        </label>
        <label className="flex flex-col gap-1">
          Lat
          <input className="w-28 rounded border border-line bg-ink px-2 py-1 font-mono" value={lat} onChange={(e) => setLat(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1">
          Lon
          <input className="w-28 rounded border border-line bg-ink px-2 py-1 font-mono" value={lon} onChange={(e) => setLon(e.target.value)} />
        </label>
        <button type="button" disabled={busy} className="rounded border border-amber-500/40 px-2 py-1 text-amber-200" onClick={onPoint}>
          {busy ? "Applying…" : "Apply point AOI"}
        </button>
      </div>
      {error ? <p className="text-rose-300">{error}</p> : null}
    </div>
  );
}
