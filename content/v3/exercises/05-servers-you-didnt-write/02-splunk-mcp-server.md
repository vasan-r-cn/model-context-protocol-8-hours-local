# Splunk MCP Server — a Vendor Server on Its Terms

**Category:** 05 · MCP Servers You Didn't Write · **Duration:** 13 min · **Runs on:** `linuxdesktop64` (client + server) · **Targets:** Splunk on `cclorchestrator78:8089`

**Devices in play:** `cclorchestrator78` (the pod's Splunk service, `:8089`) — querying its indexes, read-only.

## Introduction

Module 4 you built a server. This one you *don't* — you install someone else's and consume it on its terms. The server is [`splunk/splunk-mcp-server2`](https://github.com/splunk/splunk-mcp-server2), an **unofficial community** MCP server (MIT). It is the Module 5 lesson made concrete: you accept a server's shape, its tools, and its trust model as given.

Two things about *this* server shape the exercise. First, it is **tools-only** — seven tools, no resources, no prompts. That's the common case in the wild; the rich primitive set your own server exposes is the exception, not the rule. Second, its security model is nothing like yours: there's no per-tool MCP capability. It authenticates to Splunk with a **Splunk account**, and what you can do is bounded by that account's role plus the server's own query guardrails. Authorization lives in Splunk and the server, not in a prompt.

> **Note on the server choice.** An earlier design used a Splunk-app MCP (Splunkbase 7931) served over HTTPS with a bearer token at `:8089/services/mcp`. This workshop uses `splunk/splunk-mcp-server2` instead: it runs **locally** on your desktop, speaks **SSE** on `:8050`, and reaches Splunk over the REST API. Same lesson, different plumbing — the steps below reflect the server you actually run.

## What You'll Learn

- What a vendor-published MCP server gives you, and what it withholds
- Tools-only servers: no resources, no prompts — the common case in the wild
- One broad tool (arbitrary SPL) versus many narrow ones: power against safety
- How authorization is enforced by the Splunk account + server guardrails, not by a prompt

## Before You Start

- Exercise 5.1 complete
- A **read-only Splunk account** (username/password or token) for your pod's Splunk

## Architecture Overview

| Component | Role |
|---|---|
| `splunk-mcp-server2` (local, `:8050/sse`) | the vendor MCP server — runs on your desktop |
| your pod's Splunk (`cclorchestrator78:8089`) | the backend it queries over REST |
| `SPLUNK_USERNAME`/`PASSWORD` (or `SPLUNK_TOKEN`) | how the server authenticates to Splunk |
| fast-agent (`lab-splunk.yaml`) | the MCP client, `transport: sse` |

```text
fast-agent --SSE--> splunk-mcp-server2 (:8050) --REST--> Splunk (:8089)
   7 tools, namespaced splunk__*     auth = your Splunk account + server guardrails
```

The seven tools: `validate_spl`, `search_oneshot`, `search_export`, `get_indexes`, `get_saved_searches`, `run_saved_search`, `get_config`.

## Setup

### Step 1 — install and point it at your Splunk

```bash
cd code/server-splunk
./setup.sh                                   # clones upstream/, builds venv
cp .env.example upstream/python/.env
```

Edit `upstream/python/.env`: set `SPLUNK_HOST` to your pod's Splunk (exposed `cclorchestrator78` FQDN), `SPLUNK_PORT=8089`, and your read-only `SPLUNK_USERNAME`/`SPLUNK_PASSWORD`. Leave `VERIFY_SSL=false` (lab self-signed cert).

### Step 2 — start it (terminal 1)

```bash
./run.sh            # serves SSE on http://localhost:8050/sse
```

## Exercises

### Part 1 — read what it gives you (5 min)

Terminal 2 — connect fast-agent and list the surface:

```bash
cd ../client-fastagent
fast-agent go -c lab-splunk.yaml --servers splunk --model passthrough
```

In session:

```text
/tools        # seven splunk__* tools
/resources    # empty
/prompts      # empty
```

**A1.** Compare this to your own server (Module 4). What does this one **not** have that yours does? Why is "tools-only" the common case for a vendor server?

> Answer to check yourself: no resources, no prompts — just tools. A vendor exposes the actions they're willing to support and nothing more; resources/prompts are extra surface they'd have to design and maintain. Your server was unusually rich because it's a teaching artifact.

### Part 2 — run a query (5 min)

Switch to a real model and ask for log evidence:

```bash
fast-agent go -c lab-splunk.yaml --servers splunk --model openrouter.$OPENROUTER_MODEL
```

```text
What indexes exist, and show me the last 10 events mentioning "interface down".
```

The model will call `splunk__get_indexes`, then `splunk__search_oneshot` with an SPL query.

> [SCREENSHOT 1: fast-agent — get_indexes then a search_oneshot returning rows from the lab index] <!-- captured at dry-run; needs pod Splunk with indexed data -->

**Checkpoint 1:** a query returned rows from your pod's Splunk index.

### Part 3 — power vs safety (3 min)

Two tools sit at opposite ends: `get_indexes` (narrow, one job) and `search_oneshot`/`validate_spl` (broad — arbitrary SPL).

**B1.** What can you do through `search_oneshot` that `get_indexes` can't — and what stops it being dangerous here?

> Answer to check yourself: `search_oneshot` runs arbitrary SPL, so it's far more powerful (and could be abused — heavy queries, broad reads). What bounds it is **not the MCP layer**: it's your Splunk account's role (read-only, index scope) plus the server's own query guardrails (risk scoring / `SPL_RISK_TOLERANCE`). Same principle as your Module 6 server — authorization is enforced at the backend, not asked for in a prompt.

**Reflection Questions**

1. This server is tools-only. When would a vendor *also* ship resources or prompts — and why usually not?
2. Your read-only account lets you `search_oneshot` but not write. Where is that rule enforced — the MCP server, Splunk, or both?
3. One broad `search_oneshot` vs ten narrow report tools: which would you ship to a model, and what's the trade?

## Verify

**Success Criteria**

- You read its `tools/list` and can name what is missing compared to your server (no resources, no prompts)
- One query returns rows from the lab index
- You can say what your read-only Splunk account lets you do through the server, and what it does not

**Done when:** you listed the seven tools, ran a query that returned rows, and can explain that authorization comes from the Splunk account + server guardrails, not the MCP layer.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `/tools` empty / connect fails | server not running, or wrong transport | `./run.sh` in `code/server-splunk`; config is `transport: sse`, url `/sse` |
| server starts but queries error | wrong Splunk host/creds in `.env` | fix `SPLUNK_HOST`/`PORT`/`USERNAME`/`PASSWORD` for your pod |
| TLS verify error | self-signed Splunk cert | `VERIFY_SSL=false` in `.env` |
| query returns zero rows | index empty or wrong time range | confirm syslog is indexed; widen the time range |
| `setup.sh` clone fails | no network at setup time | run on the pod image where egress is allowed; pin `SPLUNK_MCP_REF` |

## Quick Reference

```bash
# terminal 1 — the vendor server:
cd code/server-splunk && ./run.sh            # SSE :8050, -> Splunk :8089
# terminal 2 — the client:
fast-agent go -c lab-splunk.yaml --servers splunk --model openrouter.$OPENROUTER_MODEL
```

- `splunk/splunk-mcp-server2`: **tools-only** (7), **SSE** transport, local server → Splunk REST.
- Auth = your **Splunk account** + the server's query guardrails. Not an MCP capability, not a prompt.
- Tools namespaced `splunk__*`.

---

**Source material:** `splunk/splunk-mcp-server2` (local SSE server → Splunk REST on `cclorchestrator78:8089`). Live rows need indexed syslog in the pod.
