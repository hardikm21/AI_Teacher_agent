#!/usr/bin/env bash
# Boot the backend (uvicorn) and frontend (next dev) together.
# Logs are interleaved with [api]/[web] prefixes; Ctrl-C kills both.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

prefix() { sed -e "s/^/[$1] /"; }
cleanup() {
  echo
  echo "Shutting down…"
  kill 0 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# ── backend ─────────────────────────────────────────────────────────────────
if [ ! -d "$ROOT/.venv" ]; then
  echo "==> Creating venv at $ROOT/.venv"
  python3 -m venv "$ROOT/.venv"
  "$ROOT/.venv/bin/pip" install --quiet --upgrade pip
  "$ROOT/.venv/bin/pip" install --quiet -r "$ROOT/requirements.txt"
fi

(
  cd "$ROOT/backend"
  "$ROOT/.venv/bin/uvicorn" app.main:app --reload --port 8000
) 2>&1 | prefix api &

# ── frontend ────────────────────────────────────────────────────────────────
if [ ! -d "$ROOT/frontend/node_modules" ]; then
  echo "==> Installing frontend deps"
  (cd "$ROOT/frontend" && npm install --silent)
fi

(
  cd "$ROOT/frontend"
  npm run dev
) 2>&1 | prefix web &

wait
