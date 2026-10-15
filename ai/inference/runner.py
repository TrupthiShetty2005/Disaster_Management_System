from services.damage import StubDamageClassifier
from services.flood import StubFloodDetector


def run_stub_pipeline(image_path: str) -> dict:
    flood = StubFloodDetector().detect(image_path)
    damage = StubDamageClassifier().classify(image_path)
    return {"flood": flood, "damage": damage}
