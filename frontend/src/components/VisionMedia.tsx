import { useMemo, useRef, useState } from "react";
import type { Chart, ChartOptions, Plugin } from "chart.js";
import { Line } from "react-chartjs-2";
import type { VisionDetection, VisionTimelinePoint } from "../api/types";
import { baseOptions } from "../charts/setup";
import { GROUP_COLOR, atThreshold, groupOf, nearestIndex } from "../lib/vision";

/** Before/after slider: original on the left of the handle, annotated detector output on the right. */
export function ImageCompare({ original, annotated, alt }: { original: string; annotated: string; alt: string }) {
  const [pos, setPos] = useState(50);
  return (
    <div className="relative select-none overflow-hidden rounded border border-line">
      <img src={original} alt={`${alt} (original)`} className="block w-full" draggable={false} />
      <img src={annotated} alt={`${alt} (detections)`} className="absolute inset-0 h-full w-full" style={{ clipPath: `inset(0 0 0 ${pos}%)` }} draggable={false} />
      <div className="pointer-events-none absolute inset-y-0 w-0.5 bg-white/80 shadow" style={{ left: `${pos}%` }} />
      <span className="absolute left-2 top-2 rounded bg-black/60 px-1.5 py-0.5 text-[11px] text-slate-200">Original</span>
      <span className="absolute right-2 top-2 rounded bg-black/60 px-1.5 py-0.5 text-[11px] text-amber-300">YOLOv8n detections</span>
      <input
        type="range"
        min={0}
        max={100}
        value={pos}
        onChange={(e) => setPos(Number(e.target.value))}
        aria-label="Before / after position"
        className="absolute inset-0 h-full w-full cursor-ew-resize opacity-0"
      />
    </div>
  );
}

/** Original image with detections drawn client-side, so the confidence threshold can be changed live. */
export function BoxOverlay({ src, width, height, detections, conf, alt }: { src: string; width: number; height: number; detections: VisionDetection[]; conf: number; alt: string }) {
  const shown = atThreshold(detections, conf);
  const font = Math.max(12, Math.round(width / 70));
  return (
    <div className="relative overflow-hidden rounded border border-line">
      <img src={src} alt={alt} className="block w-full" />
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className="absolute inset-0 h-full w-full">
        {shown.map((d, i) => {
          const [x1, y1, x2, y2] = d.bbox;
          const c = GROUP_COLOR[groupOf(d.label)];
          return (
            <g key={i}>
              <rect x={x1} y={y1} width={x2 - x1} height={y2 - y1} fill="none" stroke={c} strokeWidth={Math.max(2, width / 400)} />
              <text x={x1 + 3} y={Math.max(font, y1 - 4)} fill={c} fontSize={font} fontWeight={600} paintOrder="stroke" stroke="#000" strokeWidth={3}>
                {d.label} {Math.round(d.confidence * 100)}%
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

const SERIES = ["people", "vehicles", "boats", "animals"] as const;

/** Annotated video with a counts-over-time chart; a cursor follows playback and clicking the chart seeks. */
export function VideoTimeline({ src, timeline }: { src: string; timeline: VisionTimelinePoint[] }) {
  const video = useRef<HTMLVideoElement>(null);
  const chart = useRef<Chart<"line"> | null>(null);
  const cursor = useRef(-1);
  const times = useMemo(() => timeline.map((p) => p.t), [timeline]);

  const plugin = useMemo<Plugin<"line">>(
    () => ({
      id: "playhead",
      afterDatasetsDraw(c) {
        if (cursor.current < 0) return;
        const x = c.scales.x.getPixelForValue(cursor.current);
        const { top, bottom } = c.chartArea;
        c.ctx.save();
        c.ctx.strokeStyle = "#f8fafc";
        c.ctx.lineWidth = 1;
        c.ctx.beginPath();
        c.ctx.moveTo(x, top);
        c.ctx.lineTo(x, bottom);
        c.ctx.stroke();
        c.ctx.restore();
      },
    }),
    [],
  );

  const options = useMemo(() => {
    const o = baseOptions<"line">("objects in frame");
    o.onClick = (evt, _els, c) => {
      const idx = c.scales.x.getValueForPixel(evt.x ?? 0);
      if (video.current && idx !== undefined && timeline[idx]) video.current.currentTime = timeline[idx].t;
    };
    return o as ChartOptions<"line">;
  }, [timeline]);

  const active = SERIES.filter((s) => timeline.some((p) => p[s] > 0));
  const data = {
    labels: timeline.map((p) => `${p.t.toFixed(1)}s`),
    datasets: (active.length ? active : SERIES.slice(0, 1)).map((s) => ({
      label: s,
      data: timeline.map((p) => p[s]),
      borderColor: GROUP_COLOR[s],
      backgroundColor: `${GROUP_COLOR[s]}33`,
      pointRadius: 0,
      borderWidth: 1.5,
      stepped: true as const,
    })),
  };

  const onTime = () => {
    const t = video.current?.currentTime ?? 0;
    const idx = nearestIndex(times, t);
    if (idx !== cursor.current) {
      cursor.current = idx;
      chart.current?.draw();
    }
  };

  return (
    <div className="space-y-2">
      <video ref={video} src={src} controls muted playsInline loop preload="metadata" onTimeUpdate={onTime} className="w-full rounded border border-line bg-black" />
      <div className="h-40 cursor-pointer">
        <Line ref={chart} data={data} options={options} plugins={[plugin]} />
      </div>
    </div>
  );
}
