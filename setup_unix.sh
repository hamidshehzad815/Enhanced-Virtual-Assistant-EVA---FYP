#!/usr/bin/env bash
set -euo pipefail

START_SERVICES="${1:-}"

step() {
  echo
  echo "==> $1"
}

require_cmd() {
  local name="$1"
  local hint="$2"
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "Missing required command '$name'. $hint" >&2
    exit 1
  fi
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/Eva_Backend_Server"
AI_DIR="$ROOT_DIR/Eva_AI_Server"
AI_VENV_DIR="$AI_DIR/.venv"
AI_VENV_PYTHON="$AI_VENV_DIR/bin/python"

step "Checking required tools"
require_cmd node "Install Node.js 18+."
require_cmd npm "Install npm with Node.js."
require_cmd python3 "Install Python 3.11+."
require_cmd docker "Install Docker."

step "Installing backend dependencies"
cd "$BACKEND_DIR"
if [[ -f package-lock.json ]]; then
  npm ci
else
  npm install
fi

step "Preparing AI virtual environment"
if [[ ! -x "$AI_VENV_PYTHON" ]]; then
  cd "$AI_DIR"
  python3 -m venv .venv
fi

step "Installing AI dependencies"
"$AI_VENV_PYTHON" -m pip install --upgrade pip
"$AI_VENV_PYTHON" -m pip install -r "$AI_DIR/requirements.txt"

step "Environment file check"
[[ -f "$BACKEND_DIR/.env" ]] || echo "Warning: Eva_Backend_Server/.env is missing."
[[ -f "$AI_DIR/.env" ]] || echo "Warning: Eva_AI_Server/.env is missing."

echo
echo "Setup complete."
echo
echo "Start commands:"
echo "1) MongoDB: mongod --dbpath <YOUR_DB_PATH>"
echo "2) Duckling: docker run --rm -p 8000:8000 rasa/duckling"
echo "3) Backend:  cd Eva_Backend_Server && npm run dev"
echo "4) AI:       cd Eva_AI_Server && ./.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload"

if [[ "$START_SERVICES" == "--start" ]]; then
  step "Starting Duckling, Backend, and AI in background"
  (docker run --rm -p 8000:8000 rasa/duckling >/tmp/eva_duckling.log 2>&1 &)
  (cd "$BACKEND_DIR" && npm run dev >/tmp/eva_backend.log 2>&1 &)
  (cd "$AI_DIR" && ./.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload >/tmp/eva_ai.log 2>&1 &)
  echo "Services started in background. Make sure MongoDB is running."
  echo "Logs: /tmp/eva_duckling.log /tmp/eva_backend.log /tmp/eva_ai.log"
fi
