FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=180 \
    DATABASE_URL=sqlite:////data/visionguard.db \
    STORAGE_DIR=/data/storage \
    CACHE_DIR=/data/storage/cache \
    YOLO_MODEL=yolov8n.pt \
    CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# rasterio/shapely wheels bundle GDAL, PROJ, and GEOS. OpenCV and video IO need
# the system GL, glib, gomp, and ffmpeg libraries on slim images.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libexpat1 \
        libgomp1 \
        libglib2.0-0 \
        libgl1 \
        libsm6 \
        libxext6 \
        libxrender1 \
        ffmpeg \
        gdal-bin \
        libgdal32 \
        libproj25 \
        proj-data \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
# Default PyPI torch pulls multi-gigabyte CUDA libraries. The CPU wheel is enough.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu 'torch==2.14.1+cpu' \
    && pip install --no-cache-dir -r requirements.txt \
    && python -c "import fastapi, rasterio, shapely, cv2, numpy, ultralytics, lap, torch; assert '+cpu' in torch.__version__, torch.__version__"

COPY backend/app ./app
COPY backend/visionguard.db /opt/visionguard-seed/visionguard.db
COPY backend/storage/analyses /opt/visionguard-seed/storage/analyses
COPY backend/storage/vision /opt/visionguard-seed/storage/vision
COPY backend/storage/models /opt/visionguard-seed/storage/models
COPY backend/storage/previews /opt/visionguard-seed/storage/previews
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
