#!/usr/bin/env bash
# Pre-flight sanity check — run on a participant desktop.
#
# Works through the chain in dependency order: desktop -> devices -> server ->
# protocol -> client -> safety -> shared services. Read the FIRST failure.
#
#   ./scripts/sanity_check.sh                        full ladder
#   ./scripts/sanity_check.sh --quick                skip device/network checks
#   SPLUNK_HOST=cclorchestrator78 SPLUNK_USERNAME=… SPLUNK_PASSWORD=… ./scripts/sanity_check.sh
#
# Exit 0 only when nothing FAILed. BLOCKED does not fail the run: it means a
# prerequisite (usually device addresses) is not in place yet.

set -uo pipefail

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

QUICK=no
[ "${1:-}" = "--quick" ] && QUICK=yes

PORT="${PORT:-8000}"
BASE="http://127.0.0.1:$PORT"
TOKEN="${MCP_AUTH_TOKEN:-cisco-mcp-workshop}"
# Splunk REST probe vars (SPLUNK_HOST/PORT/USERNAME/PASSWORD) read at step 11.

PASS=0; FAIL=0; BLOCK=0; SKIP=0
SERVER_PID=""

pass()  { printf '  \033[32mPASS\033[0m  %s\n' "$1"; PASS=$((PASS+1)); }
fail()  { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; [ -n "${2:-}" ] && printf '        %s\n' "$2"; FAIL=$((FAIL+1)); }
block() { printf '  \033[33mBLOCKED\033[0m  %s\n' "$1"; [ -n "${2:-}" ] && printf '        %s\n' "$2"; BLOCK=$((BLOCK+1)); }
skip()  { printf '  SKIP  %s\n' "$1"; SKIP=$((SKIP+1)); }
step()  { printf '\n\033[1m%s\033[0m\n' "$1"; }

cleanup() { [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null; return 0; }
trap cleanup EXIT

# --- 1. desktop -------------------------------------------------------------
step "1. Desktop prerequisites"
HAVE_UV=no
command -v uv >/dev/null 2>&1 && HAVE_UV=yes
if command -v python3.12 >/dev/null 2>&1; then
  pass "python3.12 present ($(python3.12 --version))"
elif [ "$HAVE_UV" = yes ] && uv python find 3.12 >/dev/null 2>&1; then
  pass "python3.12 provided by uv ($(uv python find 3.12))"
elif [ "$HAVE_UV" = yes ]; then
  # Not fatal: uv downloads a private 3.12 on demand. The system python stays
  # untouched, which matters on a pod image we do not own.
  block "python3.12 not installed yet" "uv is present — run ./scripts/bootstrap_desktop.sh"
else
  fail "neither python3.12 nor uv found" "curl -LsSf https://astral.sh/uv/install.sh | sh"
fi
[ "$HAVE_UV" = yes ] && pass "uv present" || fail "uv not found" "curl -LsSf https://astral.sh/uv/install.sh | sh"

# --- 2. server venv ---------------------------------------------------------
step "2. Server environment"
if [ -x code/server/.venv/bin/python ] && code/server/.venv/bin/python -c "import mcp, netmiko, yaml" 2>/dev/null; then
  pass "server venv imports mcp, netmiko, yaml"
else
  fail "server venv missing or broken" "run ./scripts/bootstrap_desktop.sh"
fi

# --- 3. devices -------------------------------------------------------------
step "3. Lab device reachability (the check that decides hands-on vs demo)"
if [ "$QUICK" = yes ]; then
  skip "device reachability (--quick)"
else
  DEVJSON=$(code/server/.venv/bin/python - <<'PY' 2>/dev/null
import sys; sys.path.insert(0, "code/server")
from app import inventory as inv
for n, d in inv.DEVICES.items():
    print(f"{n}\t{d.host or ''}\t{d.role}")
PY
)
  if [ -z "$DEVJSON" ]; then
    fail "could not read inventory" "check code/server/inventory.yaml"
  else
    CONFIGURED=$(printf '%s\n' "$DEVJSON" | awk -F'\t' '$2!=""' | wc -l)
    TOTAL=$(printf '%s\n' "$DEVJSON" | wc -l)
    if [ "$CONFIGURED" -eq 0 ]; then
      block "no device has a management address ($TOTAL devices)" \
            "fill host: in code/server/inventory.yaml — see docs/lab-device-map.md"
    else
      while IFS=$'\t' read -r name host role; do
        [ -z "$host" ] && continue
        if timeout 5 bash -c "echo > /dev/tcp/$host/22" 2>/dev/null; then
          pass "SSH port open on $name ($host, $role)"
        else
          fail "cannot reach $name ($host, $role) on tcp/22" "no route, or device down"
        fi
      done <<< "$DEVJSON"
      [ "$CONFIGURED" -lt "$TOTAL" ] && block "$((TOTAL-CONFIGURED)) of $TOTAL devices still have no address"
    fi
  fi
fi

# --- 4. server starts -------------------------------------------------------
step "4. MCP server"
OURS=no
EXISTING=$(curl -s -m 3 "$BASE/" 2>/dev/null)
if printf '%s' "$EXISTING" | grep -q "Cisco Network MCP Server"; then
  pass "our MCP server is already running on $BASE"
  OURS=yes
elif [ -n "$EXISTING" ]; then
  fail "port $PORT is taken by something else" \
       "got: $(printf '%s' "$EXISTING" | cut -c1-90)... — rerun with PORT=8099"
else
  (cd code/server && PORT="$PORT" ./run.sh >/tmp/sanity-server.log 2>&1 &) 
  for _ in $(seq 1 20); do curl -s -m 2 -o /dev/null "$BASE/" && break; sleep 1; done
  SERVER_PID=$(pgrep -f "uvicorn app.main:app.*$PORT" | head -1)
  if curl -s -m 3 "$BASE/" 2>/dev/null | grep -q "Cisco Network MCP Server"; then
    pass "server started on $BASE"
    OURS=yes
  else
    fail "server did not start" "see /tmp/sanity-server.log"
  fi
fi
DEFDEV=""
if [ "$OURS" = yes ]; then
  DEFDEV=$(curl -s -m 5 "$BASE/" 2>/dev/null | sed -n 's/.*"default_device":"\([^"]*\)".*/\1/p')
  [ -n "$DEFDEV" ] && pass "health reports default_device=$DEFDEV" \
                   || fail "health endpoint has no default_device"
fi

# --- 5. auth ----------------------------------------------------------------
step "5. Transport auth"
if [ "$OURS" != yes ]; then block "transport auth" "our server is not running on $PORT"; else
CODE=$(curl -s -o /dev/null -w '%{http_code}' -m 5 -X POST "$BASE/mcp")
[ "$CODE" = "401" ] && pass "unauthenticated POST /mcp -> 401" || fail "unauthenticated POST /mcp -> $CODE (expected 401)"
fi

# --- 6/7. protocol + offline suite ------------------------------------------
step "6. Protocol smoke test"
if [ "$OURS" != yes ]; then block "protocol smoke test" "our server is not running on $PORT"; elif (cd code/server && ./smoke_test.sh "$BASE" >/tmp/sanity-smoke.log 2>&1); then
  pass "smoke_test.sh: $(grep -oE '[0-9]+ passed, [0-9]+ failed' /tmp/sanity-smoke.log | tail -1)"
else
  fail "smoke_test.sh failed" "$(grep FAIL /tmp/sanity-smoke.log | head -3)"
fi

step "7. Offline test suite (no device, no network)"
if (cd code/server && .venv/bin/python -m pytest --color=no >/tmp/sanity-pytest.log 2>&1); then
  pass "pytest: $(grep -oE '[0-9]+ passed' /tmp/sanity-pytest.log | tail -1) (no device needed)"
else
  fail "pytest failed" "$(tail -3 /tmp/sanity-pytest.log)"
fi

# --- 8/9/10. client + safety ------------------------------------------------
step "8. fast-agent client"
FA=code/client-fastagent/.venv/bin/fast-agent
if [ "$OURS" != yes ]; then
  block "fast-agent checks" "our server is not running on $PORT"
elif [ ! -x "$FA" ]; then
  fail "fast-agent not installed" "cd code/client-fastagent && uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt"
else
  pass "fast-agent present ($($FA --version 2>&1 | tail -1))"
  export MCP_SERVER_URL="$BASE/mcp" MCP_AUTH_TOKEN="$TOKEN"
  # fast-agent's one-shot output ends with blank lines, so take the last
  # NON-blank line, not the last line.
  last_line() { grep -v '^[[:space:]]*$' | tail -1; }
  call() { (cd code/client-fastagent && timeout 90 .venv/bin/fast-agent go -c lab1.yaml \
            --servers my_server --no-home --model passthrough -m "$1" 2>/dev/null | last_line); }

  OUT=$(call '***CALL_TOOL my_server__list_devices {}')
  if printf '%s' "$OUT" | grep -q "prod-rep"; then
    pass "fast-agent connected and called list_devices (no LLM used)"
  else
    fail "fast-agent could not call a tool" "${OUT:0:200}"
  fi

  step "9. Blast radius — production must refuse a config write"
  PRODDEV=$(printf '%s\n' "${DEVJSON:-}" | awk -F'\t' '$3=="production"{print $1; exit}')
  PRODDEV="${PRODDEV:-sdceightkv11}"
  OUT=$(call "***CALL_TOOL my_server__create_loopback {\"loopback_id\": 999, \"device\": \"$PRODDEV\"}")
  if printf '%s' "$OUT" | grep -q "Refusing to configure"; then
    pass "create_loopback on $PRODDEV refused"
  else
    fail "PRODUCTION WRITE WAS NOT REFUSED on $PRODDEV" "${OUT:0:200}"
  fi

  step "10. Elicitation gate"
  sed 's/mode: forms/mode: auto-cancel/' code/client-fastagent/lab1.yaml > /tmp/sanity-cancel.yaml
  OUT=$( (cd code/client-fastagent && timeout 90 .venv/bin/fast-agent go -c /tmp/sanity-cancel.yaml \
      --servers my_server --no-home --model passthrough \
      -m "***CALL_TOOL my_server__create_loopback {\"loopback_id\": 999, \"device\": \"$DEFDEV\"}" 2>/dev/null | last_line) )
  if printf '%s' "$OUT" | grep -q "cancelled by user"; then
    pass "confirm gate fired and declined the change (no SSH attempted)"
  elif printf '%s' "$OUT" | grep -q "no management address"; then
    # The write is refused before the gate is reached, which is correct — but
    # it means the gate itself is still untested.
    block "elicitation gate untested" \
          "$DEFDEV has no management address, so the write is refused before the gate"
  else
    fail "elicitation gate did not fire" "${OUT:0:200}"
  fi
fi

# --- 11/12. shared services -------------------------------------------------
step "11. Pod Splunk REST (for splunk/splunk-mcp-server2)"
# The Splunk MCP server (code/server-splunk/) runs locally on the desktop and
# talks to the pod Splunk over REST. This probes that REST port is reachable.
SPLUNK_HOST="${SPLUNK_HOST:-}"
SPLUNK_PORT="${SPLUNK_PORT:-8089}"
if [ -z "$SPLUNK_HOST" ]; then
  skip "Splunk not configured (set SPLUNK_HOST=cclorchestrator78 [SPLUNK_PORT=8089] [SPLUNK_USERNAME/SPLUNK_PASSWORD])"
else
  # Self-signed cert by default, so -k is a reachability probe, not an
  # endorsement — decide the real TLS story before delivery.
  CODE=$(curl -sk -o /dev/null -w '%{http_code}' -m 10 \
         -u "${SPLUNK_USERNAME:-}:${SPLUNK_PASSWORD:-}" \
         "https://${SPLUNK_HOST}:${SPLUNK_PORT}/services/server/info?output_mode=json")
  case "$CODE" in
    000) fail "Splunk REST unreachable at ${SPLUNK_HOST}:${SPLUNK_PORT}" "no route to tcp/${SPLUNK_PORT}, or TLS handshake failed" ;;
    401) fail "Splunk REST reachable but rejected the account (HTTP 401)" "check SPLUNK_USERNAME/SPLUNK_PASSWORD (read-only role)" ;;
    *) pass "Splunk REST answered at ${SPLUNK_HOST}:${SPLUNK_PORT} (HTTP $CODE)" ;;
  esac
fi

step "12. OpenRouter"
if [ -z "${OPENROUTER_API_KEY:-}" ]; then
  skip "OPENROUTER_API_KEY not set (labs 1-4 still work with --model passthrough)"
else
  CODE=$(curl -s -o /dev/null -w '%{http_code}' -m 15 https://openrouter.ai/api/v1/models \
         -H "Authorization: Bearer $OPENROUTER_API_KEY")
  [ "$CODE" = "200" ] && pass "OpenRouter key accepted" || fail "OpenRouter returned HTTP $CODE"
fi

# --- summary ----------------------------------------------------------------
printf '\n\033[1m%d passed, %d failed, %d blocked, %d skipped\033[0m\n' "$PASS" "$FAIL" "$BLOCK" "$SKIP"
if [ "$BLOCK" -gt 0 ]; then
  printf 'BLOCKED means a prerequisite is missing (usually device addresses in\n'
  printf 'code/server/inventory.yaml) — not a code fault. See docs/lab-device-map.md.\n'
fi
[ "$FAIL" -eq 0 ]
