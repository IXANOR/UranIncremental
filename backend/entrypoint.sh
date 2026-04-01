#!/bin/bash
# Backend container entrypoint.
# Runs migrations and seed before starting the application server.
set -e

echo "[entrypoint] Running database migrations..."
alembic upgrade head

echo "[entrypoint] Seeding static game data..."
python -m app.db.seed

echo "[entrypoint] Starting application..."
exec "$@"
