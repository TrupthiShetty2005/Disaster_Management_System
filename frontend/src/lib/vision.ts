import type { VisionDetection } from "../api/types";

/** Same COCO class groups the backend uses in services/vision.py. */
export const VISION_GROUPS: Record<string, string[]> = {
  people: ["person"],
  vehicles: ["car", "truck", "bus", "motorcycle", "bicycle", "train"],
  boats: ["boat"],
  animals: ["cow", "horse", "sheep", "dog", "elephant", "bird", "cat"],
};

export const GROUP_COLOR: Record<string, string> = {
  people: "#f59e0b",
  vehicles: "#38bdf8",
  boats: "#34d399",
  animals: "#f472b6",
  other: "#a78bfa",
};

export function groupOf(label: string): string {
  for (const [g, classes] of Object.entries(VISION_GROUPS)) if (classes.includes(label)) return g;
  return "other";
}

export function atThreshold(dets: VisionDetection[], conf: number): VisionDetection[] {
  return dets.filter((d) => d.confidence >= conf);
}

/** Group counts (people / vehicles / boats / animals) for detections at or above `conf`. */
export function groupCounts(dets: VisionDetection[], conf: number): Record<string, number> {
  const out: Record<string, number> = Object.fromEntries(Object.keys(VISION_GROUPS).map((g) => [g, 0]));
  for (const d of atThreshold(dets, conf)) {
    const g = groupOf(d.label);
    if (g in out) out[g] += 1;
  }
  return out;
}

export function labelCounts(dets: VisionDetection[], conf: number): [string, number][] {
  const out = new Map<string, number>();
  for (const d of atThreshold(dets, conf)) out.set(d.label, (out.get(d.label) ?? 0) + 1);
  return [...out.entries()].sort((a, b) => b[1] - a[1]);
}

/** Index of the timeline sample nearest to time `t` (seconds); timeline must be sorted by t. */
export function nearestIndex(times: number[], t: number): number {
  if (!times.length) return -1;
  let lo = 0;
  let hi = times.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (times[mid] < t) lo = mid + 1;
    else hi = mid;
  }
  return lo > 0 && Math.abs(times[lo - 1] - t) <= Math.abs(times[lo] - t) ? lo - 1 : lo;
}
