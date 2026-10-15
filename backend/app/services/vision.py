"""Object detection on field / drone photos and video with a pretrained YOLOv8 model (Ultralytics, COCO classes)."""

from __future__ import annotations

import threading
import time
from collections import Counter
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.core.config import settings
from app.core.errors import SourceUnavailable

ALLOWED = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_ALLOWED = {".mp4", ".webm", ".mov", ".mkv", ".avi", ".ogv", ".m4v"}
MAX_PIXELS = 40_000_000
GROUPS = {
    "people": {"person"},
    "vehicles": {"car", "truck", "bus", "motorcycle", "bicycle", "train"},
    "boats": {"boat"},
    "animals": {"cow", "horse", "sheep", "dog", "elephant", "bird", "cat"},
}
LABEL_GROUP = {c: g for g, classes in GROUPS.items() for c in classes}
# Browsers decode H.264 MP4 and VP8 WebM; mp4v is a last resort that most browsers cannot play.
VIDEO_CODECS = (("avc1", ".mp4", "H.264"), ("VP80", ".webm", "VP8"), ("mp4v", ".mp4", "MPEG-4 Part 2"))
MIN_TRACK_FRAMES = 3

_model = None
_lock = threading.Lock()
_infer_lock = threading.Lock()
_video_lock = threading.Lock()


def _weights() -> str:
    weights = Path(settings.storage_dir) / "models" / settings.yolo_model
    weights.parent.mkdir(parents=True, exist_ok=True)
    return str(weights) if weights.is_file() else settings.yolo_model


def _new_model():
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SourceUnavailable("yolo", "ultralytics is not installed (pip install -r requirements.txt)") from exc
    model = YOLO(_weights())
    weights = Path(settings.storage_dir) / "models" / settings.yolo_model
    if not weights.is_file() and Path(settings.yolo_model).is_file():
        Path(settings.yolo_model).replace(weights)
    return model


def _load():
    global _model
    with _lock:
        if _model is None:
            _model = _new_model()
            _model.predict(np.zeros((64, 64, 3), np.uint8), verbose=False, device="cpu")
    return _model


def status() -> dict[str, Any]:
    try:
        import ultralytics

        return {"available": True, "model": settings.yolo_model, "framework": f"ultralytics {ultralytics.__version__}", "classes": "COCO-80", "loaded": _model is not None, "video_codec": video_codec()}
    except ImportError:
        return {"available": False, "model": settings.yolo_model, "detail": "ultralytics not installed"}


def decode(filename: str, data: bytes) -> np.ndarray:
    if Path(filename or "").suffix.lower() not in ALLOWED:
        raise ValueError("Unsupported image type")
    arr = np.frombuffer(data, dtype=np.uint8)
    head = cv2.imdecode(arr, cv2.IMREAD_REDUCED_GRAYSCALE_8)
    if head is None:
        raise ValueError("Could not decode image")
    if head.shape[0] * head.shape[1] * 64 > MAX_PIXELS:
        raise ValueError("Image dimensions too large")
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image")
    return img


def _boxes(res, min_conf: float = 0.0) -> list[dict[str, Any]]:
    names = res.names
    out = []
    ids = res.boxes.id.int().tolist() if res.boxes.id is not None else [None] * len(res.boxes)
    for b, tid in zip(res.boxes, ids, strict=True):
        c = float(b.conf)
        if c < min_conf:
            continue
        x1, y1, x2, y2 = (float(v) for v in b.xyxy[0].tolist())
        d: dict[str, Any] = {"label": names[int(b.cls)], "confidence": round(c, 3), "bbox": [round(x1), round(y1), round(x2), round(y2)]}
        if tid is not None:
            d["track_id"] = int(tid)
        out.append(d)
    return out


def detect(img: np.ndarray, conf: float = 0.25, render_conf: float | None = None) -> tuple[list[dict[str, Any]], np.ndarray, float]:
    """Run YOLO on one image. Detections are returned down to `conf`; the annotated image draws boxes >= render_conf."""
    model = _load()
    with _infer_lock:
        t0 = time.perf_counter()
        res = model.predict(img, conf=conf, verbose=False, device="cpu")[0]
        ms = (time.perf_counter() - t0) * 1000
    dets = _boxes(res)
    shown = res if render_conf is None or res.boxes.conf is None else res[res.boxes.conf >= render_conf]
    return dets, shown.plot(), ms


def summarize(dets: list[dict[str, Any]]) -> dict[str, Any]:
    by_label = Counter(d["label"] for d in dets)
    groups = {g: sum(by_label[c] for c in classes) for g, classes in GROUPS.items()}
    return {"by_label": dict(by_label), "groups": groups, "total": len(dets)}


# ---------------------------------------------------------------- video
def sample_plan(src_fps: float, total_frames: int, target_fps: float, max_seconds: float) -> tuple[int, int]:
    """(stride, frames_to_read): read every `stride`-th frame, at most `max_seconds` of footage."""
    fps = src_fps if src_fps and src_fps > 0 and np.isfinite(src_fps) else 25.0
    stride = max(1, round(fps / target_fps)) if target_fps > 0 else 1
    limit = int(fps * max_seconds) if max_seconds > 0 else 0
    frames = total_frames if total_frames > 0 else limit
    if limit:
        frames = min(frames, limit) if frames else limit
    return stride, frames


def video_summary(frames: list[dict[str, Any]], latencies_ms: list[float], min_track_frames: int = MIN_TRACK_FRAMES) -> dict[str, Any]:
    """Aggregate per-frame tracked detections into a counts timeline, peaks and distinct tracked objects.

    Tracks seen in fewer than `min_track_frames` sampled frames are not counted as distinct objects:
    they are mostly flicker or ByteTrack ID switches.
    """
    timeline = []
    peaks = dict.fromkeys(GROUPS, 0)
    peak_total = 0
    tracks: dict[str, set[int]] = {g: set() for g in GROUPS}
    track_labels: dict[int, Counter] = {}
    label_hits: Counter = Counter()
    for f in frames:
        counts = dict.fromkeys(GROUPS, 0)
        for d in f["detections"]:
            label_hits[d["label"]] += 1
            g = LABEL_GROUP.get(d["label"])
            if g:
                counts[g] += 1
            tid = d.get("track_id")
            if tid is not None:
                track_labels.setdefault(tid, Counter())[d["label"]] += 1
        for g, n in counts.items():
            peaks[g] = max(peaks[g], n)
        peak_total = max(peak_total, len(f["detections"]))
        timeline.append({"t": round(f["t"], 2), **counts, "total": len(f["detections"])})
    unique_by_label: Counter = Counter()
    track_labels = {tid: labels for tid, labels in track_labels.items() if labels.total() >= min_track_frames}
    for tid, labels in track_labels.items():
        label = labels.most_common(1)[0][0]
        unique_by_label[label] += 1
        g = LABEL_GROUP.get(label)
        if g:
            tracks[g].add(tid)
    total_ms = sum(latencies_ms)
    return {
        "frames_processed": len(frames),
        "timeline": timeline,
        "peak": {**peaks, "total": peak_total},
        "unique": {g: len(ids) for g, ids in tracks.items()},
        "unique_by_label": dict(unique_by_label),
        "unique_total": len(track_labels),
        "detections_by_label": dict(label_hits),
        "avg_ms": round(total_ms / len(latencies_ms), 1) if latencies_ms else None,
        "fps": round(1000 * len(latencies_ms) / total_ms, 1) if total_ms else None,
    }


def _open_writer(base: Path, fps: float, size: tuple[int, int]) -> tuple[cv2.VideoWriter, Path, str]:
    for fourcc, ext, name in VIDEO_CODECS:
        path = base.with_suffix(ext)
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*fourcc), fps, size)
        if writer.isOpened():
            return writer, path, name
        writer.release()
        path.unlink(missing_ok=True)
    raise SourceUnavailable("opencv", "No video encoder available in this OpenCV build")


_codec: str | None = None


def video_codec() -> str:
    """Name of the first encoder this OpenCV build can open (probed once)."""
    global _codec
    if _codec is None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            try:
                writer, _, _codec = _open_writer(Path(tmp) / "probe", 10, (64, 64))
                writer.release()
            except SourceUnavailable:
                _codec = "none"
    return _codec


def process_video(src: Path, out_base: Path, conf: float = 0.25, target_fps: float = 10, max_seconds: float = 20, max_width: int = 960) -> dict[str, Any]:
    """Track objects (YOLO + ByteTrack) on sampled frames and write an annotated, browser-playable video.

    `out_base` is the output path without extension; the codec decides .mp4 or .webm.
    """
    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        raise ValueError("Could not open video")
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if w <= 0 or h <= 0:
        cap.release()
        raise ValueError("Could not read video dimensions")
    stride, to_read = sample_plan(src_fps, total, target_fps, max_seconds)
    scale = min(1.0, max_width / w)
    size = (int(w * scale) // 2 * 2, int(h * scale) // 2 * 2)
    out_fps = src_fps / stride
    frames: list[dict[str, Any]] = []
    latencies: list[float] = []
    writer = None
    with _video_lock:
        model = _new_model()
        model.predict(np.zeros((64, 64, 3), np.uint8), verbose=False, device="cpu")
        try:
            writer, out_path, codec = _open_writer(out_base, out_fps, size)
            idx = 0
            while idx < to_read:
                ok, frame = cap.read()
                if not ok:
                    break
                if idx % stride == 0:
                    if scale < 1.0:
                        frame = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
                    elif frame.shape[1] != size[0] or frame.shape[0] != size[1]:
                        frame = cv2.resize(frame, size)
                    t0 = time.perf_counter()
                    res = model.track(frame, conf=conf, persist=True, tracker="bytetrack.yaml", verbose=False, device="cpu")[0]
                    latencies.append((time.perf_counter() - t0) * 1000)
                    frames.append({"t": idx / src_fps, "detections": _boxes(res)})
                    writer.write(res.plot())
                idx += 1
        finally:
            cap.release()
            if writer is not None:
                writer.release()
    if not frames:
        out_path.unlink(missing_ok=True)
        raise ValueError("No frames could be decoded from the video")
    return {
        "path": str(out_path),
        "codec": codec,
        "browser_playable": codec in {"H.264", "VP8"},
        "source": {"fps": round(src_fps, 2), "frames": total, "width": w, "height": h, "duration_s": round(total / src_fps, 1) if total else None},
        "processed": {"stride": stride, "fps": round(out_fps, 2), "width": size[0], "height": size[1], "seconds": round(frames[-1]["t"], 1), "conf": conf, "tracker": "ByteTrack", "min_track_frames": MIN_TRACK_FRAMES},
        **video_summary(frames, latencies),
    }
