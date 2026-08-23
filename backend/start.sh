#!/bin/sh
set -e
echo "Running database migrations..."
alembic upgrade head
if [ "${SEED_ON_START:-false}" = "true" ]; then
    echo "Seeding initial data (idempotent)..."
    python -m scripts.seed || true
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${UVICORN_WORKERS:-2}"
