# Build a Read-Only Tool

**Category:** 04 · Build an MCP Server · **Duration:** 25 min · **Runs on:** `linuxdesktop64` · **Targets:** `sdceightkv24` → pings `sdceightkv11`

**Devices in play:** `sdceightkv24` (DR edge — runs the ping) → `sdceightkv11` (DC edge — the ping target).

## Introduction

This is the one where you write a tool. By the end, a model will answer "can DR reach DC?" by calling code you wrote twenty minutes earlier.

You'll build `ping_from_device(target, device=...)` — it issues an ICMP echo *from a device's own control plane* and reports whether the target answered. It reuses the `run_show` helper you read in 4.1, so there is no new SSH plumbing — just a function, a docstring, and a decision about what to return.

The habit this exercise drills: **Inspector before chat.** You verify every tool in the protocol debugger *before* you let a model near it, so that when the model misbehaves you already know the tool itself is sound.

## What You'll Learn

- How a Python signature and docstring become a tool schema and description
- Why the docstring is the part the model actually reads — write it deliberately
- How to return a verdict plus evidence, rather than raw CLI output
- Why 'no connectivity' is a successful tool result, not an error

## Before You Start

- Exercise 4.1 complete
- Inspector open alongside your editor

## Architecture Overview

| Piece | Role |
|---|---|
| `ping_from_device` (you write it) | new `@mcp.tool`, read-only, in `main.py` |
| `run_show` (`main.py:111`) | existing helper — you reuse it, no new SSH code |
| `sdceightkv24` (DR edge) | the device that *runs* the ping |
| `sdceightkv11` (DC edge, `10.2.0.1`) | the `target` you ping *to* |

```text
model --call ping_from_device(target=10.2.0.1, device=sdceightkv24)-->
   server --run_show("ping 10.2.0.1")--> sdceightkv24 --ICMP--> sdceightkv11
```

## Setup

### Step 1 — open the server source

```bash
cd code/server
$EDITOR app/main.py        # add your tool near the other read-only tools (~line 300)
```

## Exercises

### Part 1 — write the tool (10 min)

Add this next to the other read-only tools in `main.py`:

```python
@mcp.tool(annotations=types.ToolAnnotations(readOnlyHint=True))
async def ping_from_device(target: str, ctx: Context, device: DeviceName = DEFAULT_DEVICE) -> str:
    """Ping `target` (an IP or hostname) from `device` and report reachability.

    Read-only: sends ICMP echoes from the device's own control plane. Use this
    to answer connectivity questions like "can DR reach the DC edge?". A
    'not reachable' result is a normal, successful answer — not an error.
    """
    await ctx.report_progress(0, 1, f"Pinging {target} from {device}...")
    try:
        output = await run_show(f"ping {target}", device)
    except Exception as exc:
        return f"Error talking to {device}: {exc}"
    await ctx.report_progress(1, 1, "Done")
    reachable = "!!!!" in output or "Success rate is 100 percent" in output
    verdict = "reachable" if reachable else "NOT reachable (or partial loss)"
    return f"{device} -> {target}: {verdict}\n\n{output}"
```

Read your own code before you run it — each line has a job:

- `@mcp.tool(... readOnlyHint=True)` → registers the tool and declares it changes nothing.
- the **docstring** → this is what the *model reads* to decide when to call it. "can DR reach the DC edge?" is in there on purpose, so the model maps that question to this tool.
- `target: str`, `device: DeviceName = DEFAULT_DEVICE` → the schema: a free-text target, a device enum defaulting to DR.
- `run_show(f"ping {target}", device)` → reuse the existing helper; no new SSH.
- `except Exception` → **return** the error as text, never raise — the model reads it and can retry.
- the `verdict` line → you return a *verdict plus the raw output*, not just the dump. The model gets an answer and the evidence behind it.

### Step 2 — verify in Inspector (always Inspector before chat)

Restart the server (`Ctrl-C`, `./run.sh`) and reconnect Inspector. In the **Tools** tab:

1. `ping_from_device` is present, `readOnlyHint: true`, schema has `target` (string) and `device` (enum, default `sdceightkv24`).
2. Call it: `target = 10.2.0.1` (that's `sdceightkv11`, the DC edge), `device = sdceightkv24`.

**Checkpoint 1:** the tool is listed with the right schema, and the call returns a verdict line plus the raw ping output.

> [SCREENSHOT 1: Inspector Tools tab — ping_from_device called with target=10.2.0.1, device=sdceightkv24, showing the "reachable" verdict and ping output] <!-- captured at dry-run; needs reachable pod -->

### Step 3 — now with the model (10 min)

Point fast-agent at your server with a real model and ask the *question*, not the command:

```bash
cd ../client-fastagent
fast-agent go -c lab1.yaml --servers my_server --model openrouter.$OPENROUTER_MODEL
```

```text
Can the DR edge reach the DC edge? Use a ping.
```

**Checkpoint 2:** the model chose `my_server__ping_from_device`, filled `device=sdceightkv24` and a DC target, and answered in English with your verdict.

> Think first: if the model refuses to call your tool, or calls `get_interfaces` instead — is the problem your server or your docstring? (You proved the server in Step 2. So it's the docstring.)

**Reflection Questions**

1. You returned a *verdict + evidence*, not raw output. Why is "reachable" + the dump better for a model than the dump alone — or than "reachable" alone?
2. The `reachable` check looks for `!!!!` (IOS) and a success-rate line. `sdceightkv24` is IOS-XE, but 6 of your devices are **NX-OS**, whose ping output reads differently. What happens if someone pings *from* a Nexus? (Hold that thought — it's exercise 4.3.)
3. "Not reachable" returns normally instead of raising. What can the model do with a normal result that it could not do with a transport error?

## Verify

**Success Criteria**

- `ping_from_device` appears in `tools/list` carrying `readOnlyHint`
- It answers a DR→DC reachability question from fast-agent
- You verified it in Inspector *before* asking a model to call it

**Done when:** both checkpoints pass — Inspector shows the tool and a verdict, and a model answers a reachability question by calling it.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| tool not in `tools/list` after restart | edit not saved, or server not restarted | save `main.py`, `Ctrl-C` and `./run.sh` again |
| `NameError: DeviceName` / `Context` | added the tool outside `main.py` | it must live in `main.py` where those names are imported |
| verdict always "NOT reachable" but output looks fine | NX-OS/XE ping markers differ from `!!!!` | that's exercise 4.3 — note it, don't over-fix here |
| model calls the wrong tool | docstring doesn't match the question shape | rewrite the docstring to name the question it answers |
| `Error talking to <device>` | device unreachable from this pod | network/pod issue, not your tool — see exercise 1.1 |

## Quick Reference

```python
@mcp.tool(annotations=types.ToolAnnotations(readOnlyHint=True))
async def ping_from_device(target: str, ctx: Context, device: DeviceName = DEFAULT_DEVICE) -> str:
    """...docstring is the model-facing description — write it deliberately..."""
    output = await run_show(f"ping {target}", device)   # reuse the helper
    return f"{device} -> {target}: <verdict>\n\n{output}"  # verdict + evidence
```

- **Inspector before chat**, every time.
- Docstring = the description the model reads.
- Return a **verdict plus evidence**. Return errors as text; never raise.

---

**Source material:** Reuse `run_show` in `code/server/app/main.py`; pattern from `content/v2/participants/04_Lab3_Build_Guide.md`
