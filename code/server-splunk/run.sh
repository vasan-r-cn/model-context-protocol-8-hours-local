#!/usr/bin/env bash
# Start the Splunk MCP Server locally (SSE on :8050), pointed at the pod Splunk.
# Reads upstream/python/.env for SPLUNK_* connection settings.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PYDIR="$HERE/upstream/python"

if [ ! -d "$PYDIR/.venv" ]; then
  echo "Not installed yet — run ./setup.sh first." >&2
  exit 1
fi
if [ ! -f "$PYDIR/.env" ]; then
  echo "No .env in $PYDIR — cp $HERE/.env.example $PYDIR/.env and edit it." >&2
  exit 1
fi

cd "$PYDIR"
# TRANSPORT/HOST/PORT come from .env (defaults: sse / 0.0.0.0 / 8050).
exec ./.venv/bin/python server.py
