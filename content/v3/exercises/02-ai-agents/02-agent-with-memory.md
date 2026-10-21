# Agent with Memory

**Category:** 02 · AI Agents · **Duration:** 9 min · **Runs on:** `linuxdesktop64` · **Targets:** `ciscovmanage3` (read-only, via API)

**Devices in play:** `ciscovmanage3` (vManage, the SD-WAN controller) — read-only, over its REST API.

## Introduction

The 2.1 agent answered one question and forgot everything. Ask it "and how many of those are down?" and it has no idea what "those" means — each call starts blank. This exercise adds **short-term memory** so a conversation can build.

The reveal is deliberately unglamorous: memory is not a special faculty. It is the **message history, re-sent every turn**. A checkpointer stores the running transcript under a `thread_id`; each new turn ships the whole prior conversation back to the model. That's why the agent can resolve "those" — and also why a long session gets slower and more expensive every turn.

## What You'll Learn

- Why a stateless agent cannot answer "and what about the other one?"
- How short-term memory is implemented: message history, not magic
- What memory costs — every turn re-sends the whole conversation

## Before You Start

- Exercise 2.1 complete

## Architecture Overview

| Component | Role |
|---|---|
| `agent_short_term_memory.py` | the 2.1 agent + a checkpointer |
| `InMemorySaver` (LangGraph) | stores the running message history |
| `thread_id = "sdwan_agent_session"` | the key the transcript is stored under |
| `fetch_inventory` | unchanged — called **once**, then reused from memory |

```text
turn 1: [system + Q1] -> model -> fetch_inventory -> answer   (transcript saved)
turn 2: [full transcript + Q2] -> model -> answers from memory, NO tool call
```

## Setup

### Step 1 — same venv as 2.1

```bash
cd code/agents && . .venv/bin/activate      # from exercise 2.1
```

## Exercises

### Part 1 — hold a conversation (6 min)

```bash
python agent_short_term_memory.py
```

It's interactive. Ask, in sequence:

```text
You: Show me the full device inventory
You: How many of those are WAN edges?
You: And which one has the most interfaces?
```

**A1.** Turns 2 and 3 use "those" and "which one" — references to turn 1. Did the agent resolve them? Did it call `fetch_inventory` again on turns 2 and 3, or reuse the first result?

> [SCREENSHOT 1: interactive session — turn 2 resolving "those" with no second tool call] <!-- captured at dry-run; needs vManage + model -->

> Answer to check yourself: it resolves the references and does **not** re-fetch — the system prompt tells it to reuse the stored inventory, and the checkpointer makes that inventory still be in context on turn 2. Remove the checkpointer and turn 2 is blank.

### Part 2 — see the cost (3 min)

Read how memory works: `checkpointer = InMemorySaver()`, passed into `create_agent(..., checkpointer=checkpointer)`, and every `agent.invoke(..., {"configurable": {"thread_id": thread_id}})` uses the same `thread_id`.

**B1.** On turn 3, what exactly gets sent to the model — just turn 3, or turns 1+2+3? What does that do to input tokens (and cost, and latency) as a session grows?

> Answer to check yourself: the **whole transcript** is re-sent each turn. Input tokens grow with the conversation, so a long session costs and latency climb every turn. "Memory" is re-sending history, nothing more — which is why real systems summarize or trim it.

**Reflection Questions**

1. Stateless 2.1 vs memory 2.2 — what is the single mechanical difference?
2. The agent reuses the first inventory instead of re-fetching. What made that happen — the checkpointer, the system prompt, or both?
3. If this ran for 200 turns, what would you add to stop the context (and cost) growing without bound?

## Verify

**Success Criteria**

- A follow-up question resolves a reference from the previous turn
- You can show the request where the prior turns were re-sent
- You can state what happens to cost and latency as the conversation grows

**Done when:** a "those"/"which one" follow-up resolved correctly, and you can explain that memory = re-sent history with a growing token cost.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| turn 2 acts like turn 1 (no memory) | `thread_id` differs between turns, or checkpointer missing | all turns must share one `thread_id`; keep `checkpointer=` |
| agent re-fetches every turn | system prompt not applied on turn 1 | the first turn must include `system_prompt` |
| `VMANAGE_HOST not set` | `.env` not loaded | same `.env` as 2.1 |
| session won't exit | it waits for input | type `exit` or `quit` |

## Quick Reference

```bash
python agent_short_term_memory.py      # interactive; 'exit' to quit
```

- Memory = **message history re-sent each turn**, stored by `InMemorySaver` under a `thread_id`.
- Same `thread_id` across turns = one conversation.
- Cost/latency grow with conversation length — trim or summarize for long sessions.

---

**Source material:** `code/agents/agent_short_term_memory.py`
