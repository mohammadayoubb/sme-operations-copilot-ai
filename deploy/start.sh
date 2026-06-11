#!/usr/bin/env bash
# Production entrypoint: migrations, then Celery worker + beat + API in one
# container. Backend and worker must share UPLOAD_DIR and ML_MODELS_DIR, so on
# platforms with per-service volumes (Railway) they run together, backed by a
# single volume mounted at /data.
set -e

export UPLOAD_DIR="${UPLOAD_DIR:-/data/uploads}"
export ML_MODELS_DIR="${ML_MODELS_DIR:-/data/ml_models}"
mkdir -p "$UPLOAD_DIR" "$ML_MODELS_DIR"

echo "Running database migrations..."
alembic upgrade head

echo "Starting Celery worker..."
celery -A app.workers.celery_app worker \
  --loglevel=info \
  -Q default,ocr,indexing,reports,forecasting \
  --concurrency=2 &

echo "Starting Celery beat..."
celery -A app.workers.celery_app beat \
  --loglevel=info \
  --schedule=/tmp/celerybeat-schedule &

echo "Starting API on port ${PORT:-8080}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"
