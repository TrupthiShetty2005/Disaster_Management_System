from pathlib import Path

from app.core.config import settings

ALLOWED_SUFFIX = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def safe_image_suffix(filename: str) -> str:
    name = Path(filename.replace("\\", "/")).name
    suffix = Path(name).suffix.lower()
    return suffix if suffix in ALLOWED_SUFFIX else ".jpg"


class LocalStorage:
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.vision_storage_dir)
        for name in ("uploads", "processed", "results"):
            (self.root / name).mkdir(parents=True, exist_ok=True)

    def upload_path(self, job_id: str, filename: str) -> Path:
        return self.root / "uploads" / f"{job_id}{safe_image_suffix(filename)}"

    def annotated_path(self, job_id: str) -> Path:
        return self.root / "processed" / f"{job_id}_annotated.jpg"

    def result_path(self, job_id: str) -> Path:
        return self.root / "results" / f"{job_id}.json"
