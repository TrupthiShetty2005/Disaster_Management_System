from dataclasses import dataclass, field
from typing import Protocol


DISASTER_CLASSES = [
    "person",
    "vehicle",
    "bus",
    "truck",
    "building",
    "bridge",
    "road",
    "damaged_building",
    "blocked_road",
    "flooded_vehicle",
    "fire",
    "rescue_person",
]

# COCO names that a generic pretrained YOLO actually has — never invent disaster classes.
COCO_TO_APP = {
    "person": "person",
    "car": "vehicle",
    "motorcycle": "vehicle",
    "bus": "bus",
    "truck": "truck",
}


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: list[float]  # x1,y1,x2,y2 pixel
    severity: str
    specialized: bool  # True only if demo/custom weights, not generic COCO


@dataclass
class VisionOutput:
    detections: list[Detection] = field(default_factory=list)
    masks: list[dict] = field(default_factory=list)
    model_name: str = ""
    backend: str = "demo"
    notes: str = ""


class VisionModel(Protocol):
    name: str

    def health(self) -> dict: ...

    def predict(self, image) -> VisionOutput: ...

    def detect(self, image) -> VisionOutput: ...

    def segment(self, image) -> VisionOutput: ...
