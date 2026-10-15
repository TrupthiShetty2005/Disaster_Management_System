from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.providers import ProviderUnavailableError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProviderUnavailableError)
    async def provider_unavailable_handler(_request: Request, exc: ProviderUnavailableError):
        return JSONResponse(
            status_code=503,
            content={
                "detail": exc.message,
                "code": "provider_unavailable",
                "provider": exc.provider,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
        code = "http_error"
        if exc.status_code == 404:
            code = "not_found"
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": code},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "code": "internal_error"},
        )
