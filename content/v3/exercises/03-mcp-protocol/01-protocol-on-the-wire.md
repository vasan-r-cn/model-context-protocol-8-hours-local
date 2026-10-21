# Protocol on the Wire

**Category:** 03 · MCP Protocol · **Duration:** 20 min · **Runs on:** `linuxdesktop64` · **Targets:** `sdceightkv24` (DR SD-WAN edge, `default_device`)

**Devices in play:** `sdceightkv24` (DR SD-WAN edge — the server's `default_device`).

## Introduction

You have felt the integration wall. MCP is the protocol that takes it down. Before you build a server or point an agent at one, spend twenty minutes watching the protocol move — because everything later in the day is these same three message types over and over.

MCP rides on **JSON-RPC 2.0**. There are exactly three shapes of message, and you can tell them apart by sight:

- **Request** — has an `id` and a `method`. "Do this, and label the answer with this id."
- **Response** — has the matching `id` and either a `result` or an `error`. "Here is the answer to id N."
- **Notification** — has a `method` but **no `id`**. "FYI, no reply expected."

You will use **MCP Inspector**, a protocol debugger, to run the lifecycle by hand and label real captured JSON. No model yet — just you and the wire.

## What You'll Learn

- The three JSON-RPC message types and how to tell them apart by sight
- What `initialize` negotiates, and what each side declares it can do
- Where a tool's JSON Schema comes from (nobody hand-wrote it)
- Why a rejected tool call is a *successful* response carrying an error

## Before You Start

- The MCP server running: `cd code/server && ./run.sh`
- MCP Inspector open: `npx @modelcontextprotocol/inspector`

## Architecture Overview

| Component | Role in this exercise |
|---|---|
| **MCP Inspector** (browser, `:6274`) | the *client* — speaks raw MCP, shows you every message |
| **Your MCP server** (`localhost:8000/mcp`) | the *server* — `cisco-router-mcp`, bearer-auth guarded |
| **`sdceightkv24`** | the DR SD-WAN edge the server reaches over SSH when you call a tool |
| **Bearer token** `cisco-mcp-workshop` | what Inspector must present to get past the server's auth middleware |

```text
Inspector  --(Streamable HTTP + Bearer)-->  your server  --(SSH)-->  sdceightkv24
   client          JSON-RPC 2.0                 server
```

## Setup

### Step 1 — start the server

```bash
cd code/server && ./run.sh
```

Leave it running. Health check: open `http://localhost:8000/` — it answers 200 with no auth (that's the health endpoint; `/mcp` is the guarded one).

### Step 2 — open Inspector and connect

```bash
npx @modelcontextprotocol/inspector
```

Open the token URL it prints. In the connection pane:

- **Transport:** Streamable HTTP
- **URL:** `http://localhost:8000/mcp`
- **Authentication:** header `Authorization` = `Bearer cisco-mcp-workshop`

Click **Connect**. Inspector runs `initialize` for you — watch the History pane populate.

> [SCREENSHOT 1: Inspector connected, Streamable HTTP, bearer header set, History showing the initialize exchange]

## Exercises

### Part 1 — label the handshake (8 min)

Open the `initialize` request/response in Inspector's History. Fill this table from the **real captured JSON**:

| Field | Where | Value you captured |
|---|---|---|
| `id` on the `initialize` request | request | |
| `protocolVersion` | request params | |
| `serverInfo.name` | response result | |
| `capabilities.resources.subscribe` | response result | |
| server `instructions` (first sentence) | response result | |

**A1.** The server's `instructions` field is prose aimed at the *model*. Read it. It begins: *"Operates a live Cisco lab network: a DC site (production), a DR site (production-representative)…"* — what is it telling a model to do **before** calling a device-touching tool?

> Answer to check yourself: call `list_devices` first if unsure which device to use, and only write to production-representative devices — always confirming first. The server *teaches the model its own safety rules* through `instructions`.

**A2.** Right after `initialize`, the client sends `notifications/initialized`. Find it. Does it have an `id`?

> Answer to check yourself: no `id` — it is a **notification**, not a request. The handshake is "request/response (initialize) → notification (initialized)". No reply is expected to the notification.

### Part 2 — discovery: where schemas come from (7 min)

Go to the **Tools** tab. Inspector called `tools/list` for you.

**B1.** Pick `get_interfaces`. Read its input schema. The `device` parameter is an **enum** of real device names. Nobody hand-wrote that JSON — it came from the Python function signature (`device: DeviceName`, where `DeviceName` is a `Literal` of the inventory). Write down two device names you see in the enum.

**B2.** Find the tool **annotations**. `get_interfaces` carries `readOnlyHint: true`. Find a tool that carries `destructiveHint: true` instead.

> Answer to check yourself: `configure_interface` and `create_loopback` are the destructive ones. The annotation is a *hint to the client/model*, declared in the `@mcp.tool(...)` decorator.

### Part 3 — execution, and the "successful error" (5 min)

In the Tools tab, call `get_interfaces` with `device = sdceightkv24`. Watch the request go out and the response (interface table) come back.

Now the important beat. Call `dynamic_show` with `command = show running-config`. That command is **not** on the server's allowlist.

**C1.** What came back — a JSON-RPC `error` object, or a `result` with `isError: true`?

> Answer to check yourself: a **result** carrying an error message, not a transport-level `error`. The tool *ran*, decided the command wasn't allowed, and returned that as its result. The model reads it as text and can react — which is exactly why tools return errors as results instead of raising.

**Reflection Questions**

1. Why does MCP put `notifications/initialized` *after* `initialize` instead of folding it into one message?
2. A tool's schema is generated from the Python signature. What does that buy you as the person maintaining the server?
3. If a rejected tool call came back as a transport `error` instead of a result, how would that change what the model can do about it?

## Verify

**Success Criteria**

- You have labelled request / response / notification from real captured JSON
- You have written down the server's declared capabilities and its `instructions`
- You can say why `notifications/initialized` carries no `id`

**Done when:** your handshake table is filled from real JSON, and you can point at the `initialize` exchange and name each message as request, response, or notification.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Inspector won't connect, 401 | bearer header missing or wrong | set `Authorization: Bearer cisco-mcp-workshop` exactly |
| Connect hangs | transport set to stdio | switch transport to **Streamable HTTP**, URL `/mcp` |
| `http://localhost:8000/` works but `/mcp` 401s | that's correct — `/` is the open health check | use the Tools tab, which sends the token |
| Tool call errors "could not connect to device" | `sdceightkv24` unreachable from your pod | that's a network/pod issue, not protocol — see exercise 1.1, check 3 |

## Quick Reference

- **Request** = `id` + `method`. **Response** = matching `id` + `result`/`error`. **Notification** = `method`, **no `id`**.
- Lifecycle: `initialize` (req/resp) → `notifications/initialized` (notif) → you may now call tools.
- Tool schema ← Python signature + docstring. Annotations (`readOnlyHint`/`destructiveHint`) ← the decorator.
- A rejected tool call is a **successful response** whose `result` carries the error.

---

**Source material:** Extends `content/v2/participants/03_Lab1_WireTrace.md`
