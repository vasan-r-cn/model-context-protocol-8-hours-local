#!/usr/bin/env bash
# Start the SD-WAN MCP server (Streamable HTTP on :7004), pointed at pod vManage.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

if [ ! -d .venv ]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv --python 3.12 .venv
    uv pip install --python .venv/bin/python -r requirements.txt
  else
    python3 -m venv .venv
    ./.venv/bin/pip install -r requirements.txt
  fi
fi
[ -f .env ] || { echo "No .env — cp .env.example .env and set VMANAGE_HOST + creds." >&2; exit 1; }

exec ./.venv/bin/python sdwan_mcp_server.py --host "${HOST:-0.0.0.0}" --port "${PORT:-7004}"
