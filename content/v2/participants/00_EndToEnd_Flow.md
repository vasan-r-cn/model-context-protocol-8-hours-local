# MCP Workshop — End-to-End Guide

## From "Show me the router interfaces" to a configured Cisco router: the complete picture

This is the comprehensive read: environment, server code, client configuration, verification, the full message flow, what you can modify, troubleshooting, and glossary — one document, in the order the original workshop guide used. The focused companions (`01_Setup_PreFlight`, `03_Lab1_WireTrace`, `04_Lab3_Build_Guide`, `Server_Code_Walkthrough`) go deeper on their slices; this document is the whole story.

---

## 1. Introduction

You are going to operate a real Cisco IOS router by talking to an AI in a chat window — and, more importantly, understand every hop in between well enough to build, secure, and debug the path yourself.

The technology connecting the pieces is the **Model Context Protocol (MCP)**: an open standard that lets any AI application (client) use capabilities exposed by any system (server) without bespoke integration. One protocol instead of M×N custom connectors.

What makes this lab different from a chatbot demo: the server you run treats the AI as an **untrusted user**. Command allowlists, read-only vs destructive tool annotations, bearer-token auth, confirmation gates, and pre-change snapshots — the guardrail stack is the curriculum, not an afterthought.

## 2. The Big Picture

```
 You (browser)
    |
    v
 LibreChat  ..............  the MCP CLIENT (and the AI application)
    |         Streamable HTTP + bearer token
    v
 MCP server ..............  the TRANSLATOR: exposes router operations
    |         SSH (Netmiko)          as protocol primitives
    v
 Router1   ...............  a real Cisco IOS router
```

The model (Claude Haiku 4.5, reached via OpenRouter) never touches the router. It emits *structured requests* ("call `get_interfaces`"); LibreChat relays them over MCP; the server validates and translates them into SSH commands; text returns up the same path.

Your second client is **MCP Inspector** — same protocol, no AI attached. LibreChat shows the product experience; Inspector shows the wire. You will also meet a third (Claude Code) in the take-home assignment. One server, three clients, zero client-specific server code: the M+N promise, working.

## 3. Understanding Your Lab Environment

> [SCREENSHOT: network topology diagram — MCP-Client, cloud, MCP-Server, switch, Router1, Router2 with addresses]

| Component | Host | Address | Notes |
|---|---|---|---|
| LibreChat (MCP client) | `linuxdesktop3` | `172.18.0.2` — browser: `127.0.0.1:3080` | login `student@email.local` / `password` |
| MCP server | `linuxdesktop4` | `172.18.1.2:8000` | code `~/cisco_mcp/app/main.py`, start `./run.sh` |
| Router1 (the lab target) | — | `172.18.2.6` | cisco_ios; admin / admin, enable: admin |
| Router2 (advanced exercises) | — | `172.18.2.10` | same credentials |
| MCP Inspector | on `linuxdesktop4` | UI `127.0.0.1:6274` | `npx @modelcontextprotocol/inspector@2.0.0` |

Three different /24 networks (172.18.**0**.x client, 172.18.**1**.x server, 172.18.**2**.x routers) joined by a routed core. This is why every URL uses real addresses — `localhost` on the client desktop cannot reach the server — and why LibreChat's SSRF protection must explicitly allow the server address (section 5).

**Software inventory.** MCP server host: Python 3.11 with FastAPI, uvicorn, `mcp` (the official SDK), Netmiko — auto-installed into `.venv/` by `run.sh` on first start. Client host: Docker Compose v2 running five containers (`LibreChat`, `chat-mongodb`, `chat-meilisearch`, `rag_api`, `vectordb`), plus Node 22 for Inspector.

## 4. Deep Dive: the MCP Server Code

One Python file — `~/cisco_mcp/app/main.py` — built on **FastMCP** from the official SDK, served over **Streamable HTTP** at `/mcp`, guarded by a bearer token. (Line-by-line tour with design rationale: `Server_Code_Walkthrough`. This section is the fast version.)

### 4.1 The server object

```python
mcp = FastMCP(
    "cisco-router-mcp",
    instructions="Operates Router1, a live Cisco IOS lab router. ...",
    streamable_http_path="/mcp",
)
```

`instructions` travels to every client in the `initialize` response — the server author briefing every model that will ever connect. LibreChat injects it into your conversations (`serverInstructions: true`).

### 4.2 A tool is a decorated function

```python
@mcp.tool(annotations=types.ToolAnnotations(readOnlyHint=True))
async def get_interfaces(ctx: Context) -> str:
    """Get all router interfaces and their status (show ip interface brief)."""
    await ctx.report_progress(0, 1, "Connecting to Router1 over SSH...")
    output = await run_show("show ip interface brief")
    ...
```

Everything becomes protocol data: function name → tool name; **docstring → the description the LLM reads** (this is prompt engineering); type hints → generated JSON Schema; `annotations` → machine-readable safety hints. There is no schema/dispatch code to keep in sync — the decorator does both jobs.

### 4.3 The seven tools

| Tool | Kind | What it does |
|---|---|---|
| `get_interfaces` | read-only | `show ip interface brief` |
| `get_router_info` | read-only | hostname/version/uptime as **structured output** (has an outputSchema) |
| `dynamic_show` | read-only | any show command **from an exact-match allowlist** |
| `snapshot_config` | read-only | saves running config to a timestamped file — the rollback anchor |
| `configure_interface` | destructive | IP + no shutdown; elicitation-gated; auto pre-change snapshot |
| `create_loopback` | destructive | loopback tagged `MCP_CREATED` (the reset script keys on it) |
| `enable_config_tools` | toggle | registers/unregisters the destructive tools at runtime → `tools/list_changed` |

Why exact-match allowlisting and not `startswith("show")`: prefix matching would allow `show running-config` (credential exposure) and IOS pipe abuse like `show run | redirect tftp://…` — a "read-only" check that can write your config to an attacker's server. LLM-supplied arguments are untrusted input, always.

### 4.4 Three more design rules you'll observe

- **Blocking SSH runs in worker threads** (`run_show`/`run_config` helpers) — one slow router doesn't stall other sessions.
- **Errors return as text, never exceptions** — a protocol error is invisible to the model, but error text gets read and retried with corrected input.
- **Elicitation gate with graceful degradation** — before writing config, the server asks the user for confirmation *if the client supports elicitation* (Inspector: real dialog; LibreChat: proceeds with a warning). Capability negotiation decides which path runs.

The server also exposes **4 resources** (`router://interfaces`, `router://running-config`, `router://baseline`, template `router://interfaces/{name}`) and **2 prompts** (`troubleshoot_interface`, `audit_router_config`) — explored in Lab 4 via Inspector, since LibreChat doesn't consume them (section 8).

## 5. Deep Dive: LibreChat Configuration

Two files on `linuxdesktop3` under `~/LibreChat`:

### 5.1 librechat.yaml

```yaml
version: 1.2.8
cache: true

endpoints:
  custom:
    - name: "OpenRouter"
      apiKey: "${OPENROUTER_KEY}"
      baseURL: "https://openrouter.ai/api/v1"
      models:
        default: ["anthropic/claude-haiku-4.5"]
        fetch: false
      titleConvo: true
      titleModel: "anthropic/claude-haiku-4.5"
      dropParams: ["stop"]
      modelDisplayLabel: "OpenRouter"

mcpServers:
  cisco-router:
    type: streamable-http
    url: "http://172.18.1.2:8000/mcp"
    headers:
      Authorization: "Bearer ${CISCO_MCP_TOKEN}"
    serverInstructions: true
    timeout: 60000
    chatMenu: true

mcpSettings:
  allowedAddresses:
    - "172.18.1.2:8000"
```

The lines that matter:

- **`fetch: false` + one default model** — the picker offers exactly the model verified for tool calling. (`fetch: true` would list OpenRouter's whole catalog, including delisted models that fail with `404 No endpoints available`.)
- **`type: streamable-http`** — current MCP transport, one URL.
- **`headers:`** — the bearer token on every MCP request; `${CISCO_MCP_TOKEN}` expands from `.env` and must equal the server's `MCP_AUTH_TOKEN`.
- **`mcpSettings.allowedAddresses`** — LibreChat's SSRF guard blocks private addresses by default; without this block the server is silently refused (`Domain "http://172.18.1.2:8000" is not allowed` in the logs). Use `allowedAddresses`, never `allowedDomains` (that flips into a strict whitelist and blocks OpenRouter).

### 5.2 .env

```bash
OPENROUTER_KEY=sk-or-...
CISCO_MCP_TOKEN=cisco-mcp-workshop
UID=1000
GID=1000
```

**The rule that costs people an hour:** `.env` is read at container **creation**, not restart.

```bash
sudo docker compose restart api                 # picks up librechat.yaml changes
sudo docker compose up -d --force-recreate api  # required after .env changes
```

### 5.3 The UI connector (per-user alternative)

LibreChat v0.8.7 can also add an MCP server per user from the chat UI (the "+" in the MCP panel): URL `http://172.18.1.2:8000/mcp`, Transport *Streamable HTTPS*, Authentication **API Key** = the token. Leave auth on "None (Auto-detect)" and it fails instructively — the server's 401 sends LibreChat hunting for OAuth endpoints that don't exist (`OAuth Required: true … 0 tools` in the logs). yaml = shared baseline for everyone; UI connector = personal. You do both in Lab 2.

## 6. How to Verify Everything Is Working

In dependency order — each step assumes the previous passed:

1. Router reachable from the server host: `ping -c2 172.18.2.6`
2. Server up: `curl http://127.0.0.1:8000/` → status JSON (health endpoint needs no auth)
3. Protocol + auth: `./smoke_test.sh` → `13 passed, 0 failed`
4. Inspector connects (Streamable HTTP, bearer token — token only, no "Bearer " prefix), 7 tools listed
5. LibreChat containers: `sudo docker compose ps` — five Up
6. LibreChat ↔ server: `sudo docker compose logs api | grep -i mcp` → `cisco-router` with `Tools: …` and `7 tools` (not `OAuth Required: true`)
7. Full chain: new chat → enable `cisco-router` in the MCP menu → *"Show me the router interfaces"* → real table in the answer, `tools/call` visible in the server terminal

> [SCREENSHOT: LibreChat conversation — "Show me the router interfaces" with the tool call expanded and the interface table in the reply]

## 7. Understanding the Data Flow

The complete journey of one message, with the real protocol payloads. Lab 1 has you observe these on the wire; this is the story version.

### Phase 0 — before you ever type (connection setup)

When LibreChat starts, it opens a Streamable HTTP session to `http://172.18.1.2:8000/mcp` — bearer token on **every** request.

**0.1 — the client introduces itself** (request — note the `id`):

```json
{"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {
  "protocolVersion": "2025-06-18",
  "capabilities": {},
  "clientInfo": {"name": "@librechat/api-client", "version": "..."}}}
```

That empty `capabilities: {}` matters — LibreChat declares no optional client features (no elicitation, no sampling). The server remembers.

**0.2 — the server answers** with its capabilities and instructions:

```json
{"jsonrpc": "2.0", "id": 0, "result": {
  "protocolVersion": "2025-06-18",
  "capabilities": {"tools": {"listChanged": true},
                   "resources": {"subscribe": true, "listChanged": true},
                   "prompts": {"listChanged": false}},
  "serverInfo": {"name": "cisco-router-mcp", "version": "..."},
  "instructions": "Operates Router1, a live Cisco IOS lab router. ..."}}
```

**0.3 — the client confirms** (notification — no `id`, no reply expected):

```json
{"jsonrpc": "2.0", "method": "notifications/initialized"}
```

**0.4 — discovery.** `tools/list` returns all 7 tool definitions — names, descriptions, schemas, annotations. The session idles until you type.

### Phase 1 — you type

> "Show me the router interfaces"

Browser → LibreChat API. LibreChat assembles the model request: your message, history, the server instructions, and the tool definitions from 0.4 (each with its `input_schema`).

### Phase 2 — the model decides

LibreChat → OpenRouter → Claude Haiku 4.5. The description of `get_interfaces` matches your intent; the model stops with a tool-use block:

```json
{"type": "tool_use", "id": "toolu_abc123", "name": "get_interfaces", "input": {}}
```

The model has *asked*. It cannot *act*. And note who steered the decision: the server author, via a Python docstring.

### Phase 3 — the tool call crosses the lab

```json
{"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {
  "name": "get_interfaces", "arguments": {}}}
```

On `linuxdesktop4`, in order: **(1)** auth middleware checks the bearer header — wrong/missing → 401 with a hint, and the server terminal logs *why*; **(2)** FastMCP routes to the function; **(3)** a **progress notification** streams back ("Connecting to Router1 over SSH...") — LibreChat uses it to extend its timeout; **(4)** Netmiko opens SSH to `172.18.2.6` in a worker thread and runs `show ip interface brief`.

### Phase 4 — the router answers

```
Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0     unassigned      YES NVRAM  administratively down down
GigabitEthernet0/1     192.168.1.1     YES NVRAM  up                    up
GigabitEthernet0/2     10.0.0.1        YES NVRAM  up                    up
```

*(Illustrative — trust your lab's live output, not this page.)*

### Phase 5 — result travels back up

```json
{"jsonrpc": "2.0", "id": 7, "result": {
  "content": [{"type": "text", "text": "Router1 interfaces:\n\nInterface  IP-Address ..."}],
  "isError": false}}
```

Had SSH failed, this would still be a *successful protocol message* with error text as content — deliberately, so the model can read the failure and retry.

### Phase 6 — the model narrates

LibreChat appends the result and calls the model again; the model writes for a human; the answer streams to your browser with the tool call rendered expandable. Elapsed: 3–8 seconds, dominated by SSH.

### The same flow, as a ladder

```
 You        LibreChat        OpenRouter/Claude      MCP server         Router1
  |             |                   |                   |                 |
  |--prompt---->|                   |                   |                 |
  |             |--msg + tool defs->|                   |                 |
  |             |<----tool_use------|                   |                 |
  |             |------------tools/call (id:7, Bearer)->|                 |
  |             |<~~~~~~ progress notification ~~~~~~~~ |                 |
  |             |                   |                   |--ssh: show...-->|
  |             |                   |                   |<---table--------|
  |             |<-----------result (id:7)--------------|                 |
  |             |--history+result-->|                   |                 |
  |             |<--final answer----|                   |                 |
  |<--streamed--|                   |                   |                 |
```

Legend: `-->` request/response · `~~>` notification (no id).

### What changes for a config command

Ask *"configure Gi0/2 with 10.0.0.5"* and the flow is identical until Phase 3, where `configure_interface` adds three steps before touching the router: **(1)** capability check — does this client support elicitation? LibreChat said `{}` in Phase 0.1 → no → proceed with a warning prefix (Inspector said yes → a confirmation dialog, and Decline aborts everything); **(2)** pre-change snapshot saved server-side; **(3)** after the change, a `notifications/resources/updated` push to any subscriber of `router://running-config`. Same plumbing; more guardrails.

### Protocol summary

| Hop | Protocol | Auth |
|---|---|---|
| Browser ↔ LibreChat | HTTP + SSE streaming | session login |
| LibreChat ↔ OpenRouter | HTTPS (OpenAI-compatible API) | `OPENROUTER_KEY` |
| LibreChat ↔ MCP server | MCP over Streamable HTTP (JSON-RPC 2.0) | `Authorization: Bearer <token>` |
| MCP server ↔ Router1 | SSH (Netmiko) | router credentials (server-side only) |

The model holds none of these credentials — it only ever *asks*. **The server is the security boundary; the model is a user.**

## 8. Which Client Consumes What

"Supports MCP" is a spectrum. Verified for the clients in this lab:

| Capability | LibreChat v0.8.7 | Inspector | Claude Code |
|---|---|---|---|
| Tools + bearer auth | ✅ | ✅ | ✅ |
| Server instructions | ✅ | ✅ | ✅ |
| Resources | ❌ | ✅ | ✅ (@-mentions) |
| Prompts | ❌ | ✅ | ✅ (slash commands) |
| tools/list_changed · subscriptions | ❌ | ✅ | — |
| Elicitation | ❌ | ✅ | — |

Consequences: resources/prompts/notifications/elicitation are Inspector labs (4–5); `configure_interface` confirms in Inspector but warns-and-proceeds in LibreChat; the take-home assignment consumes prompts and resources from Claude Code. Design rule this teaches: tools-first, everything else progressive enhancement with graceful degradation.

## 9. What You Can Modify

Safe, verified exercises (Lab 3 guide + walkthrough §13 have the full versions with done-when criteria):

1. **Extend the allowlist** — one line in `ALLOWED_SHOW_COMMANDS`, restart, verify accept + reject.
2. **Write a new read-only tool** — `ping_from_router(target)` with IPv4 validation (Lab 3's main build), or `get_uptime`. Copy the shape: decorator, annotation, docstring, error-as-text.
3. **Start locked down** — `MCP_CONFIG_TOOLS_DEFAULT=disabled` in the server `.env`; re-enable live and watch `tools/list_changed`.
4. **Rotate the token** — change `MCP_AUTH_TOKEN`, watch LibreChat break with 401s, fix `CISCO_MCP_TOKEN`, force-recreate. The most common real-world MCP integration failure, self-inflicted once so you recognize it forever.
5. **Add a resource** — expose `show ip route` as `router://routes` (three lines).

Golden verification habit: **Inspector before chat** — every change is checked at the protocol level before you involve the model.

## 10. Troubleshooting Common Issues

| Symptom | First check | Likely fix |
|---|---|---|
| Inspector: connection refused | `curl http://127.0.0.1:8000/` on the server box | server not running — `./run.sh` |
| Inspector: 401 | server terminal prints the reason | token typed with `Bearer ` prefix, or wrong token (check server `.env`) |
| LibreChat logs: `Domain … is not allowed` | `mcpSettings` block present? | add `allowedAddresses: ["172.18.1.2:8000"]`, restart api |
| LibreChat logs: `OAuth Required: true`, `0 tools` | server terminal: 401 reason | empty/missing `CISCO_MCP_TOKEN` → fix `.env`, **force-recreate** api |
| No MCP menu in chat | config never loaded | yaml indentation; confirm the file is mounted into the container |
| Chat: `404 No endpoints available … data policy` | which model is this chat pinned to? | delisted/blocked model — select `anthropic/claude-haiku-4.5`; `fetch: false` prevents recurrence |
| Model answers but never calls the tool | `cisco-router` toggled on in this chat? | enable in the MCP menu; new chat |
| `Error talking to Router1: TCP connection …` | `ping 172.18.2.6` from server box | router/lab network — instructor |
| Tool call slow then succeeds | normal SSH round-trip | progress notifications extend the timeout; nothing to fix |
| Command rejected by dynamic_show | read the tool reply | it lists the allowed commands — pick one |

Debugging axiom: **server terminal first, api logs second, browser last.** The server's 401 log names the exact auth mistake; LibreChat's log names the exact config gate.

## 11. Glossary

- **MCP** — Model Context Protocol; open standard connecting AI applications to tools and data.
- **Host / client / server** — the AI app you see / its protocol connector / the program exposing capabilities.
- **JSON-RPC 2.0** — the message format: requests (with `id`), responses (matching `id`), notifications (no `id`).
- **Streamable HTTP** — current MCP transport; one endpoint, sessions, streaming. Replaced deprecated HTTP+SSE.
- **initialize** — first exchange; both sides declare capabilities; server sends its instructions.
- **Capability negotiation** — each side may only use what the other declared. The reason one tool behaves differently in two clients.
- **Tool** — model-controlled action; described to the LLM by its docstring-derived description.
- **Tool annotations** — machine-readable hints: `readOnlyHint`, `destructiveHint`.
- **Structured output** — tool results validated against a declared `outputSchema`.
- **Resource** — application/user-controlled context, URI-addressed; read, not executed.
- **Resource template** — parameterized URI like `router://interfaces/{name}`.
- **Prompt** — user-controlled reusable template surfaced by the client.
- **Elicitation** — server asks the user a structured question mid-operation; never for secrets.
- **Subscription** — client asks to be notified when a resource changes.
- **Progress notification** — heartbeat during long tool calls; clients extend timeouts on it.
- **Bearer token** — HTTP `Authorization` header value; MCP remote auth is plain HTTP auth.
- **SSRF guard** — client-side protection blocking requests to private addresses unless allowlisted.
- **Netmiko** — Python SSH library for network devices; the server's hands.
- **FastMCP** — the official SDK's high-level, decorator-based server API.
- **Snapshot / baseline** — saved running config; the rollback anchor for every change.
