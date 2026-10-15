import { useState } from "react";
import { assetUrl } from "../api/client";
import { detectImage, getVisionJobs, getVisionStatus } from "../api/endpoints";
import type { VisionJob } from "../api/types";
import { Async, Card, Empty, ErrorBox, Kpi, Loading, PageHeader, Source } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { fmt, fmtDateTime, label } from "../lib/format";

function JobResult({ job }: { job: VisionJob }) {
  return (
    <Card title={`Detections · ${job.filename}`} actions={<span className="text-xs text-slate-500">{fmt(job.processing_ms)} ms · {job.model}</span>}>
      <div className="mb-3 grid grid-cols-2 gap-2 md:grid-cols-4">
        {Object.entries(job.summary.groups).map(([g, n]) => (
          <Kpi key={g} label={label(g)} value={n} color={n ? "#f59e0b" : undefined} />
        ))}
      </div>
      <div className="grid gap-3 lg:grid-cols-[1fr_260px]">
        <img src={assetUrl(job.image_url)} alt="annotated detections" className="w-full rounded border border-line" />
        <div className="text-xs">
          <p className="mb-1 text-slate-500">{job.summary.total} objects</p>
          <ul className="max-h-96 space-y-0.5 overflow-auto">
            {job.detections.map((d, i) => (
              <li key={i} className="flex justify-between border-b border-line/40 py-0.5">
                <span className="text-slate-300">{d.label}</span>
                <span className="text-slate-500">{Math.round(d.confidence * 100)}%</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Card>
  );
}

export default function VisionPage() {
  const status = useAsync(getVisionStatus, []);
  const [job, setJob] = useState<VisionJob | null>(null);
  const history = useAsync(getVisionJobs, [job?.id]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onFile = (file: File | undefined) => {
    if (!file) return;
    setBusy(true);
    setError(null);
    detectImage(file)
      .then(setJob)
      .catch((e: Error) => setError(e.message))
      .finally(() => setBusy(false));
  };

  return (
    <div className="space-y-3">
      <PageHeader
        title="Computer vision"
        subtitle="Upload a drone, CCTV or field photo of an affected area. A YOLOv8 object detector counts people, vehicles, boats and animals to support search-and-rescue triage. Inference runs locally on the backend."
      />
      <Card title="Model">
        <Async state={status}>
          {(s) => (
            <p className="text-sm text-slate-300">
              {s.available ? "Ready" : "Unavailable"} · {s.model} · {s.framework} · {s.classes} classes {s.loaded ? "· loaded in memory" : "· loads on first image"}
              {s.detail ? ` · ${s.detail}` : ""}
            </p>
          )}
        </Async>
      </Card>
      <Card title="Analyse an image">
        <label className="flex cursor-pointer flex-col items-center justify-center rounded border border-dashed border-line px-4 py-8 text-sm text-slate-400 hover:bg-white/5">
          <span>{busy ? "Running detection…" : "Choose a JPG, PNG or WebP image (max 8 MB)"}</span>
          <input type="file" accept="image/jpeg,image/png,image/webp" className="hidden" disabled={busy} onChange={(e) => onFile(e.target.files?.[0])} />
        </label>
        {busy ? <Loading text="Running YOLOv8 inference…" /> : null}
        {error ? <ErrorBox message={error} /> : null}
        <Source>COCO-trained detector: it recognises general objects (person, car, truck, boat, animals), not damage classes.</Source>
      </Card>
      {job ? <JobResult job={job} /> : null}
      <Card title="Recent images">
        <Async state={history}>
          {(h) =>
            h.items.length ? (
              <ul className="grid grid-cols-2 gap-2 md:grid-cols-4">
                {h.items.map((j) => (
                  <li key={j.id}>
                    <button className="w-full text-left" onClick={() => setJob(j)}>
                      <img src={assetUrl(j.image_url)} alt={j.filename} className="aspect-video w-full rounded border border-line object-cover" />
                      <span className="text-[11px] text-slate-400">
                        {j.summary.total} objects · {fmtDateTime(j.created_at)}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <Empty>No images analysed yet.</Empty>
            )
          }
        </Async>
      </Card>
    </div>
  );
}
