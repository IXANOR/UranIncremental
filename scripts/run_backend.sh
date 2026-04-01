#!/usr/bin/env bash
# Run the FastAPI backend (uvicorn --reload)
# Usage: bash scripts/run_backend.sh

set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$REPO_ROOT/backend"

# ── .env check ───────────────────────────────────────────────────────────────
if [ ! -f "$BACKEND/.env" ]; then
  echo "ERROR: $BACKEND/.env not found."
  echo "       Copy and edit the example:"
  echo "         cp backend/.env.example backend/.env"
  exit 1
fi

# ── virtualenv / dependencies ─────────────────────────────────────────────────
cd "$BACKEND"
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python -m venv .venv
fi

source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate

echo "Installing / syncing dependencies..."
pip install -e ".[dev]" -q

# ── migrations + seed ─────────────────────────────────────────────────────────
echo "Running migrations..."
alembic upgrade head

echo "Seeding definitions..."
python -m app.db.seed

# ── start ─────────────────────────────────────────────────────────────────────
echo ""
echo "Backend running at http://localhost:8000"
echo "Swagger UI:         http://localhost:8000/docs"
echo ""
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
