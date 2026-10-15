import { SafetyBanner } from "../components/SafetyBanner";
import { Breadcrumbs } from "../components/Breadcrumbs";
import { exportUrl } from "../services/analytics";
import { generateReport } from "../services/reports";
import { DEMO_INCIDENT_ID, DEMO_INCIDENT_TITLE, DEMO_REGION, LIVE_REGION, LIVE_WEATHER_QUERY } from "../constants/demo";
import { isMockMode } from "../services/apiClient";
import { useState } from "react";

const flow = [
  "Weather → risk engine → high-risk zone → alert engine → command dashboard",
  "Satellite → image analysis → flood/damage detection → GIS → incident command",
  "Computer vision → object detection → incident analysis → rescue priority",
  "All streams → rescue planning → resource allocation → human approval (accept/modify/reject)",
];

export function SettingsPage() {
  const [note, setNote] = useState("");
  return (
    <div className="max-w-2xl space-y-4 text-sm text-slate-400">
      <Breadcrumbs items={[{ to: "/dashboard", label: "Command dashboard" }, { label: "Settings" }]} />
      <SafetyBanner />
      <section className="rounded border border-line bg-panel p-4">
        <h3 className="text-xs uppercase tracking-widest text-slate-500">Operating region</h3>
        {isMockMode() ? (
          <>
            <p className="mt-2 text-slate-200">{DEMO_INCIDENT_TITLE}</p>
            <p>
              Demo region {DEMO_REGION}. Incident ID <code className="text-amber-200">{DEMO_INCIDENT_ID}</code>.
            </p>
          </>
        ) : (
          <>
            <p className="mt-2 text-slate-200">{LIVE_REGION}</p>
            <p>
              Live weather query <code className="text-amber-200">{LIVE_WEATHER_QUERY}</code>. Seeded Kuttanad incidents are
              hidden. Missing providers show UNAVAILABLE — they never fall back to mock.
            </p>
          </>
        )}
      </section>
      <section className="rounded border border-line bg-panel p-4">
        <h3 className="text-xs uppercase tracking-widest text-slate-500">Integrated streams</h3>
        <ul className="mt-2 list-disc pl-5">
          {flow.map((f) => (
            <li key={f}>{f}</li>
          ))}
        </ul>
      </section>
      <section className="rounded border border-line bg-panel p-4">
        <h3 className="text-xs uppercase tracking-widest text-slate-500">Exports</h3>
        <div className="mt-2 flex flex-wrap gap-2">
          {["analytics", "incident", "damage", "resources", "alerts"].map((d) => (
            <a key={d} className="rounded border border-line px-2 py-1 capitalize" href={exportUrl(d)}>
              {d} CSV
            </a>
          ))}
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {["incident", "damage", "rescue", "risk"].map((kind) => (
            <button
              key={kind}
              type="button"
              className="rounded border border-amber-500/40 px-2 py-1 text-amber-200"
              onClick={async () => {
                try {
                  const r = await generateReport(kind);
                  setNote(`${kind} JSON generated (pdf_available=${String(r.pdf_available)})`);
                } catch (err) {
                  setNote(`${kind} report UNAVAILABLE: ${err instanceof Error ? err.message : "request failed"}`);
                }
              }}
            >
              {kind} report JSON
            </button>
          ))}
        </div>
        {note ? (
          <p className={`mt-2 text-xs ${note.includes("UNAVAILABLE") ? "text-rose-300" : "text-emerald-300"}`}>{note}</p>
        ) : null}
      </section>
      <section className="rounded border border-line bg-panel p-4">
        <h3 className="text-xs uppercase tracking-widest text-slate-500">Demo mode</h3>
        <p className="mt-2 text-slate-200">
          Demo Mode is explicit: backend <code className="text-amber-200">USE_MOCK_PROVIDERS=true</code>{" "}
          <em>and</em> frontend <code className="text-amber-200">VITE_USE_MOCK=true</code>. If the API reports REAL
          DATA, local mock JSON is never used. If the API is down, the UI shows unavailable — it does not fall back to
          mock.
        </p>
      </section>
      <p>Provider keys live in backend `.env`. This UI does not store secrets. Mock: `VITE_USE_MOCK` and `USE_MOCK_PROVIDERS`.</p>
    </div>
  );
}
