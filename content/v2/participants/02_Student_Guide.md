# Student Guide — MCP Workshop

## Cisco Router Operations over the Model Context Protocol

This is your reference document for the day. The labs have their own worksheets; come back here when you need the topology, the configuration details, verification steps, or troubleshooting.

Companion documents:
- **End-to-End Flow** (`00_EndToEnd_Flow`) — the story of one message through every component; read before or after Lab 1
- **Setup & Pre-Flight** (`01_Setup_PreFlight`) — done at the start of the session
- **Lab 1 worksheet: Protocol on the Wire** (`03_Lab1_WireTrace`)
- **Server Code Walkthrough** (`Server_Code_Walkthrough`) — line-by-line tour of the server you run
- **Lab 3 build guide** (`04_Lab3_Build_Guide`) — write your own tool
- **Bonus assignment** (`Bonus_Assignment_Prompts_Resources`) — take-home

---

## 1. The Big Picture

You are running three cooperating systems:

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

The model (Claude Haiku 4.5, via OpenRouter) never touches the router. It emits *structured requests* ("call `get_interfaces`"); LibreChat relays them over MCP; the server translates them into SSH commands; text comes back up the same path. Every hop is observable, and you will observe all of them today.

The second client you'll use is **MCP Inspector** — same protocol, no AI attached. LibreChat shows the product experience; Inspector shows the wire. Neither is "more real": production MCP clients range from chat products to IDEs to custom agents, and they consume different subsets of the protocol (section 6).

## 2. Lab Topology

> [SCREENSHOT 4: network topology diagram — MCP-Client, cloud, MCP-Server, switch, Router1, Router2 with addresses]

| Component | Host | Address | Notes |
|---|---|---|---|
| LibreChat (MCP client) | `linuxdesktop3` | `172.18.0.2` — browser: `127.0.0.1:3080` | login `student@email.local` / `password` |
| MCP server | `linuxdesktop4` | `172.18.1.2:8000` | code `~/cisco_mcp/app/main.py`, start `./run.sh` |
| Router1 (the lab target) | — | `172.18.2.6` | cisco_ios; admin / admin, enable: admin |
| Router2 (advanced exercises) | — | `172.18.2.10` | same credentials |
| MCP Inspector | on `linuxdesktop4` | UI `127.0.0.1:6274` | `npx @modelcontextprotocol/inspector@2.0.0` |

Note the three different /24 networks (172.18.**0**.x client, 172.18.**1**.x server, 172.18.**2**.x routers), joined by a routed core. This is why every URL uses real addresses — `localhost` on the client desktop cannot reach the server. It is also why LibreChat's SSRF protection must explicitly allow the server address (section 4).

Software: Python 3.11 + FastAPI/uvicorn/mcp/netmiko on the server (auto-installed into `.venv` by `run.sh`); Docker Compose v2 + Node 22 on the client desktop.

## 3. The MCP Server (short version)

The server is one Python file, `app/main.py`, built on **FastMCP** from the official MCP SDK, served over **Streamable HTTP** at `/mcp`, guarded by a **bearer token**. It exposes:

| Primitive | What this server provides |
|---|---|
| Tools (7) | `get_interfaces`, `get_router_info`, `dynamic_show`, `snapshot_config` (read-only) · `configure_interface`, `create_loopback` (destructive) · `enable_config_tools` (toggle) |
| Resources (4) | `router://interfaces`, `router://running-config`, `router://baseline`, template `router://interfaces/{name}` |
| Prompts (2) | `troubleshoot_interface`, `audit_router_config` |
| Notifications | `tools/list_changed` (on toggle), `resources/updated` (on config change, for subscribers) |
| Elicitation | confirmation dialog before config writes — when the client supports it |

The full tour — including *why* each piece is built the way it is — is the **Server Code Walkthrough** document. Read sections 4–7 of it before Lab 3.

Operational safety features you should notice as you work: read-only vs destructive tool annotations, an exact-match command allowlist (not prefix matching — the walkthrough explains the bypass that prevents), automatic pre-change config snapshots, and the confirmation gate.

## 4. LibreChat Configuration

Two files on `linuxdesktop3` under `~/LibreChat` control everything: `librechat.yaml` (what LibreChat offers) and `.env` (secrets).

### 4.1 librechat.yaml

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

Line-by-line, the parts that matter:

- **`fetch: false` + one default model** — the model picker offers exactly the model this lab verified for tool calling. (With `fetch: true` you get OpenRouter's full catalog, including delisted or policy-restricted models that fail with a `404 No endpoints available` error.)
- **`type: streamable-http`** — the current MCP transport. One URL, `/mcp`.
- **`headers:` with `${CISCO_MCP_TOKEN}`** — LibreChat expands the variable from its `.env` and sends it as the bearer token on every request. The value must equal the server's `MCP_AUTH_TOKEN`.
- **`serverInstructions: true`** — LibreChat injects the instructions the *server* sends during `initialize` into your conversations. The server author briefs your model.
- **`mcpSettings.allowedAddresses`** — LibreChat ships SSRF protection that blocks private addresses by default. Without this block the server is silently refused with `Domain "http://172.18.1.2:8000" is not allowed` in the logs. Use `allowedAddresses`, not `allowedDomains` (the latter switches LibreChat into a strict whitelist that would block OpenRouter).

### 4.2 .env

```bash
OPENROUTER_KEY=sk-or-...        # provided on the lab image
CISCO_MCP_TOKEN=cisco-mcp-workshop
UID=1000
GID=1000
```

**The rule that costs people an hour:** `.env` is read when a container is **created**, not on restart.

```bash
sudo docker compose restart api                 # picks up librechat.yaml changes
sudo docker compose up -d --force-recreate api  # required after .env changes
```

### 4.3 The other way in: the UI connector (Lab 2, part B)

LibreChat v0.8.7 can also add an MCP server **per user** from the chat UI — the "+" in the MCP servers panel opens a custom-connector dialog.

> [SCREENSHOT 5: LibreChat custom connector dialog with Name, MCP Server URL, Transport and Authentication fields]

| Field | Value |
|---|---|
| Name | `Cisco Router (mine)` |
| MCP Server URL | `http://172.18.1.2:8000/mcp` |
| Transport | Streamable HTTPS |
| Authentication | **API Key** → `cisco-mcp-workshop` |
| I trust this application | ✔ |

Two lessons wired into this exercise: leave Authentication on "None (Auto-detect)" and it fails — the server's 401 makes LibreChat go hunting for OAuth endpoints that don't exist (log: `OAuth Required: true … 0 tools`). And the SSRF allowlist from 4.1 applies to UI connectors too.

yaml vs UI: the yaml server is **shared** — every account gets it, admins fix it in one place. A UI connector is **per-user**. Products need the first; personal workflows use the second.

## 5. Verifying the Stack

In dependency order — each step assumes the previous passed:

1. Router reachable from the server: `ping -c2 172.18.2.6` (on linuxdesktop4)
2. Server process up: `curl http://127.0.0.1:8000/` → status JSON
3. Wire protocol + auth: `./smoke_test.sh` → `13 passed, 0 failed`
4. Inspector connects, 7 tools listed (Setup doc, step 4)
5. LibreChat containers: `sudo docker compose ps` — five Up
6. LibreChat ↔ server: `sudo docker compose logs api | grep -i mcp` → look for `cisco-router` with `Tools: get_interfaces, …` and `7 tools`
7. Full chain: new chat → enable `cisco-router` in the MCP menu → *"Show me the router interfaces"* → answer contains the real interface table, and the server terminal shows the `tools/call`

> [SCREENSHOT 6: LibreChat chat showing the MCP server toggle menu with cisco-router enabled]

> [SCREENSHOT 7: LibreChat conversation — "Show me the router interfaces" with the tool call expanded and the interface table in the reply]

## 6. Which Client Consumes What

The most practically important table of the day. "Supports MCP" is a spectrum:

| Capability | LibreChat v0.8.7 | Inspector | Claude Code |
|---|---|---|---|
| Tools | ✅ | ✅ | ✅ |
| Bearer/header auth | ✅ | ✅ | ✅ |
| Server instructions | ✅ | ✅ | ✅ |
| Resources | ❌ | ✅ | ✅ (@-mentions) |
| Prompts | ❌ | ✅ | ✅ (slash commands) |
| tools/list_changed | ❌ | ✅ | — |
| Resource subscriptions | ❌ | ✅ | — |
| Elicitation | ❌ | ✅ | — |

Consequences you will see today:
- Resources, prompts, notifications and elicitation are **Inspector labs** (Labs 4–5). LibreChat simply never asks for them.
- `configure_interface` pops a **confirmation dialog in Inspector** but applies **with a warning in LibreChat** — the server checked the client's declared capabilities and degraded gracefully. Same server, two behaviors: that is capability negotiation.
- The take-home assignment has you consume prompts and resources from Claude Code — a production client that does implement them.

## 7. Troubleshooting

Work top-down: the *server terminal* and *LibreChat api logs* name almost every failure.

| Symptom | First check | Likely fix |
|---|---|---|
| Inspector: connection refused | `curl http://127.0.0.1:8000/` on the server box | server not running — `./run.sh` |
| Inspector: 401 | server terminal prints the reason | token typed with `Bearer ` prefix, or wrong token (check server `.env`) |
| LibreChat logs: `Domain … is not allowed` | `mcpSettings` block present? | add `allowedAddresses: ["172.18.1.2:8000"]`, restart api |
| LibreChat logs: `OAuth Required: true`, `0 tools` | server terminal: 401 reason | empty/missing `CISCO_MCP_TOKEN` in `.env` → fix, then **force-recreate** api |
| LibreChat: no MCP menu in chat | config never loaded | yaml indentation; `docker compose config \| grep librechat.yaml` to confirm the file is mounted |
| Chat: `404 No endpoints available … data policy` | which model is the chat pinned to? | old/delisted model selected — pick `anthropic/claude-haiku-4.5`; `fetch: false` prevents recurrence |
| Model answers but never calls the tool | is `cisco-router` toggled on in this chat's MCP menu? | enable it; start a new chat |
| Tool errors: `Error talking to Router1: TCP connection …` | `ping 172.18.2.6` from server box | router/lab network issue — instructor |
| Tool call very slow then works | normal: SSH round-trip | progress notifications extend the timeout; nothing to fix |
| Blank/partial command output | command not in allowlist? read the tool reply | `dynamic_show` rejection text lists allowed commands |

Golden rule from the lab design: **verify in Inspector before debugging in LibreChat.** Inspector talks to the server with nothing else in the way; if it works there, the problem is client-side config.

## 8. Glossary (the 12 terms that matter today)

- **MCP** — Model Context Protocol; open standard connecting AI applications to tools and data.
- **MCP host/client** — the application embedding the AI (LibreChat) and its protocol connector.
- **MCP server** — the program exposing capabilities (our Python file).
- **JSON-RPC 2.0** — the message format: requests (with `id`), responses, notifications (no `id`).
- **Streamable HTTP** — current MCP transport; single endpoint, supports streaming and sessions. Replaced the deprecated HTTP+SSE transport.
- **initialize** — first exchange on every connection; both sides declare capabilities and the server sends its instructions.
- **Capability negotiation** — clients/servers only use features both declared during initialize.
- **Tool** — model-controlled action (`get_interfaces`). Described to the LLM by its docstring-derived description.
- **Resource** — application/user-controlled context (`router://running-config`); read, not executed.
- **Prompt** — user-controlled reusable template (`troubleshoot_interface`).
- **Elicitation** — server asks the user a structured question mid-operation (our confirmation gate). Never for secrets.
- **Tool annotations** — machine-readable hints: `readOnlyHint`, `destructiveHint`.
