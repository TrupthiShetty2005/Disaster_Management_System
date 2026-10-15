# AI guide

The running product’s “AI” lives under **`backend/app/services/`**. The **`ai/`** directory is a **separate stub package** (`ai/inference/runner.py`) that FastAPI **does not import**.

There is **no PyTorch**, **no EfficientNet**, **no Random Forest / XGBoost / LSTM / Transformer** implementation in this repository. U-Net and DeepLab are **class names that raise `NotImplementedError`**.

---

## 1. Flood segmentation (runtime)

| | |
| --- | --- |
| Problem | Estimate water extent on a demo raster |
| Input | Synthetic RGB from `generate_demo_raster` (not a real satellite file) |
| Processing | `preprocess` then blue-channel `detect_water` |
| Algorithm | **HEURISTIC** OpenCV/NumPy |
| Model name | `demo-flood-seg-v0` (`DemoFloodModel`) |
| Output | mask, polygons, heatmap GeoJSON, area, severity |
| API | `POST /api/v1/flood/analyze` |
| UI | `/flood-detection` |
| Example | Notes string says not a trained U-Net |
| Limitations | No trained weights; area depends on generated pixels |

`UNetModel` / `DeepLabModel`: **Specified as placeholders, not currently implemented** (`NotImplementedError`).

`ai/services/flood.py` `StubFloodDetector`: **MOCK** dict (`water_extent_km2: 34.5`); tests only.

---

## 2. Satellite scene analysis

| | |
| --- | --- |
| Problem | Water/veg/burn/urban metrics on a scene |
| Input | Synthetic raster keyed by scene id |
| Algorithm | **HEURISTIC** channel thresholds |
| Output | GeoJSON + metrics JSON |
| API | `POST /api/v1/satellite/analyze`, `POST /api/v1/satellite/compare` |
| UI | `/satellite`, `/satellite/compare` |
| Classification | **SIMULATION** of Sentinel-2/Landsat; provider is mock |

---

## 3. Damage / change detection

| | |
| --- | --- |
| Problem | Before/after building and road classes |
| Input | Two generated rasters |
| Algorithm | Pixel change fractions + **RULE-BASED** `classify_building` / `classify_road` |
| Output | JSON report, overlay GeoJSON |
| API | `POST /api/v1/damage/analyze` |
| UI | `/damage-assessment` |
| Classification | **HEURISTIC + RULE-BASED**, not a trained damage net |
| PDF | **NOT IMPLEMENTED** |

---

## 4. Computer vision (objects)

| | |
| --- | --- |
| Problem | Boxes on an uploaded photo |
| Input | JPEG/PNG/WebP/BMP bytes |
| Default model | `DemoVisionModel` (`demo-vision-v0`) **MOCK** — deterministic boxes from image size hash |
| Optional | `YOLOVisionModel` if `YOLO_WEIGHTS_PATH` is an existing file; Ultralytics on **CPU**; COCO subset only; **ultralytics not in requirements.txt** |
| Output | detections, severity, incident headline, annotated JPEG |
| API | `POST /api/v1/vision/detect` or `/analyze` |
| UI | `/computer-vision` |
| GPU | `gpu_required: false` |

Does **not** automatically write rescue priorities.

---

## 5. Flood / cyclone / rainfall “risk AI”

| | |
| --- | --- |
| Problem | Probability-like scores for operators |
| Algorithm | **RULE-BASED** weighted formulas (`risk/flood.py`, `cyclone.py`, `rainfall.py`) |
| Overlay | If mock providers: **SIMULATED** 82% flood (`overlay_demo_flood`) |
| Label | `Prototype AI Risk Estimate` / SIMULATED DATA |
| API | `/risk/flood`, `/risk/cyclone`, `/weather/rainfall` |
| UI | Weather and Risk Intelligence pages |

---

## 6. Rescue recommendation

| | |
| --- | --- |
| Algorithm | **RULE-BASED** `recommend_resources` + weighted `RescuePriorityService` + graph `shortest_path` |
| Classification | **RULE-BASED** / **SIMULATION** (demo road graph, not live routing APIs) |
| API | `/rescue/plan` |
| UI | `/rescue-planning` |

---

## 7. Alert engine

| | |
| --- | --- |
| Algorithm | **RULE-BASED** thresholds in `alerts/rules.json` |
| Classification | **RULE-BASED**; alerts are prototype, not government products |

---

## Honesty labels in UI

`EstimateCallout` / `SafetyBanner` tell the operator the output class. Demo Mode does not make detections “real YOLO disaster models.”
