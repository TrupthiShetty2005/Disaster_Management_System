import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

log = logging.getLogger("visionguard")


class SourceUnavailable(Exception):
    """A live upstream source failed. Surfaced as HTTP 503; never replaced with substitute data."""

    def __init__(self, source: str, message: str):
        super().__init__(message)
        self.source = source
        self.message = message


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(SourceUnavailable)
    async def _source_unavailable(_req: Request, exc: SourceUnavailable):
        log.warning("source unavailable: %s: %s", exc.source, exc.message)
        return JSONResponse(status_code=503, content={"error": "source_unavailable", "source": exc.source, "detail": exc.message})

    @app.exception_handler(Exception)
    async def _unhandled(_req: Request, exc: Exception):
        log.exception("unhandled error", exc_info=exc)
        return JSONResponse(status_code=500, content={"error": "internal_error", "detail": "Internal server error"})
