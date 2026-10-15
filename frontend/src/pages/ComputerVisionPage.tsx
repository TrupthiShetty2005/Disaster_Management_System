import { useMemo, useState } from "react";
import { StatusBadge } from "../components/StatusBadge";
import { ErrorState } from "../components/Feedback";
import { useAsync } from "../hooks/useAsync";
import { isMockMode } from "../services/apiClient";
import { analyzeVision, annotatedSrc, fetchVisionHealth, visionAnalyzeFailure } from "../services/vision";
import type { VisionResult } from "../types/api";

export function ComputerVisionPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string>("");
  const [result, setResult] = useState<VisionResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [filter, setFilter] = useState("all");
  const health = useAsync(() => (isMockMode() ? Promise.resolve({ name: "demo-vision-v0" }) : fetchVisionHealth()), []);

  const detections = useMemo(() => {
    const items = result?.detections ?? [];
    if (filter === "all") return items;
    return items.filter((d) => d.label === filter);
  }, [result, filter]);

  const labels = useMemo(() => Array.from(new Set((result?.detections ?? []).map((d) => d.label))), [result]);

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <section className="space-y-3 rounded border border-line bg-panel p-3">
        <p className="text-xs text-slate-500">
          Demo Mode uses DemoVisionModel (CPU, simulated classes). REAL DATA inference needs a local YOLO weights file
          at YOLO_WEIGHTS_PATH — weights are never downloaded. Generic YOLO does not include disaster-specific classes.
          If weights are missing the API returns 503 and no detections are invented.
        </p>
        <label htmlFor="vision-file" className="text-xs text-slate-400">
          Scene photo (JPEG/PNG/WebP, size-limited on the server)
        </label>
        <input
          id="vision-file"
          type="file"
          accept="image/jpeg,image/png,image/webp,image/bmp"
          aria-label="Upload scene image"
          onChange={(e) => {
            const next = e.target.files?.[0] ?? null;
            setFile(next);
            setResult(null);
            setError(null);
            setUnavailable(false);
            setPreview(next ? URL.createObjectURL(next) : "");
          }}
        />
          {preview ? <img src={preview} alt="Selected scene preview" className="max-h-64 w-full rounded object-contain bg-black/40" /> : null}
        <button
          type="button"
          disabled={!file || busy || (!isMockMode() && Boolean(health.error))}
          className="w-full rounded border border-amber-500/40 py-2 text-sm text-amber-200 disabled:opacity-40"
          onClick={async () => {
            if (!file) return;
            setBusy(true);
            setError(null);
            setUnavailable(false);
            try {
              setResult(await analyzeVision(file));
            } catch (err) {
              const fail = visionAnalyzeFailure(err);
              setUnavailable(fail.unavailable);
              setError(fail.message);
              setResult(null);
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? "Running analysis…" : "Run analysis"}
        </button>
        {!isMockMode() && health.error ? (
          <ErrorState message={`UNAVAILABLE: live inference requires YOLO_WEIGHTS_PATH. ${health.error}`} />
        ) : null}
        {error ? (
          unavailable ? (
            <ErrorState message={`UNAVAILABLE: ${error}`} />
          ) : (
            <p className="text-sm text-red-400">{error}</p>
          )
        ) : null}
        {result?.annotated_url ? (
          <div>
            <p className="text-[11px] uppercase tracking-widest text-slate-500">Annotated</p>
            <img src={annotatedSrc(result)} alt="Detections annotated on the uploaded scene" className="max-h-64 w-full rounded object-contain bg-black/40" />
          </div>
        ) : null}
      </section>
      <section className="space-y-3">
        {result ? (
          <>
            <div className="flex flex-wrap items-center gap-2 rounded border border-line bg-panel p-3">
              <StatusBadge value={result.overall_severity} />
              <span className="text-sm text-slate-300">{result.model_name}</span>
              <span className="text-xs text-slate-500">{result.processing_time_ms.toFixed(1)} ms · {result.backend}</span>
            </div>
            <div className="rounded border border-line bg-panel p-3">
              <h3 className="text-xs uppercase tracking-widest text-slate-500">Incident summary</h3>
              <p className="mt-1 text-sm">{result.incident?.headline}</p>
              <ul className="mt-2 list-disc pl-4 text-sm text-slate-400">
                {result.incident?.recommended_actions.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
              <p className="mt-2 text-xs text-slate-500">{result.incident?.severity_rationale}</p>
            </div>
            <div className="rounded border border-line bg-panel p-3">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-xs uppercase tracking-widest text-slate-500">Detections</h3>
                <select
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  className="rounded border border-line bg-ink px-2 py-1 text-xs"
                >
                  <option value="all">all</option>
                  {labels.map((l) => (
                    <option key={l} value={l}>
                      {l}
                    </option>
                  ))}
                </select>
              </div>
              <table className="w-full text-left text-xs">
                <thead className="text-slate-500">
                  <tr>
                    <th>Class</th>
                    <th>Conf</th>
                    <th>Severity</th>
                  </tr>
                </thead>
                <tbody>
                  {detections.map((d, i) => (
                    <tr key={`${d.label}-${i}`} className="border-t border-line">
                      <td className="py-1">{d.label}</td>
                      <td>{d.confidence.toFixed(2)}</td>
                      <td>
                        <StatusBadge value={d.severity} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              {Object.entries(result.incident?.counts ?? {}).map(([k, v]) => (
                <div key={k} className="rounded border border-line bg-panel px-3 py-2">
                  <p className="text-[11px] uppercase tracking-widest text-slate-500">{k.replaceAll("_", " ")}</p>
                  <p className="font-display text-2xl">{v}</p>
                </div>
              ))}
            </div>
          </>
        ) : health.error && !isMockMode() ? (
          <ErrorState message="No detections until YOLO weights are configured. DemoVisionModel is Demo Mode only." />
        ) : (
          <p className="text-sm text-slate-500">Upload an image and run analysis to see detections and actions.</p>
        )}
      </section>
    </div>
  );
}
