# Agent with Streaming

**Category:** 02 · AI Agents · **Duration:** 8 min · **Runs on:** `linuxdesktop64` · **Targets:** —

**Devices in play:** `ciscovmanage3` (vManage, the SD-WAN controller) — read-only, over its REST API.

## Introduction

The 2.2 agent was correct but silent — you stared at a frozen prompt while it worked, then the whole answer appeared at once. This exercise adds **streaming**: tokens and progress events arrive as they happen.

This matters more for agents than for chat, because an agent's slow part is often a **tool** — an SSH call or an API that takes twenty seconds. Streaming lets you emit "connecting… / received… / parsing…" from inside the tool so the user knows the system is alive. You'll see two streams at once: the model's token updates, and custom progress events the tool itself writes.

## What You'll Learn

- How a streamed response differs from a buffered one, on the wire
- Why streaming matters when a tool takes 20 seconds over SSH
- Where streaming and tool calls interact — what can and cannot be streamed

## Before You Start

- Exercise 2.2 complete

## Architecture Overview

| Component | Role |
|---|---|
| `agent_streaming.py` | the 2.2 agent + streaming |
| `ChatOpenAI(..., streaming=True)` | the model streams tokens as they generate |
| `get_stream_writer()` in the tool | the tool emits **custom** progress events |
| `agent.stream(..., stream_mode=["updates","custom"])` | consumes both streams together |

```text
agent.stream -> "updates" (model/tool steps) + "custom" (tool's own progress)
   tool writes: start -> download -> completed   while the HTTP call runs
```

## Setup

### Step 1 — same venv

```bash
cd code/agents && . .venv/bin/activate
```

## Exercises

### Part 1 — watch it stream (5 min)

```bash
python agent_streaming.py
```

It runs four queries in sequence. Watch the log: for the inventory fetch you'll see the tool's own events — `{"stage": "start", ...}`, `{"stage": "download", ...}`, `{"stage": "completed", ...}` — interleaved with the model's `updates`.

> [SCREENSHOT 1: streaming log — the tool's start/download/completed custom events during the fetch] <!-- captured at dry-run; needs vManage + model -->

Read the two mechanisms:

- `ChatOpenAI(..., streaming=True)` → the model emits tokens incrementally instead of one block.
- `writer = get_stream_writer(); writer({"stage": ...})` inside `fetch_inventory` → the **tool** emits its own progress, consumed as `stream_mode="custom"`.

**A1.** Which events came from the *model* and which from the *tool*? Which `stream_mode` carried each?

> Answer to check yourself: `updates` carries model/tool step events from the framework; `custom` carries the `{"stage": ...}` dicts your tool wrote itself. Streaming is two sources into one loop.

### Part 2 — why it matters for a slow tool (3 min)

**B1.** The `fetch_inventory` HTTP call still takes however long it takes — streaming doesn't make it faster. So what does streaming actually buy the user during those seconds, and what does a good client show?

> Answer to check yourself: the tool call still blocks until the HTTP response returns — streaming can't parallelize a single synchronous call. What it buys is *feedback*: the user sees "connecting / parsing / done" instead of a frozen screen. The answer isn't faster; the experience is honest about what's happening.

**Reflection Questions**

1. Buffered vs streamed — what's the difference on the wire, and what does each feel like to a user?
2. A 20-second SSH tool call: what can streaming show during it, and what can it *not* change?
3. Where does streaming connect back to MCP? (Recall the progress notifications your Module 4 server sends via `ctx.report_progress`.)

## Verify

**Success Criteria**

- Tokens render incrementally rather than all at once
- You can explain why a slow tool call still blocks, and what a client does about it

**Done when:** you saw the tool's custom progress events stream during the fetch, and can explain that streaming improves feedback, not tool speed.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| no custom events | tool didn't call `get_stream_writer()` / not consuming `custom` | keep `stream_mode=["updates","custom"]` |
| output still appears all at once | `streaming=True` not set on the LLM | confirm `ChatOpenAI(..., streaming=True)` |
| `VMANAGE_HOST not set` | `.env` | same `.env` as 2.1/2.2 |
| tool errors mid-stream | vManage unreachable | the fetch needs the pod's vManage; events still show up to the failure |

## Quick Reference

```bash
python agent_streaming.py      # runs four queries, streaming
```

- Two streams: `updates` (model/tool steps) + `custom` (your tool's progress events).
- `streaming=True` on the LLM; `get_stream_writer()` inside the tool.
- Streaming improves **feedback during a slow tool**, not the tool's speed. Ties to MCP `ctx.report_progress` (Module 4).

---

**Source material:** `code/agents/agent_streaming.py`
