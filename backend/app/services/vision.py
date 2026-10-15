"""Object detection on field / drone photos with a pretrained YOLOv8 model (Ultralytics, COCO classes)."""

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
MAX_PIXELS = 40_000_000
GROUPS = {
    "people": {"person"},
    "vehicles": {"car", "truck", "bus", "motorcycle", "bicycle", "train"},
    "boats": {"boat"},
    "animals": {"cow", "horse", "sheep", "dog", "elephant", "bird", "cat"},
}

_model = None
_lock = threading.Lock()


def _load():
    global _model
    with _lock:
        if _model is None:
            try:
                from ultralytics import YOLO
            except ImportError as exc:
                raise SourceUnavailable("yolo", "ultralytics is not installed (pip install -r requirements.txt)") from exc
            weights = Path(settings.storage_dir) / "models" / settings.yolo_model
            weights.parent.mkdir(parents=True, exist_ok=True)
            _model = YOLO(str(weights) if weights.is_file() else settings.yolo_model)
            if not weights.is_file() and Path(settings.yolo_model).is_file():
                Path(settings.yolo_model).replace(weights)
    return _model


def status() -> dict[str, Any]:
    try:
        import ultralytics

        return {"available": True, "model": settings.yolo_model, "framework": f"ultralytics {ultralytics.__version__}", "classes": "COCO-80", "loaded": _model is not None}
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


def detect(img: np.ndarray, conf: float = 0.25) -> tuple[list[dict[str, Any]], np.ndarray, float]:
    model = _load()
    t0 = time.perf_counter()
    res = model.predict(img, conf=conf, verbose=False, device="cpu")[0]
    ms = (time.perf_counter() - t0) * 1000
    names = res.names
    dets = []
    for b in res.boxes:
        x1, y1, x2, y2 = (float(v) for v in b.xyxy[0].tolist())
        dets.append({"label": names[int(b.cls)], "confidence": round(float(b.conf), 3), "bbox": [round(x1), round(y1), round(x2), round(y2)]})
    annotated = res.plot()
    return dets, annotated, ms


def summarize(dets: list[dict[str, Any]]) -> dict[str, Any]:
    by_label = Counter(d["label"] for d in dets)
    groups = {g: sum(by_label[c] for c in classes) for g, classes in GROUPS.items()}
    return {"by_label": dict(by_label), "groups": groups, "total": len(dets)}
