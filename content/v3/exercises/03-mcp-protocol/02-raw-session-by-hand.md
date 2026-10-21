# Raw Session by Hand

**Category:** 03 · MCP Protocol · **Duration:** 13 min · **Runs on:** `linuxdesktop64` · **Targets:** `sdceightkv24`

**Devices in play:** `sdceightkv24` (DR SD-WAN edge).

## Introduction

Inspector did the handshake for you. Now you do it yourself, with `curl`, so nothing is hidden. You will open a Streamable HTTP session, get a session id, send the `initialized` notification, open the server-sent-events (SSE) stream in a second terminal, make the server push a notification *to* you, and finally tear the session down.

Then the payoff: every step you just did by hand is already written down in `code/server/smoke_test.sh`. That script *is* the wire traffic of this lab. After this exercise you will never be confused about what a "session" means in MCP.

## What You'll Learn

- How a Streamable HTTP session is established and torn down
- What `Mcp-Session-Id` is for and what happens without it
- How server-initiated notifications reach a client over SSE
- How `smoke_test.sh` maps line-for-line onto what you just did by hand

## Before You Start

- Exercise 3.1 complete
- Server running; two terminals available

## Architecture Overview

| Thing | Role |
|---|---|
| **Terminal 1** | your request/response channel — POSTs to `/mcp` |
| **Terminal 2** | your notification channel — a held-open `GET /mcp` SSE stream |
| **`Mcp-Session-Id`** | the token tying both channels to one server-side session |
| **`smoke_test.sh`** | the same sequence, scripted — your reference key |

```text
Terminal 1  --POST /mcp (JSON-RPC req)-->  server  --resp-->  Terminal 1
Terminal 2  --GET  /mcp (SSE, held open)-->  server  ==notifications==>  Terminal 2
            both carry the same Mcp-Session-Id
```

## Setup

### Step 1 — shared shell variables

In **Terminal 1**:

```bash
BASE=http://127.0.0.1:8000
AUTH="Authorization: Bearer cisco-mcp-workshop"
ACCEPT="Accept: application/json, text/event-stream"
CT="Content-Type: application/json"
```

## Exercises

### Part 1 — initialize and capture the session id (5 min)

Send `initialize` and keep the **response headers** (`-D -`) — the session id comes back in a header, not the body:

```bash
curl -s -D - -o /tmp/init_body.json -X POST "$BASE/mcp" -H "$ACCEPT" -H "$CT" -H "$AUTH" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"byhand","version":"1.0"}}}'
```

Find the `mcp-session-id:` header in the output and save it:

```bash
SESSION=<paste the value from the mcp-session-id header>
```

Read your own request — every piece is doing a named job:

- `id:1` → this is a **request**; label the answer `1`.
- `protocolVersion` → which MCP version you speak; the server agrees or negotiates.
- `capabilities:{}` → you declare you support *nothing extra* (no elicitation, no sampling). Honest and minimal.
- `-D -` → dump headers; **the session id lives in a header**.

**A1.** Look in `/tmp/init_body.json` for `"serverInfo"` and `"subscribe":true`. Write down the server name.

**Checkpoint 1:** you have a non-empty `$SESSION` you obtained yourself.

Now complete the handshake with the `initialized` **notification** (no `id`, expect HTTP `202`):

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST "$BASE/mcp" -H "$ACCEPT" -H "$CT" -H "$AUTH" \
  -H "mcp-session-id: $SESSION" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'
```

> Answer to check yourself: `202 Accepted` — the server took the notification and there is nothing to reply with. A notification has no `id`, so there is no response body.

### Part 2 — make the server push you a notification (5 min)

In **Terminal 2**, open the SSE stream and leave it running (it will just hang, waiting):

```bash
BASE=http://127.0.0.1:8000
curl -N "$BASE/mcp" \
  -H "Accept: text/event-stream" \
  -H "Authorization: Bearer cisco-mcp-workshop" \
  -H "mcp-session-id: $SESSION"
```

Back in **Terminal 1**, flip the config tools on. This changes the tool list, so the server fires `notifications/tools/list_changed`:

```bash
curl -s -X POST "$BASE/mcp" -H "$ACCEPT" -H "$CT" -H "$AUTH" -H "mcp-session-id: $SESSION" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"enable_config_tools","arguments":{"enabled":true}}}'
```

**B1.** Watch Terminal 2. A `tools/list_changed` notification should arrive on the stream.

> [SCREENSHOT 1: Terminal 2 SSE stream showing the tools/list_changed notification that Terminal 1 triggered]

**Checkpoint 2:** a server-initiated notification appeared on your SSE stream because of something you did on the other channel.

### Part 3 — tear it down (3 min)

Close the session with `DELETE`, then prove it's gone by reusing the dead id:

```bash
curl -s -o /dev/null -w 'delete: %{http_code}\n' -X DELETE "$BASE/mcp" -H "$AUTH" -H "mcp-session-id: $SESSION"

curl -s -o /dev/null -w 'reuse: %{http_code}\n' -X POST "$BASE/mcp" -H "$ACCEPT" -H "$CT" -H "$AUTH" \
  -H "mcp-session-id: $SESSION" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/list","params":{}}'
```

**C1.** The second call should be **rejected** — the session no longer exists. Terminal 2's stream drops too.

**Checkpoint 3:** the reused session id is refused.

### Part 4 — map it onto `smoke_test.sh`

Open `code/server/smoke_test.sh`. Match each thing you did to a numbered block:

| You did | `smoke_test.sh` block |
|---|---|
| `initialize`, grabbed the session header | `== 3. initialize handshake ==` (it `grep`s `mcp-session-id`) |
| `notifications/initialized` → 202 | `== 4. notifications/initialized ==` |
| listed/triggered tools | `== 5. tools/list ==` |
| health check (no auth) | `== 1. Health check ==` |
| the 401 you'd get with no token | `== 2. Auth: request without token is rejected ==` |

Run it and watch it do all of that in one shot:

```bash
./smoke_test.sh
```

Verified reference result: **17 passed, 0 failed**.

**Reflection Questions**

1. Why does the session id come back in a **header** rather than the response body?
2. The SSE stream is a *second* HTTP connection. Why does MCP need a separate channel for server→client notifications at all?
3. What is the security reason the server refuses a reused (deleted) session id?

## Verify

**Success Criteria**

- You hold an `Mcp-Session-Id` you obtained yourself with `curl`
- Your SSE stream showed a `tools/list_changed` notification you triggered
- You closed the session with `DELETE` and the next request was rejected

**Done when:** all three checkpoints pass, and you can point at the line in `smoke_test.sh` that grabs the session id.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `initialize` returns 401 | no/wrong bearer token | add `-H "$AUTH"` with the right token |
| No `mcp-session-id` header | you dropped `-D -` | re-send with `-D -` and read the headers |
| POST after initialize returns 400 "no session" | you forgot `-H "mcp-session-id: $SESSION"` | add the session header to every call after initialize |
| SSE stream shows nothing | `enable_config_tools` was already on (no change → no notification) | toggle `enabled:false` then `true`, or restart the server |
| 202 for a `tools/call` | you sent it as a notification (no `id`) | requests need an `id` |

## Quick Reference

```bash
# 1. initialize — session id is in a HEADER:
curl -s -D - -X POST $BASE/mcp -H "$ACCEPT" -H "$CT" -H "$AUTH" -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"x","version":"1"}}}'
# 2. complete handshake (202, no id):
#    method: notifications/initialized   + mcp-session-id header
# 3. open SSE (held open): GET /mcp, Accept: text/event-stream, + session header
# 4. close: DELETE /mcp + session header
./smoke_test.sh     # the whole thing, scripted -> 17 passed
```

---

**Source material:** `code/server/smoke_test.sh`
