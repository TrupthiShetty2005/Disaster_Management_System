import { useState } from "react";
import { Bar } from "react-chartjs-2";
import { assetUrl } from "../api/client";
import { detectImage, detectVideo, getVisionGallery, getVisionJobs, getVisionStatus, rebuildVisionGallery } from "../api/endpoints";
import type { VisionGallery, VisionGalleryItem, VisionImageResult, VisionJob, VisionVideoResult } from "../api/types";
import { baseOptions } from "../charts/setup";
import { BoxOverlay, ImageCompare, VideoTimeline } from "../components/VisionMedia";
import { Async, Card, Empty, ErrorBox, Kpi, Loading, PageHeader, Source } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { fmt, fmtDateTime, label } from "../lib/format";
import { GROUP_COLOR, groupCounts, labelCounts } from "../lib/vision";

const MODEL_NOTE =
  "Model: YOLOv8n pretrained on COCO (80 everyday object classes such as person, car, truck, bus, boat, cow, dog). It counts people, vehicles, boats and animals; it does not classify flood depth, building damage or fire. Counts are machine estimates for triage support and need human verification.";

function Attribution({ item }: { item: VisionGalleryItem }) {
  return (
    <p className="text-[11px] leading-snug text-slate-500">
      <a href={item.source_url} target="_blank" rel="noreferrer" className="underline hover:text-slate-300">
        {item.title}
      </a>{" "}
      · {item.author} ·{" "}
      <a href={item.licence_url} target="_blank" rel="noreferrer" className="underline hover:text-slate-300">
        {item.licence}
      </a>{" "}
      · Wikimedia Commons
    </p>
  );
}

function GroupChips({ counts }: { counts: Record<string, number> }) {
  return (
    <div className="flex flex-wrap gap-1">
      {Object.entries(counts).map(([g, n]) => (
        <span key={g} className="rounded px-1.5 py-0.5 text-[11px]" style={{ color: n ? GROUP_COLOR[g] : "#64748b", background: n ? `${GROUP_COLOR[g]}1a` : "transparent", border: `1px solid ${n ? GROUP_COLOR[g] : "#334155"}55` }}>
          {label(g)} {n}
        </span>
      ))}
    </div>
  );
}

function Benchmark({ g, onRebuild, rebuilding }: { g: VisionGallery; onRebuild: () => void; rebuilding: boolean }) {
  const s = g.stats;
  const b = g.build;
  const labels = Object.keys(s.by_label);
  return (
    <Card
      title="Benchmark on real disaster media"
      actions={
        <button className="btn" onClick={onRebuild} disabled={rebuilding || b.status === "running"}>
          {b.status === "running" ? `Processing ${b.done}/${b.total}…` : "Re-run all"}
        </button>
      }
    >
      <div className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">
        <Kpi label="Images processed" value={s.images} hint="flood & rescue photos" />
        <Kpi label="Video frames" value={fmt(s.video_frames)} hint={`${s.videos} clips · ${fmt(s.video_seconds, 1)} s of footage`} />
        <Kpi label="Objects detected" value={fmt(s.objects)} hint={`images ≥ ${s.render_conf} conf + distinct video tracks`} color="#f59e0b" />
        <Kpi label="People found" value={fmt(s.groups.people)} hint={`${s.groups.boats} boats · ${s.groups.vehicles} vehicles`} color={GROUP_COLOR.people} />
        <Kpi label="Image latency" value={`${fmt(s.image_avg_ms, 1)} ms`} hint={`avg per image · max ${fmt(s.image_max_ms, 1)} ms`} color="#38bdf8" />
        <Kpi label="Video throughput" value={`${fmt(s.video_fps, 1)} FPS`} hint={`${fmt(s.video_avg_ms, 1)} ms/frame incl. tracking`} color="#34d399" />
      </div>
      <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_320px]">
        <div className="h-48">
          {labels.length ? (
            <Bar
              data={{ labels, datasets: [{ label: "objects by COCO class", data: Object.values(s.by_label), backgroundColor: labels.map((l) => (l === "person" ? GROUP_COLOR.people : l === "boat" ? GROUP_COLOR.boats : "#38bdf8")) }] }}
              options={{ ...baseOptions<"bar">(), plugins: { legend: { display: false } } }}
            />
          ) : (
            <Empty>No results yet.</Empty>
          )}
        </div>
        <div className="space-y-1 text-xs text-slate-400">
          <p>
            <span className="text-slate-200">{g.model.name}</span> · {g.model.dataset} · {g.model.device} on {g.model.machine}
          </p>
          <p>Video: ByteTrack multi-object tracking, ~10 sampled FPS, first 20 s per clip, annotated output encoded as {g.model.video_codec}.</p>
          <p>Latency is single-image inference after model warm-up (excludes download and JPEG decode).</p>
          <p>Cache built {fmtDateTime(g.built_at)}{b.status === "running" && b.current ? ` · now processing: ${b.current}` : ""}</p>
          {b.error ? <p className="text-red-300">{b.error}</p> : null}
        </div>
      </div>
      <Source>{MODEL_NOTE}</Source>
    </Card>
  );
}

function ImageDetail({ item, conf }: { item: VisionGalleryItem; conf: number }) {
  const [mode, setMode] = useState<"compare" | "boxes">("compare");
  const r = item.result as VisionImageResult;
  const counts = labelCounts(r.detections, conf);
  return (
    <Card
      title={item.title}
      actions={
        <div className="flex gap-1">
          {(["compare", "boxes"] as const).map((m) => (
            <button key={m} className={m === mode ? "btn btn-primary" : "btn"} onClick={() => setMode(m)}>
              {m === "compare" ? "Before / after" : `Live boxes ≥ ${Math.round(conf * 100)}%`}
            </button>
          ))}
        </div>
      }
    >
      <div className="grid gap-3 lg:grid-cols-[1fr_260px]">
        {mode === "compare" ? (
          <ImageCompare original={assetUrl(item.original_url!)} annotated={assetUrl(item.annotated_url!)} alt={item.title} />
        ) : (
          <BoxOverlay src={assetUrl(item.original_url!)} width={r.width} height={r.height} detections={r.detections} conf={conf} alt={item.title} />
        )}
        <div className="space-y-2 text-xs">
          <GroupChips counts={groupCounts(r.detections, conf)} />
          <p className="text-slate-400">
            {fmt(r.processing_ms, 1)} ms · {r.width}×{r.height} px · {item.location}
            {item.year ? ` · ${item.year}` : ""}
          </p>
          <p className="text-slate-500">{item.description}</p>
          <ul className="max-h-64 space-y-0.5 overflow-auto">
            {counts.map(([l, n]) => (
              <li key={l} className="flex justify-between border-b border-line/40 py-0.5">
                <span className="text-slate-300">{l}</span>
                <span className="text-slate-500">{n}</span>
              </li>
            ))}
            {!counts.length ? <li className="text-slate-500">Nothing detected at this threshold.</li> : null}
          </ul>
          <p className="text-[11px] text-slate-500">The before/after image is rendered at {Math.round(r.render_conf * 100)}% confidence; "Live boxes" follows the threshold slider.</p>
          <Attribution item={item} />
        </div>
      </div>
    </Card>
  );
}

function VideoCard({ item }: { item: VisionGalleryItem }) {
  const r = item.result as VisionVideoResult;
  return (
    <Card title={item.title} actions={<span className="text-xs text-slate-500">{item.location}{item.year ? ` · ${item.year}` : ""}</span>}>
      <VideoTimeline src={assetUrl(item.annotated_url!)} timeline={r.timeline} />
      <VideoStats r={r} />
      <p className="mt-1 text-[11px] text-slate-500">{item.description}</p>
      <Attribution item={item} />
    </Card>
  );
}

function VideoStats({ r }: { r: VisionVideoResult }) {
  return (
    <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-slate-400 sm:grid-cols-4">
      <span>
        Frames: <b className="text-slate-200">{r.frames_processed}</b> (every {r.processed.stride}
        {r.processed.stride === 1 ? "st" : r.processed.stride === 2 ? "nd" : r.processed.stride === 3 ? "rd" : "th"})
      </span>
      <span>
        Speed: <b className="text-slate-200">{fmt(r.fps, 1)} FPS</b> · {fmt(r.avg_ms, 1)} ms
      </span>
      <span>
        Peak in one frame: <b className="text-slate-200">{r.peak.total}</b>
      </span>
      <span>
        Codec: {r.codec}
        {r.browser_playable ? "" : " (may not play in browsers)"}
      </span>
      <span className="col-span-2 sm:col-span-4">
        Distinct tracked objects (seen ≥ {r.processed.min_track_frames ?? 3} frames, ByteTrack):{" "}
        {Object.entries(r.unique_by_label)
          .map(([l, n]) => `${n} ${l}`)
          .join(" · ") || "none"}{" "}
        <span className="text-slate-500">— an upper-bound estimate: occlusion and camera motion cause ID switches.</span>
      </span>
    </div>
  );
}

function Gallery({ g, conf }: { g: VisionGallery; conf: number }) {
  const images = g.items.filter((i) => i.kind === "image");
  const videos = g.items.filter((i) => i.kind === "video");
  const ready = images.filter((i) => i.result);
  const [selected, setSelected] = useState<string | null>(null);
  const current = ready.find((i) => i.id === selected) ?? ready[0];
  return (
    <>
      {current ? <ImageDetail key={current.id} item={current} conf={conf} /> : null}
      <Card title={`Image gallery · ${ready.length}/${images.length} processed`}>
        <ul className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-4">
          {images.map((i) => (
            <li key={i.id}>
              {i.result ? (
                <button className={`w-full rounded border p-1 text-left hover:bg-white/5 ${current?.id === i.id ? "border-amber-400/70" : "border-transparent"}`} onClick={() => setSelected(i.id)}>
                  <img src={assetUrl(i.annotated_url!)} alt={i.title} loading="lazy" className="aspect-video w-full rounded border border-line object-cover" />
                  <span className="mt-1 block truncate text-xs text-slate-300">{i.title}</span>
                  <GroupChips counts={groupCounts((i.result as VisionImageResult).detections, conf)} />
                  <span className="text-[11px] text-slate-500">
                    {fmt((i.result as VisionImageResult).processing_ms, 1)} ms · {i.licence}
                  </span>
                </button>
              ) : (
                <div className="flex aspect-video items-center justify-center rounded border border-dashed border-line p-2 text-center text-[11px] text-slate-500">
                  {i.error ? `Failed: ${i.error}` : `Waiting: ${i.title}`}
                </div>
              )}
            </li>
          ))}
        </ul>
      </Card>
      <div className="grid gap-3 xl:grid-cols-2">
        {videos.map((v) =>
          v.result ? (
            <VideoCard key={v.id} item={v} />
          ) : (
            <Card key={v.id} title={v.title}>
              {v.error ? <ErrorBox message={v.error} /> : <Loading text="Downloading and tracking…" />}
              <Attribution item={v} />
            </Card>
          ),
        )}
      </div>
    </>
  );
}

function JobResult({ job }: { job: VisionJob }) {
  if (job.kind === "video" && job.video_url) {
    const r = job.summary as unknown as VisionVideoResult;
    return (
      <Card title={`Tracking · ${job.filename}`} actions={<span className="text-xs text-slate-500">{job.model}</span>}>
        <VideoTimeline src={assetUrl(job.video_url)} timeline={r.timeline} />
        <VideoStats r={r} />
      </Card>
    );
  }
  return (
    <Card title={`Detections · ${job.filename}`} actions={<span className="text-xs text-slate-500">{fmt(job.processing_ms)} ms · {job.model}</span>}>
      <div className="mb-3 grid grid-cols-2 gap-2 md:grid-cols-4">
        {Object.entries(job.summary.groups).map(([g, n]) => (
          <Kpi key={g} label={label(g)} value={n} color={n ? "#f59e0b" : undefined} />
        ))}
      </div>
      <div className="grid gap-3 lg:grid-cols-[1fr_260px]">
        {job.image_url ? <img src={assetUrl(job.image_url)} alt="annotated detections" className="w-full rounded border border-line" /> : null}
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
  const [rebuilding, setRebuilding] = useState(false);
  const [running, setRunning] = useState(false);
  const gallery = useAsync(
    () =>
      getVisionGallery().then((g) => {
        setRunning(g.build.status === "running");
        return g;
      }),
    [],
    running ? 3000 : undefined,
  );
  const [conf, setConf] = useState(0.25);
  const [job, setJob] = useState<VisionJob | null>(null);
  const history = useAsync(getVisionJobs, [job?.id]);
  const [busy, setBusy] = useState<"image" | "video" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onFile = (file: File | undefined) => {
    if (!file) return;
    const isVideo = file.type.startsWith("video/");
    setBusy(isVideo ? "video" : "image");
    setError(null);
    (isVideo ? detectVideo(file) : detectImage(file))
      .then(setJob)
      .catch((e: Error) => setError(e.message))
      .finally(() => setBusy(null));
  };

  const rebuild = () => {
    setRebuilding(true);
    rebuildVisionGallery(true)
      .then(() => setRunning(true))
      .catch((e: Error) => setError(e.message))
      .finally(() => {
        setRebuilding(false);
        gallery.reload();
      });
  };

  return (
    <div className="space-y-3">
      <PageHeader
        title="Computer vision"
        subtitle="Object detection and tracking for search-and-rescue triage: how many people, boats and vehicles are visible in drone, CCTV or field footage. Benchmarked below on real, openly licensed flood and rescue photos and videos from Karnataka, Kerala and elsewhere. Inference runs locally on the backend CPU."
        actions={
          <label className="flex items-center gap-2 rounded border border-line bg-panel px-3 py-2 text-xs text-slate-300">
            Confidence ≥ <b className="w-8 text-amber-300">{Math.round(conf * 100)}%</b>
            <input type="range" min={0.1} max={0.9} step={0.05} value={conf} onChange={(e) => setConf(Number(e.target.value))} aria-label="Confidence threshold" />
          </label>
        }
      />
      <Async state={gallery} loadingText="Loading benchmark gallery…">
        {(g) => (
          <>
            <Benchmark g={g} onRebuild={rebuild} rebuilding={rebuilding} />
            <Gallery g={g} conf={conf} />
          </>
        )}
      </Async>
      <Card title="Analyse your own image or video">
        <Async state={status}>
          {(s) => (
            <p className="mb-2 text-xs text-slate-400">
              {s.available ? "Ready" : "Unavailable"} · {s.model} · {s.framework} · {s.classes} classes {s.loaded ? "· loaded in memory" : "· loads on first request"}
              {s.detail ? ` · ${s.detail}` : ""}
            </p>
          )}
        </Async>
        <label className="flex cursor-pointer flex-col items-center justify-center rounded border border-dashed border-line px-4 py-8 text-sm text-slate-400 hover:bg-white/5">
          <span>{busy ? `Running ${busy === "video" ? "tracking" : "detection"}…` : "Choose a JPG / PNG / WebP image (max 8 MB) or an MP4 / WebM / MOV video (max 40 MB, first 20 s analysed)"}</span>
          <input type="file" accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,video/quicktime" className="hidden" disabled={!!busy} onChange={(e) => onFile(e.target.files?.[0])} />
        </label>
        {busy ? <Loading text={busy === "video" ? "Running YOLOv8n + ByteTrack on sampled frames…" : "Running YOLOv8n inference…"} /> : null}
        {error ? <ErrorBox message={error} /> : null}
        <Source>{MODEL_NOTE}</Source>
      </Card>
      {job ? <JobResult job={job} /> : null}
      <Card title="Recent uploads">
        <Async state={history}>
          {(h) =>
            h.items.length ? (
              <ul className="grid grid-cols-2 gap-2 md:grid-cols-4">
                {h.items.map((j) => (
                  <li key={j.id}>
                    <button className="w-full text-left" onClick={() => setJob(j)}>
                      {j.image_url ? (
                        <img src={assetUrl(j.image_url)} alt={j.filename} className="aspect-video w-full rounded border border-line object-cover" />
                      ) : (
                        <div className="flex aspect-video w-full items-center justify-center rounded border border-line bg-black text-xs text-slate-400">▶ {j.filename}</div>
                      )}
                      <span className="text-[11px] text-slate-400">
                        {j.kind === "video" ? `${j.summary.frames_processed ?? 0} frames` : `${j.summary.total} objects`} · {fmtDateTime(j.created_at)}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <Empty>No uploads analysed yet.</Empty>
            )
          }
        </Async>
      </Card>
    </div>
  );
}
