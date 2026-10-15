"""Ultralytics YOLO adapter. Loads local weights only — never downloads."""

from pathlib import Path

import numpy as np

from app.services.vision.demo_model import DemoVisionModel
from app.services.vision.protocol import COCO_TO_APP, Detection, VisionOutput
from app.services.vision.severity import detection_severity


class YOLOVisionModel:
    name = "yolo-local"

    def __init__(self, weights_path: str):
        self.weights_path = Path(weights_path)
        self._model = None
        self._fallback = DemoVisionModel()

    def health(self) -> dict:
        exists = self.weights_path.is_file()
        return {
            "ok": exists,
            "backend": "yolo" if exists else "unavailable",
            "gpu_required": False,
            "weights": str(self.weights_path),
            "specialized_disaster_classes": False,
            "note": (
                "Generic YOLO weights expose COCO classes only (person/vehicle/bus/truck). "
                "Disaster-specific labels are not implied."
                if exists
                else "Weights file missing; factory will use DemoVisionModel."
            ),
        }

    def _load(self):
        if self._model is not None:
            return self._model
        if not self.weights_path.is_file():
            raise FileNotFoundError(self.weights_path)
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("ultralytics is not installed") from exc
        self._model = YOLO(str(self.weights_path))
        return self._model

    def predict(self, image: np.ndarray) -> VisionOutput:
        return self.detect(image)

    def detect(self, image: np.ndarray) -> VisionOutput:
        from app.core.config import settings

        try:
            model = self._load()
        except (FileNotFoundError, RuntimeError) as exc:
            if not settings.use_mock_providers:
                raise RuntimeError(
                    "YOLO weights unavailable in Real Data Mode; DemoVisionModel fallback is disabled. "
                    "Set YOLO_WEIGHTS_PATH or enable Demo Mode (USE_MOCK_PROVIDERS=true)."
                ) from exc
            out = self._fallback.detect(image)
            out.notes = "YOLO unavailable; used DemoVisionModel (Demo Mode only)."
            return out
        results = model.predict(image, verbose=False, device="cpu")
        detections: list[Detection] = []
        names = results[0].names if results else {}
        boxes = results[0].boxes if results else []
        for box in boxes:
            cls_id = int(box.cls[0])
            raw = names.get(cls_id, str(cls_id))
            label = COCO_TO_APP.get(raw)
            if not label:
                continue
            xyxy = [float(x) for x in box.xyxy[0].tolist()]
            conf = float(box.conf[0])
            detections.append(
                Detection(
                    label=label,
                    confidence=round(conf, 3),
                    bbox=xyxy,
                    severity=detection_severity(label, conf),
                    specialized=False,
                )
            )
        return VisionOutput(
            detections=detections,
            model_name=f"yolo:{self.weights_path.name}",
            backend="yolo",
            notes="Mapped from COCO labels only. No damaged_building/fire/blocked_road from this checkpoint.",
        )

    def segment(self, image: np.ndarray) -> VisionOutput:
        out = self.detect(image)
        out.masks = [{"label": d.label, "bbox": d.bbox} for d in out.detections]
        return out
