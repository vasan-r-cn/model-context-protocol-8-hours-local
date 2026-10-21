#!/bin/bash
# Starts the Cisco MCP Server (Streamable HTTP at /mcp, health check at /).
# First run: creates .venv/ and installs requirements.txt automatically.
set -e
cd "$(dirname "$0")"

# Load local overrides if present (see .env.example)
if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

VENV=.venv

# Create the venv if it is missing OR unusable. A venv carries absolute paths,
# so one that was copied or had its parent directory renamed still looks
# present but its scripts point at an interpreter that no longer exists.
if [ ! -x "$VENV/bin/python" ] || ! "$VENV/bin/python" -c "import sys" >/dev/null 2>&1; then
  if [ -e "$VENV" ]; then
    echo "Existing $VENV is unusable (moved or renamed?) — rebuilding."
    rm -rf "$VENV"
  fi
  for PY in python3.12 python3.11 python3; do
    command -v "$PY" >/dev/null 2>&1 && break
  done
  echo "Creating virtualenv in $VENV with $PY..."
  "$PY" -m venv "$VENV"
fi

# Install requirements if not already installed
if ! "$VENV/bin/python" -c "import uvicorn, fastapi, mcp, netmiko" >/dev/null 2>&1; then
  echo "Installing requirements..."
  "$VENV/bin/python" -m pip install --upgrade pip -q
  "$VENV/bin/python" -m pip install -r requirements.txt
fi

# Bind address (override via HOST/PORT env or .env if 8000 is taken)
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

echo "Starting Cisco MCP Server on http://$HOST:$PORT (MCP endpoint: /mcp)..."
exec "$VENV/bin/python" -m uvicorn app.main:app --host "$HOST" --port "$PORT"
