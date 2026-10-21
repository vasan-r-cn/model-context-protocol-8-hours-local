# Simple Agent — Tools Wired by Hand

**Category:** 02 · AI Agents · **Duration:** 18 min · **Runs on:** `linuxdesktop64` · **Targets:** `ciscovmanage3` (read-only, via API)

**Devices in play:** `ciscovmanage3` (vManage, the SD-WAN controller) — read-only, over its REST API.

## Introduction

In Module 1 the model hit a wall: it could not look at anything. This exercise gives it one way to look — a single tool — and in doing so turns a model into an **agent**.

The thing to internalize: an agent is not a smarter prompt. It is a **loop**. The model is told what tools exist; it answers not with prose but with a *tool call*; your code runs the tool and feeds the result back; the model reads it and answers. One tool, one decision. You'll watch that loop happen against real SD-WAN inventory.

This is also where the integration cost from Module 2.4 ("the wall") starts: *you* wrote the tool's schema, the HTTP call, the auth, the error handling. One tool, one agent — fine. The pain is what happens at twenty tools and three agents. Hold that thought; MCP (Module 3) is the answer.

## What You'll Learn

- What turns a model into an agent: a tool loop, not a bigger prompt
- How a tool is described to a model, and how the model answers with a call
- How to read an agent trace and see which tool was chosen and why
- What the agent code owns: schemas, dispatch, error handling, retries

## Before You Start

- Exercise 1.2 complete
- vManage reachable; `VMANAGE_HOST` (pod FQDN + exposed port) and key in `.env`

## Architecture Overview

| Component | Role |
|---|---|
| `sdwan_agent.py` (`code/agents/`) | the agent: LLM + one tool + `create_agent` loop |
| `fetch_inventory` (`@tool`) | the one tool — GETs the SD-WAN inventory over HTTPS |
| **vManage NVCL API** (`https://$VMANAGE_HOST/nvcl/api/inventory/`) | the backend the tool calls |
| OpenRouter | the model provider |

```text
"list my inventory" -> model -> emits tool call: fetch_inventory()
   loop runs the tool -> vManage NVCL API -> JSON back -> model -> English answer
```

## Setup

### Step 1 — venv + env

```bash
cd code/agents
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`: your `OPENROUTER_API_KEY`, and `VMANAGE_HOST=<your pod FQDN>:<exposed vManage port>`.

## Exercises

### Part 1 — run it and read the loop (9 min)

```bash
python sdwan_agent.py
```

It runs one query: *"List my full SD-WAN device inventory details."* Watch the log — you'll see the tool fire (`[TOOL] Fetching inventory -> https://.../nvcl/api/inventory/`) and then the model's summary.

> [SCREENSHOT 1: sdwan_agent.py log — the fetch_inventory tool call, then the grouped inventory answer] <!-- captured at dry-run; needs vManage + model -->

Read your own code — the two lines that make it an agent:

- **Registration** (`agent = create_agent(model=llm, tools=[fetch_inventory])`) — this is where the model is *told the tool exists*. The tool's name and docstring (`"""Fetch the SD-WAN device inventory for this lab."""`) become the description the model reads.
- **Dispatch** — `create_agent` runs the loop: when the model emits a call to `fetch_inventory`, the loop executes the Python function and returns its result to the model. You didn't write the loop; you wrote the tool and registered it.

**A1.** Point at the line that *registers* the tool and the line (inside `fetch_inventory`) that actually does the work. What does the model see that makes it choose this tool for an inventory question?

> Answer to check yourself: the model sees the tool **name** and **docstring**. "Fetch the SD-WAN device inventory" matches an inventory question, so it emits that call. The docstring is the interface — same lesson as the MCP server you'll build in Module 4.

### Part 2 — what your code owns (6 min)

Look at everything inside `fetch_inventory` that is *not* the model: the URL, `verify=False`, `timeout=30`, `raise_for_status()`, the `except httpx.HTTPError` returning `{"error": ...}`.

**B1.** List the responsibilities the *agent code* carries for this one tool. Now imagine a second tool (say, interface status) and a second agent. What multiplies?

> Answer to check yourself: you own the schema, the HTTP call, auth, TLS, timeout, error-to-result conversion, and retries — per tool. Add tools and agents and it's N×M of this glue. That is the wall. MCP moves most of it to the server author, once.

### Part 3 — break it on purpose (3 min)

Set `VMANAGE_HOST` to a bad value and rerun.

**C1.** The tool returns `{"error": ...}` rather than crashing the agent. What does the model do with an error result, and why is returning the error better than raising?

**Reflection Questions**

1. "An agent is a loop, not a bigger prompt." Defend that in one sentence using what you saw.
2. The docstring is the tool's description to the model. How is that the same idea as an MCP tool's docstring (Module 4)?
3. If vManage changes its API, which file changes — and in a 20-tool fleet, how many places?

## Verify

**Success Criteria**

- The agent answers an SD-WAN question by selecting among the registered tools
- You can point at the line that registers a tool and the line that dispatches it
- You can say what the model saw that made it pick that tool

**Done when:** the agent ran the tool and answered, and you can point at the registration line and explain the docstring-as-interface.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `VMANAGE_HOST not set` | `.env` missing the host | set `VMANAGE_HOST=<fqdn>:<port>` |
| tool returns `{"error": ...}` | vManage unreachable / wrong port | confirm the exposed vManage FQDN+port for your pod |
| `OPENROUTER_API_KEY not set` | key missing | put it in `.env` |
| model answers without calling the tool | question not inventory-shaped, or weak match | ask an inventory question; the docstring drives selection |
| TLS error | lab cert self-signed | `verify=False` is already set; confirm you're on the right host |

## Quick Reference

```bash
cd code/agents && . .venv/bin/activate
python sdwan_agent.py
```

- Agent = **model + tool loop**. `create_agent(model, tools=[...])` registers; the loop dispatches.
- The model picks a tool from its **name + docstring**.
- Your code owns schema, HTTP, auth, errors, retries — **per tool**. That cost is the wall (2.4).

---

**Source material:** `code/agents/sdwan_agent.py` (vendored from sibling repo)
