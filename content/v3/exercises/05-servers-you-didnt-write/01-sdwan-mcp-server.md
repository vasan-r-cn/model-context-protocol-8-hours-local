# SD-WAN MCP Server

**Category:** 05 · MCP Servers You Didn't Write · **Duration:** 22 min · **Runs on:** `linuxdesktop64` (server + client); or pod-hosted on `cclorchestrator78:7004` · **Targets:** `ciscovmanage3` via REST

**Devices in play:** `ciscovmanage3` (vManage) and the SD-WAN fabric it reports on (WAN edges, Nexus) — read-only.

## Introduction

Your Module 4 server had eight tools. This one has about **twenty** — a real, domain-specific SD-WAN server over the Cisco vManage dataservice API. The jump in scale is the point. When a server exposes twenty tools, two new questions appear that you never had to ask about your own: how did the author decide where one tool ends and the next begins, and how does a *model* choose the right one from twenty?

You'll explore it the disciplined way — **Inspector first** — read how REST endpoints were mapped onto operator-shaped tools, then put a model on top and watch it pick. Leave the server running at the end; exercise 6.4 (DefenseClaw) can scan it as a "real server" comparison.

> **Reconcile note:** some older prose for this server says "five tools." The actual server exposes ~20 (`get_inventory`, `get_wan_edge_devices`, `get_device_tunnels`, `get_control_connections`, `get_transport_health_summary`, `get_health_status`, `get_alarms`, `get_events`, templates, policies, `get_running_config`, `generate_audit_report`, …). Trust the live `tools/list`, not the prose.

## What You'll Learn

- What a larger, domain-specific MCP server looks like: ~20 tools over one API
- How a server author maps REST endpoints onto tools an agent can choose between
- How to explore an unfamiliar server with Inspector before writing any prompt
- Where this server's design differs from yours, and what that costs

## Before You Start

- Exercise 4.4 complete
- vManage reachable; `VMANAGE_HOST` (pod FQDN + exposed port) + creds

## Architecture Overview

| Component | Role |
|---|---|
| `code/server-sdwan/sdwan_mcp_server.py` | the server — FastMCP 2.x, ~20 read-only tools, `:7004/mcp` |
| **vManage dataservice API** | the backend; each tool is a GET after `j_security_check` login |
| MCP Inspector / fast-agent | the clients you explore and drive it with |

```text
Inspector / fast-agent --HTTP--> sdwan-mcp (:7004) --REST(login+GET)--> vManage
   ~20 tools, namespaced sdwan__*     read-only
```

## Setup

### Step 1 — start the server (terminal 1)

```bash
cd code/server-sdwan
cp .env.example .env         # set VMANAGE_HOST=<pod FQDN>:<port>, VMANAGE_USERNAME/PASSWORD
./run.sh                     # serves Streamable HTTP on :7004/mcp
```

> If your pod pre-hosts this server on `cclorchestrator78:7004`, you can point the clients there instead of running it locally. Either way the endpoint is `/mcp` on `:7004`.

## Exercises

### Part 1 — explore it in Inspector (10 min)

```bash
npx @modelcontextprotocol/inspector
```

Connect (Streamable HTTP, `http://localhost:7004/mcp`, no auth header for this server). In the **Tools** tab, read the surface.

**A1.** Pick **three** tools and write, for each: its name, its one-line purpose, and the REST concept it maps to. Good candidates: `get_inventory`, `get_device_tunnels`, `get_transport_health_summary`.

> [SCREENSHOT 1: Inspector Tools tab — the ~20 sdwan__ tools listed] <!-- captured at dry-run; needs vManage -->

**A2.** Notice the **granularity choices**. There's `get_device_tunnels` *and* `get_control_connections` *and* `get_transport_health_summary` — all touch connection state. Why would an author split those into separate tools instead of one `get_connections`?

> Answer to check yourself: each answers a different *operator question* — "are my tunnels up?" vs "is control plane connected?" vs "is transport healthy?" Intent-shaped tools let a model map a question to a tool directly. One mega-tool would push that disambiguation into arguments and raise the chance of a wrong call. (Same lesson as exercise 4.3, now at scale.)

### Part 2 — drive it with a model (9 min)

```bash
cd ../client-fastagent
fast-agent go -c lab-sdwan.yaml --servers sdwan --model openrouter.$OPENROUTER_MODEL
```

Ask an SD-WAN question:

```text
Is the Site-10 edge healthy? Check its tunnels and any alarms.
```

The model has ~20 tools to choose from. Watch which it calls (`sdwan__get_device_tunnels`, `sdwan__get_alarms`, …).

> [SCREENSHOT 2: fast-agent — the model selecting tunnel/alarm tools and summarizing Site-10 health] <!-- captured at dry-run; needs vManage + model -->

**Checkpoint 1:** one SD-WAN question answered end to end, and you can see which tools the model picked.

**B1.** With twenty tools, did the model pick well? What makes selection *harder* at twenty tools than at eight — and what could a server author do to help (naming, descriptions, hiding rarely-used tools)?

### Part 3 — compare to your server (3 min)

**C1.** Name two ways this server's design differs from your Module 4 server (e.g. tool count, optional `fqdn` arg on every tool, no resources/prompts, no elicitation gate because it's read-only). What does each difference cost or buy?

**Reflection Questions**

1. Twenty tools over one API — where did the author draw tool boundaries, and by what principle?
2. Selection quality: what degrades as a server grows past ~30 tools, and what would you hide? (This sets up exercise 5.3.)
3. This server is read-only, so it has no elicitation gate. Is that the right call? When would a read-only server still want one?

## Verify

**Success Criteria**

- Inspector lists the server's tools and you can describe three of them
- One SD-WAN question answered end to end through the client
- The server is left running — Exercise 6.4 can scan it

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| server exits: "vManage authentication failed" | wrong creds or host | fix `VMANAGE_USERNAME`/`PASSWORD`/`VMANAGE_HOST` in `.env` |
| tools error with a 403/connection error | wrong exposed port, or vManage unreachable | confirm the pod's exposed vManage FQDN+port |
| Inspector won't connect | wrong transport/url | Streamable HTTP, `http://localhost:7004/mcp` |
| model picks the wrong tool | ambiguous question at 20 tools | be specific; this is the Part 2 lesson |
| `fix_url` forces :443 | you set a bare host with no port | include the exposed port in `VMANAGE_HOST` |

## Quick Reference

```bash
# terminal 1 — the server:
cd code/server-sdwan && ./run.sh                 # :7004/mcp, ~20 read-only tools
# terminal 2 — the client:
fast-agent go -c lab-sdwan.yaml --servers sdwan --model openrouter.$OPENROUTER_MODEL
```

- ~20 read-only vManage tools, namespaced `sdwan__*`. Each takes an optional `fqdn` (defaults to `VMANAGE_HOST`).
- Explore with **Inspector first**, then drive with a model.
- **Leave it running** for exercise 6.4.

---

**Source material:** `expansion/sdwam-mcp.md` and `code/server-sdwan/` (vendored from the sibling repo's `mcp/sdwan/`). The live `tools/list` is authoritative on tool count.
