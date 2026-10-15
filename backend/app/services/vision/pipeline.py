import json
import time
from dataclasses import asdict

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.db.session import new_uuid
from app.models import VisionJob
from app.services.vision.factory import get_vision_model
from app.services.vision.incident import incident_summary
from app.services.vision.severity import scene_severity
from app.services.vision.storage import LocalStorage
from app.services.vision.validation import validate_upload


def decode_image(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return image


def annotate(image: np.ndarray, detections: list[dict]) -> np.ndarray:
    canvas = image.copy()
    for det in detections:
        x1, y1, x2, y2 = [int(v) for v in det["bbox"]]
        cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 180, 255), 2)
        label = f"{det['label']} {det['confidence']:.2f}"
        cv2.putText(canvas, label, (x1, max(16, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    return canvas


class VisionPipeline:
    def __init__(self, db: Session, storage: LocalStorage | None = None):
        self.db = db
        self.storage = storage or LocalStorage()
        self.model = get_vision_model()

    def run(self, filename: str, data: bytes, mode: str = "analyze") -> VisionJob:
        validate_upload(filename, data)
        image = decode_image(data)
        if image is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=400, detail="Could not decode image")
        job_id = new_uuid()
        upload = self.storage.upload_path(job_id, filename)
        upload.write_bytes(data)
        t0 = time.perf_counter()
        if mode == "segment":
            output = self.model.segment(image)
        else:
            output = self.model.detect(image)
        elapsed = (time.perf_counter() - t0) * 1000
        detections = [asdict(d) for d in output.detections]
        level, score, why = scene_severity(detections)
        incident = incident_summary(detections)
        incident["severity_rationale"] = why
        incident["severity_score"] = score
        annotated = annotate(image, detections)
        ann_path = self.storage.annotated_path(job_id)
        cv2.imwrite(str(ann_path), annotated)
        payload = {
            "detections": detections,
            "incident": incident,
            "notes": output.notes,
            "masks": output.masks,
        }
        self.storage.result_path(job_id).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        job = VisionJob(
            id=job_id,
            original_filename=filename,
            upload_path=str(upload),
            annotated_path=str(ann_path),
            model_name=output.model_name,
            backend=output.backend,
            overall_severity=level,
            processing_ms=round(elapsed, 2),
            detections=detections,
            incident=incident,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job
