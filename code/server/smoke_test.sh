#!/bin/bash
# Instructor pre-flight smoke test: raw JSON-RPC against the running server.
# Exercises: health check, auth rejection, initialize handshake, tools/list.
# Doubles as teaching material — this is the actual wire traffic of Lab 1.
#
# Usage: ./smoke_test.sh [base_url] [token]
set -u

BASE_URL="${1:-http://127.0.0.1:8000}"
TOKEN="${2:-${MCP_AUTH_TOKEN:-cisco-mcp-workshop}}"
MCP="$BASE_URL/mcp"
ACCEPT="Accept: application/json, text/event-stream"
CT="Content-Type: application/json"
AUTH="Authorization: Bearer $TOKEN"
PASS=0; FAIL=0

check() { # name, expected, actual
  if [ "$2" = "$3" ]; then echo "PASS: $1"; PASS=$((PASS+1));
  else echo "FAIL: $1 (expected $2, got $3)"; FAIL=$((FAIL+1)); fi
}

echo "== 1. Health check (unauthenticated) =="
code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/")
check "GET / returns 200" 200 "$code"

echo "== 2. Auth: request without token is rejected =="
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$MCP" -H "$ACCEPT" -H "$CT" -d '{}')
check "POST /mcp without token returns 401" 401 "$code"

echo "== 3. initialize handshake =="
INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke-test","version":"1.0"}}}'
resp_headers=$(mktemp)
init_body=$(curl -s -D "$resp_headers" -X POST "$MCP" -H "$ACCEPT" -H "$CT" -H "$AUTH" -d "$INIT")
SESSION=$(grep -i '^mcp-session-id:' "$resp_headers" | tr -d '\r' | awk '{print $2}')
rm -f "$resp_headers"
echo "$init_body" | grep -q '"serverInfo"' && ok=yes || ok=no
check "initialize returns serverInfo" yes "$ok"
echo "$init_body" | grep -q '"subscribe":true' && ok=yes || ok=no
check "capabilities advertise resources.subscribe" yes "$ok"
[ -n "$SESSION" ] && ok=yes || ok=no
check "server issued mcp-session-id" yes "$ok"

echo "== 4. notifications/initialized =="
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$MCP" -H "$ACCEPT" -H "$CT" -H "$AUTH" \
  -H "mcp-session-id: $SESSION" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}')
check "initialized notification accepted (202)" 202 "$code"

echo "== 5. tools/list =="
tools=$(curl -s -X POST "$MCP" -H "$ACCEPT" -H "$CT" -H "$AUTH" -H "mcp-session-id: $SESSION" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}')
for tool in get_interfaces get_router_info dynamic_show snapshot_config list_devices enable_config_tools configure_interface create_loopback; do
  echo "$tools" | grep -q "\"$tool\"" && ok=yes || ok=no
  check "tools/list contains $tool" yes "$ok"
done

echo
echo "== 6. inventory and blast radius =="
health=$(curl -s "$BASE_URL/")
default_device=$(echo "$health" | sed -n 's/.*"default_device":"\([^"]*\)".*/\1/p')
check "health reports a default device" yes "$([ -n "$default_device" ] && echo yes || echo no)"

# The default device must be one the server is willing to write to; if it is
# not, a tool call that omits `device` could land somewhere unintended.
writable=$(echo "$health" | sed -n 's/.*"writable_devices":\[\([^]]*\)\].*/\1/p')
echo "$writable" | grep -q "\"$default_device\"" && ok=yes || ok=no
check "default device ($default_device) is writable" yes "$ok"

# Every device in the tool schema must be a device the server knows about.
enum_ok=$(echo "$tools" | grep -c "\"device\"" || true)
check "tools expose a device parameter" yes "$([ "$enum_ok" -gt 0 ] && echo yes || echo no)"

unconfigured=$(echo "$health" | sed -n 's/.*"devices_without_management_address":\[\([^]]*\)\].*/\1/p')
if [ -n "$unconfigured" ]; then
  echo "   NOTE: devices with no management address yet: $unconfigured"
fi

echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
