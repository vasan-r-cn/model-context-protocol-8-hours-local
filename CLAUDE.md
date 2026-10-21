# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

Teaching material for a one-day MCP (Model Context Protocol) workshop. Students run a Python MCP server that exposes Cisco router operations as MCP tools, and connect to it from LibreChat as the MCP client. This is workshop/lab code — clarity for students matters more than production hardening, and the hardcoded lab credentials/IPs (router `172.18.2.6`, admin/admin) are intentional.

## Layout

- `code/server/` — the MCP server students build and run (the core workshop artifact)
  - `app/main.py` — FastMCP (official SDK) server over Streamable HTTP at `/mcp`, mounted in a FastAPI app (health check at `GET /`). Bearer-token auth guards `/mcp` (`MCP_AUTH_TOKEN`, default `cisco-mcp-workshop`). 7 tools (read-only ones annotated `readOnlyHint`, config-writing ones `destructiveHint` and toggleable via `enable_config_tools` → `tools/list_changed`), 3 resources + 1 template (`router://…`), 2 prompts, resource subscriptions, and an elicitation confirm-gate that degrades gracefully for clients without the capability (LibreChat). Router access via Netmiko SSH in worker threads; errors returned as tool results, never raised.
  - `run.sh` — self-bootstrapping: creates `.venv/` + installs requirements on first run, sources `.env` if present, starts `uvicorn app.main:app` on `$HOST:$PORT` (default 0.0.0.0:8000)
  - `smoke_test.sh` — instructor pre-flight: raw JSON-RPC curl checks (health, 401, initialize, tools/list)
  - `reset_lab.py` — removes `MCP_CREATED` loopbacks between cohorts (dry-run by default, `--apply` to execute)
  - `librechat.reference.yaml` — mcpServers/mcpSettings blocks to merge into the LibreChat host config (incl. the SSRF `allowedAddresses` requirement)
  - `requirements.txt`, `.env.example` — pinned deps and env overrides (lab defaults built in)
- `code/client/LibreChat/` — full vendored LibreChat monorepo used as the MCP client. It has its own `CLAUDE.md` with detailed workspace boundaries, code style, and commands — follow that file for any work inside LibreChat.
- `content/` — original student-facing workshop docs (.docx/.pdf), kept for reference; superseded by `content/v2/`.
- `content/v2/participants/` — student doc set: `00_EndToEnd_Flow` (comprehensive end-to-end guide — full original-guide structure: environment, code, config, data flow, troubleshooting, glossary), `01_Setup_PreFlight`, `02_Student_Guide`, `03_Lab1_WireTrace`, `04_Lab3_Build_Guide`, `Server_Code_Walkthrough`, `Bonus_Assignment_Prompts_Resources`.
- `content/v2/instructor/` — `05_Instructor_Guide` (pacing, answer keys, incident runbook, reset), `06_Deck_Corrections_Memo`, `07_Participant_QA` (anticipated participant questions with lab-grounded answers). Do not hand these to students.
- `content/v2/MCP_Essentials_Deck_v2.pptx` — the corrected M1 lecture deck (31 slides, replaces the watermarked PDF); regenerate with `python3 scripts/build_deck.py` (needs python-pptx) — the script is the source of truth.
- Every v2 `.docx` is generated from its same-named `.md` — **edit the .md, it is the source of truth**, then regenerate: `python3 scripts/md2docx.py <name>.md <name>.docx` (needs python-docx). Screenshot placeholders appear as `[SCREENSHOT n: description]` lines — images pasted manually into the .docx.
- `docs/` — maintainer planning docs: content improvement plan, MCP server improvement plan (FastMCP/auth/resources/prompts/notifications/elicitation), and the 4-hour workshop run-of-show.

## Running

MCP server (from `code/server/`):
```bash
./run.sh
```
First run auto-creates `.venv/` and installs `requirements.txt` (prefers python3.11, falls back to python3). Override bind with `HOST`/`PORT` env vars if :8000 is taken. Health check at `GET /`; MCP endpoint at `/mcp` (Streamable HTTP, `Authorization: Bearer cisco-mcp-workshop` unless overridden in `.env`).

Quick verify: `./smoke_test.sh` (server must be running). Inspect/test without LibreChat: `npx @modelcontextprotocol/inspector`, open the token URL it prints, connect via Streamable HTTP to `http://<server>:8000/mcp` with the bearer token header.

LibreChat client: see `code/client/LibreChat/CLAUDE.md` (backend on :3080, frontend dev on :3090).

## End-to-End Flow (what the workshop demonstrates)

LibreChat UI (:3080) → LibreChat API connects to the MCP server via Streamable HTTP (:8000/mcp, bearer token) → `tools/list` results are passed to the LLM → it emits a tool call → server executes the tool over SSH (Netmiko) against Router1 (`172.18.2.6`) → result streams back → final answer rendered in LibreChat. Resources, prompts, notifications, and elicitation are demoed via MCP Inspector — the vendored LibreChat build does not consume them (verified; see `docs/mcp-server-improvement-plan.md` §4 client compatibility matrix).

## Notes for Changes

- Tools/resources/prompts are FastMCP decorators in `main.py` — the schema comes from the function signature + docstring (docstring = tool description the LLM sees; write it deliberately).
- Netmiko is blocking: route all router I/O through the `run_show`/`run_config` helpers (worker threads). Return errors as text, never raise — the LLM reads the error and retries.
- New config-writing tools: register via `_CONFIG_TOOLS` (keeps the enable/disable toggle honest), annotate `destructiveHint`, gate with `_confirm_change`, and call `_notify_config_changed()` after the change.
- `dynamic_show` uses an exact-command allowlist on purpose — do not "simplify" it to prefix matching (that reintroduces `show run | redirect …` bypasses).
- The `create_initialization_options` wrapper near the bottom of `main.py` exists because the SDK hardcodes `resources.subscribe=false` — keep it when upgrading the `mcp` package, or verify it's no longer needed.
- Verification: `./smoke_test.sh` for the wire-level basics; there is no test suite or linter for the server code. LibreChat has its own (Jest per-workspace, ESLint — see its CLAUDE.md).
