from pathlib import Path

from fastapi import HTTPException

from app.core.config import settings

ALLOWED = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def validate_upload(filename: str, data: bytes) -> None:
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    suffix = Path(filename or "upload.jpg").suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(status_code=400, detail="Unsupported image type")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(status_code=400, detail="File exceeds upload limit")
    if data[:8] != b"\x89PNG\r\n\x1a\n" and data[:3] != b"\xff\xd8\xff" and data[:2] != b"BM":
        # allow webp RIFF
        if data[:4] != b"RIFF":
            raise HTTPException(status_code=400, detail="File is not a recognizable image")
