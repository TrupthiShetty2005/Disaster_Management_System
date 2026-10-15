# VisionGuard AI — AI models

This prototype **does not ship trained weights** and **does not auto-download** Ultralytics/YOLO checkpoints.

## Object detection (`VisionModel`)

| Implementation | When used | Classes |
|----------------|-----------|---------|
| `DemoVisionModel` | Default (CPU, no GPU) | Simulated disaster classes (person, vehicle, damaged_building, blocked_road, fire, …) |
| `YOLOVisionModel` | Only if `YOLO_WEIGHTS_PATH` points to an **existing local** file and `ultralytics` is installed | COCO-mapped: person, vehicle, bus, truck only |

A generic pretrained YOLO **does not** have `damaged_building`, `blocked_road`, `flooded_vehicle`, or `fire`. Those labels appear only in the demo backend.

Set `YOLO_WEIGHTS_PATH` to a local `.pt` you already have. Never pass a hub name that would trigger a download.

## Flood segmentation (`FloodSegModel`)

| Implementation | When used | Notes |
|----------------|-----------|-------|
| `DemoFloodModel` | Default | Blue-channel water mask (OpenCV/NumPy). **Not** trained semantic segmentation. |
| `UNetModel` / `DeepLabModel` | Not shipped | Raise `NotImplementedError` until local weights exist. |

## Damage assessment

`DamageAssessmentService` compares synthetic before/after rasters. Building classes: NO DAMAGE → DESTROYED. Road classes: OPEN → DESTROYED. Reports are JSON (`ReportRenderer.to_pdf` returns `None`).

## Other interfaces (`ai/services`)

| Contract | Current implementation |
|----------|------------------------|
| `FloodDetector` | Raster / GeoJSON stubs |
| `DamageClassifier` | Seeded classes |
| Satellite baseline CV | NumPy/OpenCV water/veg/burn/urban |

## Pipeline

Thresholds for early warning live in `backend/app/services/alerts/rules.json` (INFO / WATCH / WARNING / CRITICAL). Notification adapters are mock unless `ENABLE_REAL_*` is set; no live SMS/email client is wired.
