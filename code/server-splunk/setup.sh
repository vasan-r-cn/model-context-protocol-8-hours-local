#!/usr/bin/env bash
# Fetch and install the Splunk MCP Server (splunk/splunk-mcp-server2, MIT).
#
# This is a third-party, UNOFFICIAL community server. We do not vendor its
# source into this repo; we clone a pinned ref into upstream/ at setup time so
# the exact code is reproducible and auditable. It runs LOCALLY on the
# participant desktop and talks to the pod's Splunk over the REST API (:8089).
#
# Usage:
#   ./setup.sh                 # clone + create venv + install
#   SPLUNK_MCP_REF=<sha> ./setup.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
UPSTREAM="$HERE/upstream"
REPO="https://github.com/splunk/splunk-mcp-server2.git"
REF="${SPLUNK_MCP_REF:-main}"   # pin to a commit SHA once verified on the pod image

if [ ! -d "$UPSTREAM/.git" ]; then
  echo "== cloning $REPO ($REF) into upstream/ =="
  git clone "$REPO" "$UPSTREAM"
fi
git -C "$UPSTREAM" fetch --all --quiet || true
git -C "$UPSTREAM" checkout "$REF"

# The python implementation lives in upstream/python/.
cd "$UPSTREAM/python"
if command -v uv >/dev/null 2>&1; then
  uv venv --python 3.12 .venv
  uv pip install --python .venv/bin/python -e .
else
  python3 -m venv .venv
  ./.venv/bin/pip install -e .
fi

echo
echo "Installed. Next:"
echo "  1. cp $HERE/.env.example $UPSTREAM/python/.env   # then edit it"
echo "  2. $HERE/run.sh                                  # starts SSE on :8050"
