#!/usr/bin/env bash
# One-time setup on a pod desktop (linuxdesktop64 / linuxdesktop65).
#
#   cd ~/mcp-8-hours && ./scripts/bootstrap_desktop.sh
#
# Builds both virtualenvs on Python 3.12 without touching the system Python.
# The pod image ships 3.10; uv fetches a private 3.12 instead of upgrading
# anything, which keeps the image's own tooling intact.
set -euo pipefail

# Locate the workshop root (the directory containing code/server/app/main.py).
# These scripts get copied around — into a home directory, next to code/, or
# left in scripts/ — so find the root rather than assuming a layout.
find_workshop_root() {
  local here d
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  for d in "${WORKSHOP_ROOT:-}" "$here/.." "$here" "$PWD"; do
    [ -n "$d" ] && [ -f "$d/code/server/app/main.py" ] && { (cd "$d" && pwd); return 0; }
  done
  # Walk up from the script location and from the current directory.
  for d in "$here" "$PWD"; do
    while [ "$d" != "/" ] && [ -n "$d" ]; do
      [ -f "$d/code/server/app/main.py" ] && { echo "$d"; return 0; }
      d="$(dirname "$d")"
    done
  done
  return 1
}

if ! ROOT="$(find_workshop_root)"; then
  printf '\033[31mCannot find the workshop files.\033[0m\n\n'
  printf 'Looked for code/server/app/main.py near:\n'
  printf '  %s   (this script)\n' "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  printf '  %s   (current directory)\n\n' "$PWD"
  printf 'Fix by doing one of:\n'
  printf '  cd <dir containing code/>  && %s\n' "$(basename "${BASH_SOURCE[0]}")"
  printf '  WORKSHOP_ROOT=<dir containing code/> %s\n' "$(basename "${BASH_SOURCE[0]}")"
  exit 2
fi
cd "$ROOT"
echo "workshop root: $ROOT"

echo "== 1. uv =="
if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # shellcheck disable=SC1091
  . "$HOME/.local/bin/env" 2>/dev/null || export PATH="$HOME/.local/bin:$PATH"
fi
echo "uv: $(uv --version)"

echo
echo "== 2. Python 3.12 (private to uv — the system python3 is left alone) =="
uv python install 3.12
echo "3.12 at: $(uv python find 3.12)"

echo
echo "== 3. MCP server venv =="
rm -rf code/server/.venv
uv venv --python 3.12 code/server/.venv
uv pip install --python code/server/.venv/bin/python -r code/server/requirements.txt
code/server/.venv/bin/python -c "import mcp, netmiko, yaml, pytest; print('server deps OK')"

echo
echo "== 4. fast-agent venv =="
rm -rf code/client-fastagent/.venv
uv venv --python 3.12 code/client-fastagent/.venv
uv pip install --python code/client-fastagent/.venv/bin/python -r code/client-fastagent/requirements.txt
echo "fast-agent: $(code/client-fastagent/.venv/bin/fast-agent --version 2>&1 | tail -1)"

echo
echo "== 5. Offline checks (no device needed) =="
(cd code/server && .venv/bin/python -m pytest --color=no | tail -1)

cat <<'NEXT'

Done. Next:

  ./scripts/sanity_check.sh          # full ladder, including device reachability

If check 3 fails on every device, this desktop has no route to the management
subnet — that is a pod networking question, not a code problem.
NEXT
