# Three Servers, One Agent

**Category:** 05 · MCP Servers You Didn't Write · **Duration:** 15 min · **Runs on:** `linuxdesktop64` · **Targets:** `sdceightkv24` + vManage + Splunk index

**Devices in play:** `sdceightkv24` (device state, your server) + `ciscovmanage3` (SD-WAN, vManage) + `cclorchestrator78` (Splunk) — one question across all three.

## Introduction

So far: one client, one server. This exercise is where MCP earns its keep. You point **one** fast-agent at **three** servers at once — your own device server, the SD-WAN server, and the Splunk server — and ask a question that no single one can answer alone.

This is composition. Device state from your server, SD-WAN path/tunnel state from the vManage server, log evidence from Splunk — three domains, three authors, one answer. The thing that makes it work without collisions is **namespacing**: every tool is `<server>__<tool>`, so `my_server__get_interfaces` and `sdwan__get_device_tunnels` never clash even if both servers had a `get_status`. And the thing that makes it *useful* is the model deciding, per sub-question, which server to ask.

## What You'll Learn

- How one client holds several servers at once, and how names stay unambiguous
- How a model chooses between servers answering about different domains
- What composition buys you: device state plus log evidence in one answer
- Where this breaks down — overlapping tools, ambiguous descriptions

## Before You Start

- Exercises 5.1 and 5.2 complete (SD-WAN and Splunk servers installed)

## Architecture Overview

| Server | Transport · Port | Domain |
|---|---|---|
| `my_server` (Module 4) | HTTP · `:8000` | device state (`sdceightkv24`, …) over SSH |
| `sdwan` (5.1) | HTTP · `:7004` | SD-WAN tunnels, health, alarms via vManage |
| `splunk` (5.2) | SSE · `:8050` | log evidence from the Splunk index |

```text
                         fast-agent (one model)
             /                    |                    \
   my_server__* (:8000)   sdwan__* (:7004)      splunk__* (:8050)
     device state           SD-WAN state           log evidence
```

## Setup

### Step 1 — start all three servers

Three terminals (or background them):

```bash
cd code/server        && ./run.sh &                 # my_server :8000
cd code/server-sdwan  && ./run.sh &                 # sdwan     :7004
cd code/server-splunk && ./run.sh &                 # splunk    :8050
```

### Step 2 — client env

```bash
cd code/client-fastagent
export MCP_SERVER_URL=http://127.0.0.1:8000/mcp MCP_AUTH_TOKEN=cisco-mcp-workshop
export OPENROUTER_API_KEY=sk-or-v1-...
export OPENROUTER_MODEL=anthropic/claude-sonnet-4
```

## Exercises

### Part 1 — one client, three servers (4 min)

```bash
fast-agent go -c lab-three.yaml --servers my_server,sdwan,splunk --model passthrough
```

In session:

```text
/mcp         # three servers connected
/tools       # tools from all three, each prefixed its server name
```

**A1.** Find one tool from each server in `/tools`. Write their fully namespaced names. Why does the `<server>__` prefix matter when three servers are loaded at once?

> Answer to check yourself: without the prefix, two servers exposing a same-named tool would collide and the model couldn't address them unambiguously. `my_server__get_interfaces` vs `sdwan__get_device_interfaces` stay distinct. Namespacing is what makes multi-server composition safe.

### Part 2 — a question that needs two servers (8 min)

Switch to a real model and ask something cross-domain:

```bash
fast-agent go -c lab-three.yaml --servers my_server,sdwan,splunk --model openrouter.$OPENROUTER_MODEL
```

```text
Is sdceightkv24's uplink healthy? Check the device interfaces, the SD-WAN
tunnel state, and any related log events.
```

Watch the trace: the model should call `my_server__get_interfaces` (device), `sdwan__get_device_tunnels` (path), and `splunk__search_oneshot` (logs), then synthesize one answer.

> [SCREENSHOT 1: fast-agent — the model calling tools from all three servers for one question] <!-- captured at dry-run; needs all three backends -->

**Checkpoint 1:** one answer drew on at least **two** different servers, and you can say which server answered which part.

**B1.** Which server answered which sub-question? Was there any part where two servers *could* have answered — and how did the model choose?

### Part 3 — where it breaks (3 min)

**C1.** Imagine both your server and the SD-WAN server exposed a tool literally named `get_interfaces` with similar descriptions. What would go wrong, and which of the two would the model pick? What does that tell you about writing descriptions when servers compose?

> Answer to check yourself: the names stay distinct via prefix, but if the *descriptions* overlap the model may pick the wrong one or waver. Composition quality depends on tool descriptions being specific about *domain* ("SD-WAN tunnel interfaces via vManage" vs "device interfaces via SSH"). At 30+ tools across servers, this is the real failure mode — and the reason you'd hide or rename overlapping tools.

**Reflection Questions**

1. Namespacing prevents *name* collisions. What kind of collision does it *not* prevent?
2. The model composed device + path + logs. What would that have cost you to build as hand-wired integrations (recall Module 2.4, the wall)?
3. As you add servers, tool count climbs fast. What's your strategy to keep selection accurate past ~30 tools?

## Verify

**Success Criteria**

- One fast-agent session answers a question needing two different servers
- You can say which server answered which part of the answer, and why
- You can show the namespaced tool names in `/tools`

**Done when:** a single answer drew on two+ servers, you attributed each part to its server, and you showed the `<server>__` prefixes in `/tools`.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `/tools` shows only one server | `--servers` listed one name | pass `--servers my_server,sdwan,splunk` (comma-separated) |
| "No tools available" | `-c` without `--servers` | always pass `--servers` with `-c` |
| a server missing from `/mcp` | that server not running / wrong port | start it; check `:8000`/`:7004`/`:8050` |
| splunk fails but others work | SSE transport / Splunk creds | `transport: sse`, url `/sse`; check `code/server-splunk/.env` |
| model answers from one server only | question not cross-domain, or descriptions ambiguous | ask a question that clearly spans device + path + logs |

## Quick Reference

```bash
# three servers up: code/server (:8000), code/server-sdwan (:7004), code/server-splunk (:8050)
fast-agent go -c lab-three.yaml --servers my_server,sdwan,splunk \
  --model openrouter.$OPENROUTER_MODEL
```

- One client, many servers. `--servers a,b,c` (comma-separated).
- Every tool is `<server>__<tool>` — no name collisions.
- Composition = device + path + logs in one answer. Selection accuracy is the thing that degrades as servers/tools multiply.

---

**Source material:** `code/client-fastagent/lab-three.yaml` (my_server + sdwan + splunk)
