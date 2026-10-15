import hashlib

import numpy as np

from app.services.vision.protocol import DISASTER_CLASSES, Detection, VisionOutput
from app.services.vision.severity import detection_severity


class DemoVisionModel:
    """Deterministic boxes for disaster classes. Not a trained detector."""

    name = "demo-vision-v0"

    def health(self) -> dict:
        return {
            "ok": True,
            "backend": "demo",
            "gpu_required": False,
            "specialized_disaster_classes": True,
            "note": "DemoVisionModel simulates disaster classes. Not Ultralytics YOLO.",
        }

    def predict(self, image: np.ndarray) -> VisionOutput:
        return self.detect(image)

    def detect(self, image: np.ndarray) -> VisionOutput:
        h, w = image.shape[:2]
        digest = hashlib.sha256(f"{w}x{h}".encode()).digest()
        detections: list[Detection] = []
        specs = [
            ("person", 0.12, 0.55, 0.08, 0.22, 0.86),
            ("vehicle", 0.40, 0.62, 0.18, 0.16, 0.81),
            ("bus", 0.62, 0.58, 0.22, 0.18, 0.74),
            ("truck", 0.18, 0.70, 0.16, 0.14, 0.77),
            ("building", 0.68, 0.18, 0.24, 0.32, 0.71),
            ("damaged_building", 0.72, 0.22, 0.16, 0.20, 0.69),
            ("road", 0.05, 0.82, 0.90, 0.10, 0.64),
            ("blocked_road", 0.35, 0.80, 0.28, 0.12, 0.72),
            ("bridge", 0.08, 0.42, 0.30, 0.10, 0.66),
            ("flooded_vehicle", 0.48, 0.74, 0.14, 0.12, 0.70),
            ("fire", 0.22, 0.20, 0.10, 0.12, 0.78),
            ("rescue_person", 0.28, 0.50, 0.07, 0.16, 0.83),
        ]
        for i, (label, nx, ny, nw, nh, conf) in enumerate(specs):
            if digest[i] < 40:
                continue
            x1 = int(nx * w)
            y1 = int(ny * h)
            x2 = int((nx + nw) * w)
            y2 = int((ny + nh) * h)
            detections.append(
                Detection(
                    label=label,
                    confidence=round(conf, 2),
                    bbox=[x1, y1, x2, y2],
                    severity=detection_severity(label, conf),
                    specialized=True,
                )
            )
        if not detections:
            detections.append(
                Detection(
                    label="person",
                    confidence=0.61,
                    bbox=[int(0.1 * w), int(0.2 * h), int(0.2 * w), int(0.5 * h)],
                    severity=detection_severity("person", 0.61),
                    specialized=True,
                )
            )
        return VisionOutput(
            detections=detections,
            model_name=self.name,
            backend="demo",
            notes="Simulated disaster classes for prototype ops. Not a pretrained YOLO taxonomy.",
        )

    def segment(self, image: np.ndarray) -> VisionOutput:
        out = self.detect(image)
        out.masks = [
            {"label": d.label, "bbox": d.bbox, "confidence": d.confidence} for d in out.detections[:4]
        ]
        out.notes += " Segment masks are box proxies in the demo backend."
        return out
