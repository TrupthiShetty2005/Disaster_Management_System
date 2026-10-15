import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { DEMO_INCIDENT_ID, DEMO_INCIDENT_TITLE, DEMO_REGION } from "../constants/demo";
import { isMockMode } from "../services/apiClient";
import { fetchAoi, type AoiState } from "../services/region";

export function IncidentBar() {
  const [aoi, setAoi] = useState<AoiState | null>(null);

  useEffect(() => {
    if (isMockMode()) return;
    fetchAoi()
      .then(setAoi)
      .catch(() => setAoi(null));
  }, []);

  if (isMockMode()) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line bg-ink/40 px-3 py-1.5 text-xs text-slate-400">
        <p>
          Active incident:{" "}
          <Link className="text-amber-300 hover:underline" to={`/disasters/${DEMO_INCIDENT_ID}`}>
            {DEMO_INCIDENT_TITLE}
          </Link>
          <span className="text-slate-600">
            {" "}
            · {DEMO_REGION} · ID {DEMO_INCIDENT_ID.slice(0, 8)}…
          </span>
          <span className="ml-2 rounded border border-amber-500/40 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-amber-200">
            Demo mode
          </span>
        </p>
        <p className="text-slate-600">Prototype decision support · not official warnings</p>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line bg-ink/40 px-3 py-1.5 text-xs text-slate-400">
      <p>
        India · Karnataka
        {aoi?.district ? <span className="text-amber-200"> · {aoi.district}</span> : null}
        {aoi ? (
          <span className="font-mono text-slate-500">
            {" "}
            · {aoi.latitude.toFixed(3)}°N {aoi.longitude.toFixed(3)}°E
          </span>
        ) : null}
        <span className="ml-2 rounded border border-emerald-500/40 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-emerald-200">
          Real data
        </span>
      </p>
      <p className="text-slate-600">Decision support · not official government warnings</p>
    </div>
  );
}
