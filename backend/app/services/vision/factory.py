from pathlib import Path

from app.core.config import settings
from app.core.providers import ProviderUnavailableError
from app.services.vision.demo_model import DemoVisionModel
from app.services.vision.yolo_model import YOLOVisionModel


def get_vision_model():
    path = settings.yolo_weights_path
    if path and Path(path).is_file():
        return YOLOVisionModel(path)
    if settings.use_mock_providers:
        return DemoVisionModel()
    raise ProviderUnavailableError(
        "vision",
        "YOLO_WEIGHTS_PATH is not set or missing. DemoVisionModel is only available in Demo Mode "
        "(USE_MOCK_PROVIDERS=true).",
    )
