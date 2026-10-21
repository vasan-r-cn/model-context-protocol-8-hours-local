# Environment Setup & Sandbox Tour

**Category:** 01 · LLM Foundations · **Duration:** 12 min · **Runs on:** `linuxdesktop64` (your main workstation) · **Targets:** —

**Devices in play:** No device touched directly — the health ladder (`sanity_check.sh`) probes every inventory device over SSH; the default device is `sdceightkv24` (DR SD-WAN edge).

## Introduction

Before you write a line of agent code, you need to know two things: where every moving part of the day runs, and how to prove your pod is healthy without an instructor leaning over your shoulder.

Good news first — **you have your own complete topology pod.** Nothing is shared. Your DC, your DR, your branches, your Splunk, your controllers. That means every command in every lab guide is the *same* for everyone in the room: `localhost:8000` and `sdceightkv24`, no seat numbers, no per-seat ports, no `10.<seat>.x.x` arithmetic.

> **Which machine am I on?** Your pod gives you **two** Linux desktops, and both are yours:
> - **`linuxdesktop64`** (Site-10) — your **main workstation**. Run everything here: the MCP server, fast-agent, Inspector, and the Lab 5 orchestrator.
> - **`linuxdesktop65`** (Site-20) — used **only** for the DefenseClaw security scan (exercises 4/6.4).
>
> Wherever a guide says "your desktop," it means **`linuxdesktop64`** unless it names `linuxdesktop65` explicitly. Everything in this exercise runs on `linuxdesktop64`.

This exercise is a guided tour of the pod and a single health script, `sanity_check.sh`. The script is not a pass/fail blob — it is a **dependency ladder**. Link 2 depends on link 1, link 6 on link 4. When something breaks, the *first* failure is almost always the only real problem; everything below it fails because it was standing on the broken link. Learn to read it that way now and you will debug every later lab in seconds.

## What You'll Learn

- Where every component of the day runs, and on which host
- How to build the workshop virtualenv with `uv` and Python 3.12
- How to read `sanity_check.sh` — a dependency ladder, not a pass/fail blob
- Which failures are yours to fix and which are environmental

## Before You Start

- Nothing. This is the first exercise of the day.

## Architecture Overview

Everything below runs **inside your own pod**. Only OpenRouter and ThousandEyes leave it.

| Component | Runs on | Port | Started by |
|---|---|---|---|
| **Your MCP server** (`code/server/`) | `linuxdesktop64` | `8000` (localhost) | you — `./run.sh` |
| **fast-agent** (`code/client-fastagent/`) | `linuxdesktop64` | — (CLI) | you |
| **MCP Inspector** | `linuxdesktop64`, browser | `6274` | you — `npx` |
| **Multi-agent orchestrator** (Lab 5) | `linuxdesktop64` | `7860` (Gradio) | you |
| **DefenseClaw** (Lab 4/6.4) | `linuxdesktop65` | — | you |
| **Splunk MCP Server** (`code/server-splunk/`) | `linuxdesktop64` | `8050` `/sse` | you (Module 5) → pod Splunk `:8089` |
| **SD-WAN MCP Server** (`code/server-sdwan/`) | `linuxdesktop64` | `7004` `/mcp` | you (Module 5) → pod vManage |
| **Network devices** (`sdceightkv24`, the Nexus pair, …) | the lab topology | SSH 22 | nobody — reached over SSH |

The one chain that must be true for the day to be hands-on rather than a demo:

```
linuxdesktop64  --SSH-->   your sdceightkv24 (DR)        # or your server is useless
linuxdesktop64  --HTTPS->  your cclorchestrator78:8089   # or Splunk (Module 5) is a demo
linuxdesktop64  --HTTPS->  openrouter.ai                 # or no model can run
```

## Setup

### Step 1 — build the pod the first time

The pod image ships Python 3.10. fast-agent needs 3.12, so the bootstrap script has `uv` fetch a **private** 3.12 rather than touching the system Python. Run it once:

```bash
cd ~/mcp-8-hours
./scripts/bootstrap_desktop.sh    # uv's private 3.12, both venvs, offline tests
```

Read what it does — every step is a named job:

- Installs `uv` (the fast Python package manager) if it is missing.
- Fetches a private Python **3.12** — your system `python3` (3.10) is left alone.
- Builds **two** virtualenvs: the MCP server's and fast-agent's, each from its own `requirements.txt`.
- Runs an `import` smoke check on both, then the **offline** pytest suite — no device needed.

> [SCREENSHOT 1: bootstrap_desktop.sh final lines — both venvs built, "31 passed" from the offline test run]

### Step 2 — export your OpenRouter key

The model provider for the whole day is OpenRouter. Export your key into the shell you will work in:

```bash
export OPENROUTER_API_KEY=sk-or-v1-...    # the key on your lab sheet
export OPENROUTER_MODEL=anthropic/claude-sonnet-4
```

(Alternatively it can live in `code/client-fastagent/fastagent.secrets.yaml`, `chmod 600`. Never put it in a config file that gets shared.)

## Exercises

### Part 1 — run the ladder and read it top-down

Run the quick ladder first — it skips the device and network links, so it works even before your pod's network is fully up:

```bash
./scripts/sanity_check.sh --quick
```

Each line is one rung, printed with its evidence:

- `PASS` — verified. The evidence is printed next to it.
- `FAIL` — broken. **Fix this before anything below it** — the ladder is ordered.
- `BLOCKED` — can't be checked yet because something upstream is missing (e.g. no management address in `inventory.yaml`). Not your code's fault.
- `SKIP` — deliberately not run (`--quick`, or no key configured).

On a correctly built pod with the network still coming up, a representative run looks like this (your exact lines are captured at the start of class):

```text
PASS: 1  Python 3.12 and uv present
PASS: 2  Server venv builds and imports
SKIP: 3  Inventory devices reachable over SSH        (--quick)
...
PASS: 7  Offline test suite (pytest)                 # never needs a device
PASS: 9  Blast radius: write to a production device is refused
```

> [SCREENSHOT 2: your own `sanity_check.sh --quick` output, top to bottom]

Now run the **full** ladder once the network is up:

```bash
./scripts/sanity_check.sh
```

### Part 2 — locate the three checks that never need a device

Checks **7 (pytest)**, **9 (blast radius)** and **10 (elicitation gate)** are the regression gate for the *code itself*. They run anywhere — including CI — with no lab network. Find all three in your output and note which passed.

**Reflection Questions**

1. Check 2 passes but check 4 (server starts) FAILs with "port 8000 already taken." Which earlier exercise might have left a server running? How would you find and stop it?
2. Check 3 (SSH reachability) is BLOCKED, not FAIL. Why is that distinction correct — what is the difference between "your code is wrong" and "this can't be tested yet"?
3. Your neighbour's check 9 passes and yours fails. The safety code is identical. What else could differ between two pods that would change that result?

> Answer to check yourself (Q2): a BLOCKED rung means an *upstream* requirement is missing (e.g. `inventory.yaml` has no management address for the default device), so the rung is untestable — not that the safety model is broken. A FAIL means the thing was tested and came back wrong.

## Verify

**Success Criteria**

- `./scripts/sanity_check.sh --quick` reports no `FAIL`
- `uv`, `python3.12` and the server venv are present
- Your OpenRouter API key is exported and the key check passes
- You can name the host your MCP server will run on, and its port

**Done when:** `sanity_check.sh --quick` shows no `FAIL`, and you can answer "where does my MCP server run?" with `linuxdesktop64, localhost:8000`.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `python3.12: command not found` | bootstrap didn't run, or `uv`'s shims aren't on `PATH` | `./scripts/bootstrap_desktop.sh`; open a new shell so `PATH` reloads |
| Check 1 FAIL: `uv` not found | image missing `uv` or not on `PATH` | re-run bootstrap; `source ~/.bashrc` |
| Check 2 FAIL: venv import error | PyPI blocked while building the venv | check network, re-run `bootstrap_desktop.sh` |
| Check 12 SKIP, not PASS | `OPENROUTER_API_KEY` not exported in this shell | `export OPENROUTER_API_KEY=...`, re-run |
| Script "can't find the workshop" | run from an unusual directory | `WORKSHOP_ROOT=<dir containing code/> ./scripts/sanity_check.sh` |

## Quick Reference

```bash
# First time on a pod:
./scripts/bootstrap_desktop.sh

# Health ladder:
./scripts/sanity_check.sh            # full
./scripts/sanity_check.sh --quick    # skip device/network checks

# Your key:
export OPENROUTER_API_KEY=sk-or-v1-...
export OPENROUTER_MODEL=anthropic/claude-sonnet-4
```

- Your MCP server: **`linuxdesktop64`, `localhost:8000`**.
- Device-free checks: **7 (pytest), 9 (blast radius), 10 (elicitation)**.
- Read the **first** FAIL, not the last.

---

**Source material:** `scripts/sanity_check.sh`, `docs/where-things-run.md`
