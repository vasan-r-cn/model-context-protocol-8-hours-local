# MCP Server Improvement Plan

**Scope:** complete improvement plan for the workshop MCP server (`code/server/`). Content-document fixes are in [content-improvement-plan.md](content-improvement-plan.md); delivery structure in [workshop-flow-4h.md](workshop-flow-4h.md).

**Decisions already made:** official Python SDK FastMCP (`mcp.server.fastmcp`, from the `mcp` package — not the standalone `fastmcp` 2.x library) · bearer-token authentication · Streamable HTTP as the primary transport.

---

## 1. Current State and Gaps

`code/server/app/main.py` today:
- Low-level `mcp.server.Server` with a hand-wired `SseServerTransport` inside FastAPI (`GET /sse` + `POST /messages/`), using the private `request._send` ASGI attribute.
- HTTP+SSE transport — **deprecated in the MCP spec since revision 2025-03-26.**
- Two tools (`get_interfaces`, `configure_interface`); manual `list_tools()`/`call_tool()` dispatch that must be kept in sync by hand.
- No authentication of any kind.
- Router credentials hardcoded (acceptable for the lab, but there's no exercise or path to do it right).
- No resources, prompts, notifications, subscriptions, or elicitation — the deck teaches all of them; the server demonstrates none.
- `app/tools.py` is fabricated code: `from mcp import Tool, tool` and `Tool.arg(...)` do not exist in any version of the SDK. The file cannot import. It must be deleted or rewritten — students *will* copy it.
- No `requirements.txt`; environment is unreproducible.
- `configure_interface` writes live router config with no confirmation gate, no read-only/destructive classification, no rollback story.

## 2. Target Architecture

**One FastMCP server, mounted inside the existing FastAPI app** (keeps the `GET /` health check students already curl, and gives a natural place for the auth middleware):

```
FastAPI app
├── GET /            health check (unchanged behavior)
├── /mcp             FastMCP Streamable HTTP endpoint (primary)
└── BearerAuthMiddleware (ASGI) guarding /mcp
```

Sketch:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP, Context

mcp = FastMCP(
    "cisco-router-mcp",
    instructions="Operates Router1 (172.18.2.6). Read-only tools are safe; "
                 "config tools modify a live lab router.",
    stateless_http=False,   # keep sessions: needed for subscriptions/elicitation demos
)

# tools/resources/prompts defined with decorators (below)

app = FastAPI(title="Cisco Router MCP Server", lifespan=lambda app: mcp.session_manager.run())
app.mount("/", mcp.streamable_http_app())   # serves /mcp
```

(Exact mount/lifespan wiring to be finalized against the installed `mcp 1.14.1` API when implementing; the SDK exposes `mcp.streamable_http_app()` and `mcp.session_manager.run()` for exactly this pattern.)

Old `/sse` + `/messages/` endpoints: **removed.** Docs get a one-paragraph "legacy HTTP+SSE" sidebar for historical context. The `instructions` string is consumed by LibreChat via `serverInstructions: true` — a free teaching moment.

**Teaching rationale for FastMCP:** the schema is derived from the function signature + docstring, which eliminates the "list_tools and call_tool must stay in sync" failure mode the current CLAUDE.md has to warn about, and cuts the code students must understand roughly in half.

## 3. Feature Plan

Each feature lists: implementation, which client demos it, and the workshop exercise it enables. The client column is load-bearing — see the compatibility matrix in §4 for why.

### 3.1 Authentication — bearer token

**Implementation:** ASGI middleware on the FastAPI app guarding `/mcp`:
- Expect `Authorization: Bearer <token>`; compare (constant-time) against `MCP_AUTH_TOKEN` from the environment.
- On failure: `401` with `WWW-Authenticate: Bearer` and a JSON body that tells the student exactly what's missing (workshop-friendly error text).
- Health check `GET /` stays unauthenticated (students verify liveness before touching auth).

**LibreChat side** (reference `librechat.yaml`, to be checked into the repo):

```yaml
mcpServers:
  cisco-router:
    type: streamable-http
    url: http://172.18.1.2:8000/mcp
    headers:
      Authorization: "Bearer ${CISCO_MCP_TOKEN}"
    serverInstructions: true
    timeout: 60000
mcpSettings:
  allowedAddresses:
    - "172.18.1.2:8000"       # LibreChat SSRF guard blocks private IPs by default
```

**Inspector side:** add the same header in the Inspector connection pane.

**Exercise (Lab 2):** connect without the token → observe 401 in LibreChat logs → add header → tools appear. Teaches that MCP auth is transport-level HTTP auth, and where to look when it fails.

**Explicitly out of scope:** OAuth 2.1. LibreChat fully supports it (PKCE, dynamic client registration, auto-discovery on 401), and the SDK ships `mcp.server.auth` — worth a bonus doc section, not a 4-hour-workshop lab.

### 3.2 Tools

Port and consolidate (all in `main.py`; **delete `tools.py`**):

| Tool | Source | Annotations | Notes |
|---|---|---|---|
| `get_interfaces` | existing | `readOnlyHint: true` | unchanged behavior |
| `get_router_info` | rewrite of broken tools.py | `readOnlyHint: true` | hostname/version/uptime via TextFSM |
| `dynamic_show` | Bonus guide exercise | `readOnlyHint: true` | **hardened**: exact-command allowlist (no prefix matching), reject `\|` and `>`, `show running-config` excluded |
| `configure_interface` | existing | `destructiveHint: true` | gains elicitation gate (§3.6) + pre-change snapshot |
| `create_loopback` | rewrite of broken tools.py | `destructiveHint: true` | description `MCP_CREATED` kept — the reset script keys on it |
| `snapshot_config` | new | `readOnlyHint: true` | captures `show running-config` to a timestamped file server-side; rollback/reset anchor |

Implementation details:
- FastMCP decorator style; typed parameters; docstrings become tool descriptions (Bonus guide's "description as prompt engineering" lesson carries straight over).
- **Progress reporting** via `Context`: `await ctx.report_progress(...)` around SSH connect/command/disconnect. Pedagogically visible in Inspector; in LibreChat, progress pings extend the tool timeout (its client sets `resetTimeoutOnProgress`), which is exactly what slow SSH calls need.
- **Structured output** for `get_router_info` (typed dict return) — demonstrates `outputSchema`/structured content from the 2025 spec revisions.
- Netmiko calls are blocking — run them via `anyio.to_thread.run_sync` so one slow SSH session doesn't stall other students' sessions. Shared `run_show_command()` / `run_config_set()` helpers; errors returned as tool results (`isError`), never raised — preserves the "LLM sees the error and retries" behavior Test Case 3 in the Bonus guide relies on.
- Router credentials from env vars (`ROUTER_HOST`, `ROUTER_USER`, `ROUTER_PASSWORD`, `ROUTER_SECRET`) with the current lab values as defaults — keeps `./run.sh` zero-config while making the "fix the hardcoded creds" exercise real.

### 3.3 Resources — **Inspector demo**

| Resource | URI | Content |
|---|---|---|
| Interface table | `router://interfaces` | `show ip interface brief` output |
| Running config | `router://running-config` | full config (this is *why* the resource endpoint is authed) |
| Per-interface detail | `router://interfaces/{name}` | resource **template** — teaches URI templates |
| Baseline snapshot | `router://baseline` | last `snapshot_config` capture |

Teaching point: resources are application-controlled context (client decides to read), tools are model-controlled actions — the deck states this; the lab now shows it.

**LibreChat caveat (must be stated in docs):** LibreChat does not list or read MCP resources (`resources/list` exists in its code but is dead code — no callers). It *does* render resources **embedded in tool results**. So `get_interfaces` can return an embedded resource alongside text — the one resource-flavored thing LibreChat students will see.

### 3.4 Prompts — **Inspector demo**

- `troubleshoot_interface(interface: str)` — multi-step diagnostic prompt (status → config → common causes → recommended `show` commands).
- `audit_router_config()` — reviews running config against a small checklist (unused interfaces up, missing descriptions, weak SNMP strings).

Prompts return structured messages; Inspector's Prompts tab lists and renders them. Teaching point: prompts are user-controlled templates the *client* surfaces — and LibreChat's "Prompts" feature is its own unrelated Mongo-backed library, a naming collision worth one sentence in the docs.

### 3.5 Notifications & subscriptions — **Inspector demo**

- **`tools/list_changed`:** an `enable_config_tools` toggle tool registers/unregisters the destructive tools at runtime; FastMCP emits the notification, Inspector shows the tool list change live. Also models a real operational pattern: config-writing capability off by default, explicitly enabled.
- **Resource subscription:** `resources/subscribe` on `router://running-config`; after any config-writing tool runs, the server emits `notifications/resources/updated` — subscribe in Inspector, change config via a tool, watch the update arrive.

**LibreChat caveat:** it neither handles `tools/list_changed` (tool refresh is startup/manual only) nor calls `resources/subscribe`. Inspector-only lab.

### 3.6 Elicitation — **Inspector demo**

Confirmation gate inside `configure_interface` (and `create_loopback`):

```python
result = await ctx.elicit(
    message=f"About to configure {interface} with {ip_address}/24 on Router1 "
            f"(live lab device). Proceed?",
    schema=ConfirmSchema,   # accept / decline / cancel
)
if result.action != "accept":
    return "Change cancelled by user."
```

**Graceful degradation is mandatory:** LibreChat advertises `capabilities: {}` — an elicitation request against it fails or hangs. Wrap the elicit call: if the client lacks the capability, skip the gate and prepend a warning line to the result ("client does not support elicitation — change applied without confirmation"). This split *is* the lesson: capability negotiation decides what a server can ask of a client.

Docs must also carry the spec rule the current deck violates: elicitation **must never** be used to collect secrets/credentials.

### 3.7 Sampling — out of scope

Neither lab client supports it usefully (LibreChat: no; Inspector: mock-only). Stays lecture-only; the deck slide gets fixed per the content plan.

## 4. Client Compatibility Matrix

Verified against the vendored LibreChat v0.8.7 (`@modelcontextprotocol/sdk` 1.29.0, `packages/api/src/mcp/connection.ts`). This table gates every lab design decision and belongs in the instructor guide verbatim.

| Server feature | LibreChat | MCP Inspector | Demo in |
|---|---|---|---|
| Streamable HTTP transport | ✅ (`type: streamable-http`) | ✅ | both |
| Bearer token header | ✅ (`headers` / `apiKey`) | ✅ | LibreChat (Lab 2) |
| Tools + schemas | ✅ | ✅ | both |
| Progress notifications | ⚠️ extends timeout only, not shown | ✅ visible | Inspector |
| Server instructions | ✅ (`serverInstructions: true`) | ✅ | LibreChat |
| Embedded resources in tool results | ✅ | ✅ | LibreChat |
| `resources/list` / `read` / templates | ❌ dead code | ✅ | Inspector (Lab 4) |
| Prompts | ❌ dead code | ✅ | Inspector (Lab 4) |
| `tools/list_changed` | ❌ | ✅ | Inspector (Lab 5) |
| `resources/subscribe` + updated | ❌ | ✅ | Inspector (Lab 5) |
| Elicitation | ❌ (`capabilities: {}`) | ✅ | Inspector (Lab 5) |
| Sampling | ❌ | ⚠️ mock | lecture only |
| OAuth 2.1 | ✅ full | ✅ | bonus doc only |

## 5. Config & Packaging

- `code/server/requirements.txt`: `fastapi`, `uvicorn`, `mcp`, `netmiko` — pinned to the lab-tested versions.
- `code/server/.env.example`: `MCP_AUTH_TOKEN`, `ROUTER_HOST`, `ROUTER_USER`, `ROUTER_PASSWORD`, `ROUTER_SECRET`.
- `run.sh`: unchanged entry point (`python3.11 -m uvicorn app.main:app --host 0.0.0.0 --port 8000`); add `set -a; source .env` if present.
- Reference `librechat.yaml` (snippet in §3.1) checked into the repo — none exists today.
- Delete `app/tools.py` (fabricated API; cannot import).
- Update root `CLAUDE.md` notes after the rewrite (tool-sync warning becomes obsolete; endpoint changes).

## 6. Migration Steps & Test Plan

Incremental, verify after each step (each step is also a checkpoint in the instructor dry run):

1. **FastMCP port, transport swap.** Tools only (`get_interfaces`, `configure_interface`) on `/mcp`. Verify: pinned Inspector connects via Streamable HTTP; `tools/list` shows 2 tools; `get_interfaces` returns live router output.
2. **Auth middleware.** Verify: `curl http://172.18.1.2:8000/mcp` → 401; with bearer header → JSON-RPC response. LibreChat connects with reference yaml (including `allowedAddresses`); tools callable from chat.
3. **Tool set completion.** Add `get_router_info`, `dynamic_show`, `create_loopback`, `snapshot_config`, annotations, progress, env-var creds. Verify: whitelist rejects `show run | redirect`, annotations visible in Inspector, progress events stream during SSH calls.
4. **Resources + prompts.** Verify in Inspector: 3 resources + 1 template listed and readable; both prompts render.
5. **Notifications + subscriptions + elicitation.** Verify in Inspector: toggle tool fires `list_changed`; subscription to `router://running-config` yields `resources/updated` after a config write; `configure_interface` raises the elicitation dialog, and Decline aborts the change. Verify in LibreChat: same tool completes with the "no elicitation support" warning path.
6. **Smoke script.** A `curl`-based raw JSON-RPC script (initialize → tools/list → tools/call with bearer header) kept in `code/server/` for instructor pre-flight; doubles as teaching material for what the wire traffic looks like.
7. **Reset procedure.** Script that removes `Loopback*` interfaces whose description is `MCP_CREATED` and restores baseline interface addressing from the last snapshot; run between cohorts.

Regression guard for the workshop's own promise: after every step, the LibreChat end-to-end path ("show me the router interfaces" in chat → answer rendered) must still work — that path is the demo the whole workshop builds toward.
