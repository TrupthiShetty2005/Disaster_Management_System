"""Explainable severity from class, confidence, and scene counts."""

HIGH_IMPACT = {"fire", "damaged_building", "blocked_road", "flooded_vehicle", "rescue_person"}
MEDIUM_IMPACT = {"person", "truck", "bus", "bridge"}


def class_weight(label: str) -> float:
    if label in HIGH_IMPACT:
        return 1.0
    if label in MEDIUM_IMPACT:
        return 0.6
    return 0.35


def detection_severity(label: str, confidence: float) -> str:
    score = class_weight(label) * 70 + confidence * 30
    return score_to_level(score)


def score_to_level(score: float) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def scene_severity(detections: list[dict]) -> tuple[str, float, str]:
    if not detections:
        return "low", 0.0, "No objects of operational interest."
    n = len(detections)
    avg_conf = sum(d["confidence"] for d in detections) / n
    impact = sum(class_weight(d["label"]) for d in detections) / n
    critical_n = sum(1 for d in detections if d["label"] in HIGH_IMPACT)
    score = min(100.0, impact * 50 + avg_conf * 25 + min(n, 12) * 2.5 + critical_n * 8)
    level = score_to_level(score)
    why = (
        f"{n} objects, avg confidence {avg_conf:.2f}, "
        f"{critical_n} high-impact classes (fire/damage/blockage/flooded vehicle/rescue)."
    )
    return level, round(score, 1), why
