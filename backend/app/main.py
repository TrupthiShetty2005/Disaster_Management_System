import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.errors import SourceUnavailable, register_exception_handlers
from app.db import SessionLocal, init_db

log = logging.getLogger("visionguard")
_stop = threading.Event()


def _background() -> None:
    """Warm slow reference data, then refresh alerts on a fixed interval."""
    from app.geo import karnataka
    from app.geo.karnataka import RIVER_STATIONS
    from app.services import alerts, water
    from app.sources import osm

    for task in (karnataka.karnataka_boundary, karnataka.district_boundaries, osm.emergency_facilities):
        try:
            task()
        except SourceUnavailable as exc:
            log.warning("warmup %s failed: %s", task.__name__, exc.message)
    for st in RIVER_STATIONS:
        if _stop.is_set():
            return
        try:
            water.thresholds(st.id)
        except SourceUnavailable as exc:
            log.warning("thresholds %s failed: %s", st.id, exc.message)
    if settings.vision_gallery_autobuild:
        from app.services import vision_gallery

        vision_gallery.start_build()
    while not _stop.is_set():
        db = SessionLocal()
        try:
            alerts.refresh(db)
        except Exception:
            log.exception("alert refresh failed")
        finally:
            db.close()
        _stop.wait(settings.refresh_interval_min * 60)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    init_db()
    _stop.clear()
    threading.Thread(target=_background, name="live-refresh", daemon=True).start()
    yield
    _stop.set()


app = FastAPI(title="VisionGuard AI — Karnataka", description="Live disaster monitoring for Karnataka: floods, fires and infrastructure impact.", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_methods=["*"], allow_headers=["*"])
register_exception_handlers(app)
app.include_router(router, prefix="/api/v1")


@app.get("/")
def root():
    return {"service": settings.app_name, "docs": "/docs", "api": "/api/v1"}
