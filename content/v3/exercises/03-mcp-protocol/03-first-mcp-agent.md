# First MCP Agent

**Category:** 03 · MCP Protocol · **Duration:** 12 min · **Runs on:** `linuxdesktop64` · **Targets:** `sdceightkv24`

**Devices in play:** `sdceightkv24` (DR SD-WAN edge).

## Introduction

So far a *human* (you, via Inspector and curl) has driven the protocol. Now a *model* does. You will connect **fast-agent** — a real MCP client you did not write and the server did not ship with — to your server, and watch a model discover your tools and choose one on its own.

Two moves matter here. First, you'll prove the wiring with **no model at all** (`--model passthrough` + `***CALL_TOOL`) — because when something breaks later you must be able to ask "is it my server or the model?" and answer it in one command. Then you'll put a real model on top and ask a question in English.

## What You'll Learn

- How a real client connects to a server it did not ship with
- What the client sees: tools, resources, prompts — the same six primitives
- How to verify wiring without spending a token (`--model passthrough`)
- Why tool names are namespaced per server

## Before You Start

- Exercise 3.2 complete
- `MCP_SERVER_URL` and `MCP_AUTH_TOKEN` exported

## Architecture Overview

| Component | Role |
|---|---|
| **fast-agent** (CLI) | the MCP client — connects, lists primitives, lets a model call tools |
| **`lab1.yaml`** | the client config: one server `my_server`, bearer header from env |
| **your MCP server** (`localhost:8000/mcp`) | unchanged from 3.1/3.2 |
| **OpenRouter** | the model provider for the real-model step |

```text
fast-agent (model) --MCP--> my_server (localhost:8000) --SSH--> sdceightkv24
         names tools my_server__<tool>   (namespaced per server)
```

## Setup

### Step 1 — export the connection

```bash
cd code/client-fastagent
export MCP_SERVER_URL=http://127.0.0.1:8000/mcp
export MCP_AUTH_TOKEN=cisco-mcp-workshop
```

`lab1.yaml` reads both via `${...}` substitution — including inside the `Authorization: "Bearer ${MCP_AUTH_TOKEN}"` header. Nothing secret is written into the file.

## Exercises

### Part 1 — prove the wiring with no model (4 min)

`--model passthrough` runs **no LLM** — it only executes `***CALL_TOOL`. This is your "is it the server or the model?" test:

```bash
fast-agent go -c lab1.yaml --servers my_server --model passthrough \
  -m '***CALL_TOOL my_server__list_devices {}'
```

Read the command — every piece earns its place:

- `-c lab1.yaml` → use the config file (so the bearer header and server URL load).
- `--servers my_server` → **mandatory** with `-c`. Omit it and you get zero tools.
- `my_server__list_devices` → the tool name is **namespaced** `<server>__<tool>`. The `__` separator is how one agent keeps two servers' tools apart (you'll have two servers in Lab 3).
- `{}` → no arguments; `list_devices` takes none.

Expected: the 11-device inventory table (DC, DR, branches, legacy), returned with no model and no API key spent.

> [SCREENSHOT 1: passthrough CALL_TOOL list_devices output — the device table]

**Checkpoint 1:** `list_devices` returned real data with `--model passthrough`. The server wiring is proven, independent of any model.

### Part 2 — see what the client sees (3 min)

Start an interactive session (still no token spend needed for these commands):

```bash
fast-agent go -c lab1.yaml --servers my_server --model passthrough
```

At the prompt, run the client's own discovery commands:

```text
/mcp         # the connected servers
/tools       # your server's tools, namespaced
/prompts     # troubleshoot_interface, audit_router_config
/resources   # device://sdceightkv24/interfaces, .../running-config, templates ...
```

**B1.** These are the same primitives Inspector showed you in 3.1 — now through a different client. Note that `/prompts` and `/resources` are populated **with no extra config**: fast-agent auto-discovers them from the server.

### Part 3 — now a real model chooses a tool (5 min)

Make sure your key is exported:

```bash
export OPENROUTER_API_KEY=sk-or-v1-...
export OPENROUTER_MODEL=anthropic/claude-sonnet-4
```

Start a session with a real model (this overrides the config's `passthrough` default):

```bash
fast-agent go -c lab1.yaml --servers my_server \
  --model openrouter.$OPENROUTER_MODEL
```

> Note the model string: the **dot** prefix `openrouter.` means "provider = openrouter"; `$OPENROUTER_MODEL` (from your `.env`, e.g. `anthropic/claude-sonnet-4`) is the model. A bare `$OPENROUTER_MODEL` with no `openrouter.` prefix would route to the wrong provider.

Ask, in English:

```text
What interfaces does sdceightkv24 have, and which are down?
```

The model will read your `tools/list`, pick `my_server__get_interfaces`, call it with `device=sdceightkv24`, read the result, and answer.

> [SCREENSHOT 2: fast-agent session — the model calling get_interfaces and summarising the interface state in English] <!-- captured at dry-run; real-model output -->

**Checkpoint 2:** one English question was answered end-to-end by a model choosing and calling your tool.

**Reflection Questions**

1. You ran the exact same tool two ways — `***CALL_TOOL` and via a model. What does each one tell you when you're debugging?
2. Tool names are `my_server__get_interfaces`. Why namespace per server instead of just `get_interfaces`?
3. `/prompts` and `/resources` worked with no extra config. Where did fast-agent learn they existed?

> Answer to check yourself (Q1): `***CALL_TOOL` isolates the **server** (no model in the loop); the model path tests **discovery + selection + your docstrings**. If `***CALL_TOOL` works but the model won't call the tool, the problem is your tool's description, not your server.

## Verify

**Success Criteria**

- `fast-agent go` connects and `/tools` lists your server's tools
- One question is answered by a model choosing a tool, end to end
- A `***CALL_TOOL` invocation returned a result with no model involved

**Done when:** all three succeed — passthrough CALL_TOOL, `/tools` listing, and a real-model answer that visibly called `get_interfaces`.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "No tools are currently available" | used `-c` without `--servers my_server` | add `--servers my_server` |
| `fast-agent: command not found` | venv not active | `source .venv/bin/activate` (or use the full venv path) |
| passthrough just echoes "hi", no answer | that's correct — passthrough runs **no model** | ask real questions only with `--model openrouter...` |
| real model errors on auth/credits | `OPENROUTER_API_KEY` missing or unfunded | export the key; check credit on the lab sheet |
| model answers but never calls the tool | weak tool docstring, or question too vague | be specific ("interfaces on sdceightkv24"); this is the lesson of Lab 2 |
| wrong-provider error on the model string | dropped the `openrouter.` dot prefix | use `--model openrouter.$OPENROUTER_MODEL` |

## Quick Reference

```bash
export MCP_SERVER_URL=http://127.0.0.1:8000/mcp MCP_AUTH_TOKEN=cisco-mcp-workshop

# wiring check, no model, no token spend:
fast-agent go -c lab1.yaml --servers my_server --model passthrough \
  -m '***CALL_TOOL my_server__list_devices {}'

# interactive, real model:
export OPENROUTER_API_KEY=sk-or-v1-...
export OPENROUTER_MODEL=anthropic/claude-sonnet-4
fast-agent go -c lab1.yaml --servers my_server --model openrouter.$OPENROUTER_MODEL
# in session: /mcp /tools /prompts /resources /help
```

- `--servers` is **mandatory** with `-c`.
- Tool names are namespaced `my_server__<tool>` (`__` separator).
- `--model passthrough` = no LLM; only `***CALL_TOOL` works.

---

**Source material:** `code/client-fastagent/lab1.yaml`, `code/client-fastagent/README.md`
