from typing import Any, Protocol


class DamageClassifier(Protocol):
    def classify(self, image_path: str) -> dict[str, Any]: ...


class StubDamageClassifier:
    def classify(self, image_path: str) -> dict[str, Any]:
        return {
            "model": "stub-damage-v0",
            "image_path": image_path,
            "damage_class": "moderate",
            "confidence": 0.72,
            "note": "Package stub. Runtime uses DamageAssessmentService (change detection, not a trained classifier).",
        }
