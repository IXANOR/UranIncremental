#!/usr/bin/env bash
# Run the Vite dev server (proxies /api/* → localhost:8000)
# Usage: bash scripts/run_frontend.sh

set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND="$REPO_ROOT/frontend"

cd "$FRONTEND"

if [ ! -d "node_modules" ]; then
  echo "Installing npm dependencies..."
  npm install
fi

echo ""
echo "Frontend running at http://localhost:5173"
echo "(proxies /api/* → http://localhost:8000 — start backend first)"
echo ""
npm run dev
