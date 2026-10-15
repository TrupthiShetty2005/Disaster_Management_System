from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.db.init_db import init_db
from app.db.seed import seed_if_empty


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    init_db()
    # REAL DATA mode must not load Kuttanad/demo operational rows into the running app.
    if settings.use_mock_providers:
        seed_if_empty()
    from app.services.provenance import log_live_startup_banner

    log_live_startup_banner()
    yield


app = FastAPI(
    title="VisionGuard AI",
    description="Computer vision disaster management decision support (prototype).",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
def root():
    return {"service": "VisionGuard AI", "docs": "/docs", "api": settings.api_v1_prefix}
