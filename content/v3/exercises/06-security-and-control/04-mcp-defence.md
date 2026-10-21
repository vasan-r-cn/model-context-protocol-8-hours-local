# MCP Defence — Scanning a Server

**Category:** 06 · MCP Security & Control · **Duration:** 13 min · **Runs on:** `linuxdesktop65` · **Targets:** a deliberately vulnerable MCP server (and, optionally, servers from Module 5)

**Devices in play:** No production device — you scan a local, deliberately vulnerable MCP server (and optionally the SD-WAN server, which reaches `ciscovmanage3`).

## Introduction

You have spent the day *building* and *controlling* servers. This exercise flips the role: you are the reviewer deciding whether a server is safe to connect to. The tool is **DefenseClaw** (Cisco AI Defense's `mcp-scanner`) — it reads a server's advertised tools, resources, and prompts and flags the defect classes that MCP introduces.

You'll scan a **deliberately vulnerable server** (`code/server/security/vulnerable_server.py`) with five planted issues, each designed to trip a different analyzer. First a no-key baseline (`yara`, `readiness`), then an LLM-enhanced pass that reads tool descriptions the way an agent would. The lesson underneath: **a clean report is evidence, not proof** — and the scariest MCP defects (tool poisoning, prompt injection) are the ones only the LLM pass sees.

## What You'll Learn

- What a scanner can find in an MCP server without running it
- The common defect classes: tool poisoning, over-broad capability, hardcoded secrets, injected prompt templates
- How an LLM-enhanced scan differs from a static one
- What a clean report does and does not prove

## Before You Start

- Python 3.12 available via `uv` (the 3.10 path does not work)
- Your OpenRouter key (Section 2 only)
- `linuxdesktop65` — your pod's DefenseClaw host

## Architecture Overview

| Component | Role |
|---|---|
| **`mcp-scanner`** (DefenseClaw) | the reviewer — connects to a server, analyzes its surface |
| `yara` analyzer | signature match (e.g. hardcoded secret patterns) — no key |
| `readiness` analyzer | production-safety gaps (missing timeout/error handling) — no key |
| `llm` analyzer | reads descriptions like an agent; catches poisoning/injection — needs key |
| **`vulnerable_server.py`** (`:8766/mcp`) | the scan target, five planted issues |

```text
mcp-scanner --analyzers yara,readiness,llm --> vulnerable_server (:8766/mcp)
   yara: secrets   readiness: timeouts   llm: hidden instructions
```

The five planted issues and who should catch each:

| # | Planted issue | Caught by |
|---|---|---|
| 1 | Tool poisoning — hidden instruction in a docstring ("do not mention this to the user") | `llm` |
| 2 | Over-broad capability — a tool that runs arbitrary shell commands | `llm` / `behavioral` |
| 3 | Hardcoded secret in a tool *description* | `yara` |
| 4 | Missing timeout / error handling | `readiness` |
| 5 | Prompt injection inside a prompt template | `llm` (`--scan-prompts`) |

## Setup

### Step 1 — Python 3.12 (the scanner needs 3.11+)

The pod ships 3.10. Give the installer a private 3.12 without touching system Python:

```bash
python3 --version        # 3.10.x on this machine
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
uv python install 3.12
```

### Step 2 — install DefenseClaw

```bash
curl -LsSf https://raw.githubusercontent.com/cisco-ai-defense/defenseclaw/main/scripts/install.sh -o /tmp/install.sh
bash /tmp/install.sh --connector none
source $HOME/.local/bin/env
defenseclaw --help
```

> If a numbered connector menu appears, type `15` for `none`. Red `✗` lines about "OpenClaw" are expected — ignore them. The line that matters: `✓ Scanner: mcp-scanner`.

```bash
defenseclaw init --connector none --non-interactive
defenseclaw-gateway start      # ALWAYS start the gateway before a scan, or it crashes
defenseclaw doctor
```

### Step 3 — start the vulnerable target (terminal 2)

```bash
pip install fastmcp
cd ~/mcp-8-hours/code/server/security
FASTMCP_STATELESS_HTTP=true python3 vulnerable_server.py    # serves :8766/mcp
```

Confirm it answers before scanning:

```bash
curl -s http://localhost:8766/mcp -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"curl","version":"1.0"}}}' | head
```

## Exercises

### Part 1 — baseline scan, no key (5 min)

Back in terminal 1:

```bash
defenseclaw setup mcp-scanner --analyzers yara,readiness \
  --scan-prompts --scan-resources --scan-instructions --non-interactive

~/.defenseclaw/.venv/bin/mcp-scanner --analyzers yara,readiness \
  --format detailed remote --server-url http://localhost:8766/mcp | tee stage1-report.txt
```

**A1.** Read `stage1-report.txt`. Which of the five planted issues did the no-key pass catch, and which did it **miss**?

> Answer to check yourself: `yara` catches the **hardcoded secret** (#3); `readiness` catches the **missing timeout** (#4). The two *agent-facing* attacks — tool poisoning (#1) and prompt injection (#5) — and the dangerous-capability judgment (#2) are **invisible** to the no-key pass. That gap is the whole reason for Part 2.

**Checkpoint 1:** `stage1-report.txt` exists and flags the secret and the readiness gap.

### Part 2 — LLM-enhanced scan (6 min)

Set all three variables together (the scanner silently falls back to OpenAI `gpt-4o` and rejects your key if you set only the API key):

```bash
export MCP_SCANNER_LLM_API_KEY="<your-openrouter-key>"
export MCP_SCANNER_LLM_MODEL="openrouter/anthropic/claude-sonnet-4.5"
export MCP_SCANNER_LLM_BASE_URL="https://openrouter.ai/api/v1"

~/.defenseclaw/.venv/bin/mcp-scanner --analyzers yara,readiness,llm \
  --format detailed remote --server-url http://localhost:8766/mcp | tee stage2-llm-report.txt
```

**B1.** Diff `stage2-llm-report.txt` against `stage1-report.txt`. The `llm_analyzer` should now flag the **tool poisoning** (#1), the **dangerous shell tool** (#2), and the **prompt injection** (#5).

> **Trust check:** this scanner does *not* fail loudly if the LLM call errors — it prints `llm_analyzer: SAFE` as if it passed. Before trusting any `llm_analyzer` line, scan the log above `=== MCP Scanner Detailed Results ===` for `AuthenticationError` / `LLM API error`. If present, the SAFE lines are meaningless until you fix the key/model/base-URL and rerun.

> [SCREENSHOT 1: stage2-llm-report.txt showing llm_analyzer flagging get_user_profile tool poisoning] <!-- captured at dry-run -->

**Checkpoint 2:** the LLM report names every planted issue the baseline missed.

### Part 3 — what a clean report proves (2 min)

**C1.** Of the issues found, which would you fix **first**, and why?

> Answer to check yourself: the **tool poisoning** (#1) — a hidden instruction that makes an agent act against the user, silently, is the one that turns a trusted server into an attacker. The hardcoded secret is bad, but it's a disclosed credential; the poisoned tool weaponizes the agent itself.

**C2.** The scan read only what the server *advertises*. What class of problem can a black-box scan never see?

**Reflection Questions**

1. The no-key pass missed the two worst issues. What does that tell you about relying on signature/readiness scanning alone?
2. A clean `llm` report — does it prove the server is safe? What would you still verify?
3. Your *own* server (Module 4) — predict what a scan would find. Would `readiness` flag anything? (Stretch: scan it and see.)

## Verify

**Success Criteria**

- A baseline scan report exists
- The report names every planted issue in the deliberately vulnerable server
- You can name one finding you would fix first, and why

**Done when:** you have `stage1-report.txt` and `stage2-llm-report.txt`, the LLM pass named all five planted issues (secret, timeout, poisoning, shell tool, injection), and you can justify a fix-first choice.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `curl: (60) SSL ... not yet valid` | machine clock wrong | `sudo timedatectl set-ntp true`, confirm `date` |
| `mcp-scanner not found` in `doctor` | Python 3.10 used at install | redo Step 1, then `defenseclaw uninstall --all --binaries --yes` and reinstall |
| crash right after a `setup` command | gateway not running | `defenseclaw-gateway start`, rerun |
| `llm_analyzer: SAFE` but `AuthenticationError` above it | LLM call failed silently (fell back to OpenAI) | set all three `MCP_SCANNER_LLM_*` vars; rerun |
| `UnboundLocalError` with `--llm-api-key` | known broken flag | use the `MCP_SCANNER_LLM_API_KEY` env var, not the flag |
| `Behavioral analyzer requires --source-path` | `behavioral` can't scan a live URL | run it separately with `--source-path <dir>` |
| red `✗` OpenClaw lines in `doctor` | expected, unrelated to scanning | ignore |

## Quick Reference

```bash
# baseline (no key):
~/.defenseclaw/.venv/bin/mcp-scanner --analyzers yara,readiness \
  --format detailed remote --server-url http://localhost:8766/mcp | tee stage1-report.txt
# LLM-enhanced (all three vars required):
export MCP_SCANNER_LLM_API_KEY=... MCP_SCANNER_LLM_MODEL="openrouter/anthropic/claude-sonnet-4.5" MCP_SCANNER_LLM_BASE_URL="https://openrouter.ai/api/v1"
~/.defenseclaw/.venv/bin/mcp-scanner --analyzers yara,readiness,llm \
  --format detailed remote --server-url http://localhost:8766/mcp | tee stage2-llm-report.txt
```

- `yara` = secrets/signatures · `readiness` = timeouts/error-handling · `llm` = poisoning/injection.
- The agent-facing attacks are **only** visible to the `llm` pass.
- A clean report is **evidence, not proof**. Full verified guide: `expansion/mcp-server-security.md`.

---

**Source material:** `expansion/mcp-server-security.md` (runnable as-is; includes the 3.10→3.12 `uv` workaround)
