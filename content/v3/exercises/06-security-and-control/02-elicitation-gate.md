# Human Approval — the Elicitation Gate

**Category:** 06 · MCP Security & Control · **Duration:** 12 min · **Runs on:** `linuxdesktop64` · **Targets:** `sdceightkv24`

**Devices in play:** `sdceightkv24` (DR SD-WAN edge, writable).

## Introduction

The role gate from 6.1 decides *whether* a device may be written at all. The elicitation gate decides *whether this specific change goes through right now* — by asking a human, mid-call, to confirm.

Elicitation is the MCP primitive for a **server-initiated question to the user**. When `configure_interface` is about to touch a live router, the server pauses and asks "proceed?" The crucial detail is *where* this lives: in the **server**, not in a prompt. A prompt that says "always confirm destructive changes" is advice a model can ignore. A server that will not apply the change until it receives a confirmation is a gate the model cannot route around.

You'll drive the same change three ways by changing one line of client config — `forms`, `auto-cancel`, `none` — and watch the server's behavior change with the client's capability.

## What You'll Learn

- What elicitation is, and where in the call it interrupts
- What a server must do when the client cannot ask the human
- The three client modes — `forms`, `auto-cancel`, `none` — and what each produces
- Why the gate belongs in the server, not in the prompt

## Before You Start

- Exercise 6.1 complete

## Architecture Overview

| Piece | Where | Role |
|---|---|---|
| `_confirm_change(ctx, description)` | `main.py:193` | the gate: checks client capability, elicits, returns `(proceed, warning)` |
| `elicitation.mode` | `lab1.yaml` | the client's half: `forms` \| `auto-cancel` \| `none` |
| `check_client_capability(elicitation=...)` | inside `_confirm_change` | the negotiation that decides which path runs |

```text
configure_interface -> _confirm_change -> client supports elicitation?
   yes -> ask the human (forms) -> accept: apply | decline: "Change cancelled by user."
   no  -> graceful-degrade path (depends on mode) -> warn or cancel
```

## Setup

### Step 1 — server + client

```bash
cd code/server && ./run.sh
cd ../client-fastagent
export MCP_SERVER_URL=http://127.0.0.1:8000/mcp MCP_AUTH_TOKEN=cisco-mcp-workshop
```

`lab1.yaml` ships `elicitation: mode: forms`.

## Exercises

### Part 1 — `forms`: accept once, decline once (5 min)

Start fast-agent with a real model (the gate is client-side; it fires regardless, but you want a model to drive the change):

```bash
fast-agent go -c lab1.yaml --servers my_server --model openrouter.$OPENROUTER_MODEL
```

Ask for a change on the writable DR device:

```text
Create loopback 950 on sdceightkv24.
```

The server reaches `_confirm_change` and fast-agent pops a **form**. **Accept** it.

**Checkpoint 1:** on accept, the loopback is created (the result names a pre-change snapshot). Run it again, and this time **decline** — the result is exactly `Change cancelled by user.` and nothing was applied.

> [SCREENSHOT 1: fast-agent forms dialog asking "...modifies a live lab router. Proceed?" with accept/decline] <!-- captured at dry-run; interactive TTY -->

**A1.** Where in the call did the pause happen — before or after the role check, before or after SSH?

> Answer to check yourself: after the role check (`may_write_to` already passed), before SSH. The server has decided the device is *writable*; the gate decides whether to proceed *now*. Decline → no SSH.

### Part 2 — `auto-cancel`: refuse without asking (3 min)

Stop fast-agent. Edit `lab1.yaml`:

```yaml
    elicitation:
      mode: auto-cancel
```

Re-run the same request. This mode answers the server's elicitation with an automatic cancel.

**Checkpoint 2:** the result is `Change cancelled by user.` and **no SSH is attempted**. Verified timing from the build log: this path returns in **~11 ms** — the device is never touched.

### Part 3 — `none`: the deliberate degrade (2 min)

Edit `lab1.yaml` to `mode: none` and read `_confirm_change` again:

```python
supports_elicitation = ctx.session.check_client_capability(...)
if not supports_elicitation:
    return True, "WARNING: client does not support elicitation — change applied without interactive confirmation.\n\n"
```

**B1.** With `none`, the client advertises *no* elicitation capability. What does the server do — block, or proceed with a warning?

> Answer to check yourself: it **proceeds**, prepending a WARNING to the result. This is a deliberate server decision for clients that genuinely cannot ask a human (the old LibreChat harness was one). The server chooses degrade-with-warning over refuse-everything — a documented trade-off, not an accident. Set it back to `forms` when done.

**Reflection Questions**

1. Why does the gate live in the server rather than in a system prompt that says "always confirm"?
2. `auto-cancel` and `none` both avoid a human click, but one cancels and one proceeds. Why would a server author offer both?
3. The gate fires *after* the role check. Why is that ordering right?

## Verify

**Success Criteria**

- With `mode: forms`, accepting applies the change and declining does not
- With `auto-cancel`, the change is refused and no SSH is attempted
- You can state what `mode: none` does, and why that is a deliberate server decision

**Done when:** you've driven all three modes, seen `forms` accept-vs-decline diverge, confirmed `auto-cancel` touches no device, and can explain why `none` proceeds-with-warning is a choice.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| no form appears in `forms` mode | `mode` under the wrong server block, or typo (`auto_cancel`) | it's `auto-cancel` with a hyphen; nest under `my_server` |
| change applied without asking | `mode: none`, or client advertised no elicitation | set `mode: forms`; check the WARNING line in the result |
| "Refusing to configure" instead of a form | you targeted a non-writable device | target `sdceightkv24` (DR, writable) — the gate is after the role check |
| form appears but SSH then errors | pod off-network | the gate worked; SSH failure is environmental |

## Quick Reference

```yaml
# lab1.yaml
mcp:
  servers:
    my_server:
      elicitation:
        mode: forms        # forms | auto-cancel | none
```

- `forms` → ask the human; accept applies, decline → `Change cancelled by user.`
- `auto-cancel` → auto-refuse, **no SSH** (~11 ms).
- `none` → client has no elicitation capability → server **proceeds with a WARNING** (deliberate degrade).
- The gate lives in the **server** (`_confirm_change`), not the prompt.

---

**Source material:** `_confirm_change` in `code/server/app/main.py`; `elicitation` block in `code/client-fastagent/lab1.yaml`
