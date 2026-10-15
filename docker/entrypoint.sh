#!/bin/sh
# Seed the writable data volume from files baked into the image, then start the API.
# Existing analyses, the vision gallery, and YOLO weights show up on first run.
# Later uploads stay on the volume and are not overwritten.
set -eu

SEED=/opt/visionguard-seed
DATA=/data

mkdir -p \
  "$DATA/storage/cache" \
  "$DATA/storage/analyses" \
  "$DATA/storage/vision" \
  "$DATA/storage/models" \
  "$DATA/storage/previews"

if [ ! -s "$DATA/visionguard.db" ]; then
  cp "$SEED/visionguard.db" "$DATA/visionguard.db"
fi

if [ ! -f "$DATA/storage/vision/gallery/results.json" ]; then
  cp -a "$SEED/storage/vision/." "$DATA/storage/vision/"
fi

if [ -z "$(find "$DATA/storage/analyses" -type f -print -quit)" ]; then
  cp -a "$SEED/storage/analyses/." "$DATA/storage/analyses/"
fi

if [ ! -f "$DATA/storage/models/yolov8n.pt" ]; then
  cp -a "$SEED/storage/models/." "$DATA/storage/models/"
fi

if [ -d "$SEED/storage/previews" ] && [ -z "$(find "$DATA/storage/previews" -type f -print -quit)" ]; then
  cp -a "$SEED/storage/previews/." "$DATA/storage/previews/"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
