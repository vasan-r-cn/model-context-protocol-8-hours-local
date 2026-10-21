# Instructor Guide — MCP Workshop (4 hours)

Internal document. Run-of-show source of truth is `docs/workshop-flow-4h.md`; this guide adds the operational layer: pre-flight, answer keys, pacing calls, known failure modes with fixes, and reset.

---

## 1. T-minus-1-day checklist

- [ ] Router1 (`172.18.2.6`) and Router2 (`172.18.2.10`) reachable from `linuxdesktop4`; credentials admin/admin/enable admin work
- [ ] Router baseline clean: `cd ~/cisco_mcp && python3 reset_lab.py` reports "router is clean" (run with `--apply` if not)
- [ ] Server starts: `./run.sh` → smoke test `13 passed, 0 failed`
- [ ] `.venv` pre-built on lab image (first-run pip install needs internet/minutes — don't spend session time on it)
- [ ] Node 22 on `linuxdesktop4` (`node --version`) — Inspector 2.x hard-requires ≥22.19; Node 20 fails with `EBADENGINE`/undici errors
- [ ] Inspector pre-cached: run `npx @modelcontextprotocol/inspector@2.0.0` once on the image (venue bandwidth is never trustworthy)
- [ ] LibreChat: five containers up; `librechat.yaml` matches Student Guide §4.1 exactly (streamable-http, bearer header, `mcpSettings.allowedAddresses`, `fetch: false`)
- [ ] `.env` on desktop3 has `OPENROUTER_KEY` (funded!), `CISCO_MCP_TOKEN`, `UID`, `GID`
- [ ] OpenRouter model check: curl `anthropic/claude-haiku-4.5` with the lab key → completion returned. Also verify in a LibreChat chat that it *calls a tool* when asked for interfaces
- [ ] Prepare Lab 2's broken state (see §3, Lab 2)
- [ ] Projector-ready: topology diagram, capability matrix (Student Guide §6), this guide

## 2. Timing and the skip ladder

Full agenda in `docs/workshop-flow-4h.md`. Hard rules:

- M0 pre-flight (10 min) and Lab 1 (25) protect everything downstream — never compress them.
- Clock checkpoints: Lab 2 must start by **1:15**, Lab 3 by **2:00** (post-break), Lab 4 by **3:00**. Miss one → apply the skip ladder immediately, don't "catch up by talking faster":
  1. Lab 5 elicitation → instructor demo (−10)
  2. Lab 4 prompts → show only (−10)
  3. Lab 3 advanced exercises → take-home (−10)
  4. M1 LLM-fundamentals slides → 2-min recap (−10)

## 3. Per-lab instructor notes & answer keys

### Lab 1 — Wire trace (worksheet `03_Lab1_WireTrace`)

Answers: **A1** Inspector declares sampling/elicitation/roots capabilities (contrast with LibreChat's `{}` — plant this now, harvest in Lab 5). **A2** `tools.listChanged: true`, `resources.subscribe: true`, prompts present. **A4** no `id` → notification. **B1** 7 tools; `configure_interface`, `create_loopback` destructive. **B3** request (has `id`, got a response). **C1** order: tools/call → progress → SSH in terminal → (router output) → result with same id. **C3** successful tool result describing rejection — so the *model* can read it and retry (protocol errors are invisible to the model). **D1** request/client · notification/client · request+response/client-then-server. **D2** server learned client capabilities during `initialize`.

Common stall: students connect Inspector *before* opening History and miss the handshake → reconnect, it replays.

### Lab 2 — LibreChat end-to-end + auth

**Prepared broken state (choose ONE, do it before session):**
- Option A (recommended): comment out `CISCO_MCP_TOKEN` in desktop3's `.env` + force-recreate. Symptom students hunt: api log `OAuth Required: true … 0 tools`; server terminal: `401 … no Authorization header sent`. Fix: restore var, `docker compose up -d --force-recreate api` — teaches the recreate-vs-restart rule.
- Option B: remove the `mcpSettings` block. Symptom: `Domain "http://172.18.1.2:8000" is not allowed` reinspection loop. Fix: restore + `restart api`.

Part B (UI connector): students each create a per-user connector (Student Guide §4.3). Deliberately have them try Authentication = "None (Auto-detect)" first → watch it fail → switch to API Key. That 401→OAuth-hunt behavior is the same one from Option A, now self-inflicted and understood.

Answer to "why can't I use localhost in the URL": three subnets — show the topology.

### Lab 3 — Build a tool (guide `04_Lab3_Build_Guide`)

- Complete reference implementation of `ping_from_router` is in the guide itself; your answer key is: checkpoint 2 = tool + schema + both accept/reject behaviors in Inspector; checkpoint 3 = model calls it from chat.
- **Shared-router collision management:** read-only lab, low risk; but assign each student a distinct loopback range (seat number × 10) for any config exercises, and stagger LibreChat reinitializes.
- If a student's server won't start: traceback is in their terminal; 90% it's indentation or a missing comma in the decorator.
- "Model won't call my tool": docstring too vague — have them read it aloud; if it doesn't say *when to use it*, the model can't know.

### Lab 4 — Resources & prompts (Inspector)

Script: resources list → read `router://interfaces` → template with `GigabitEthernet0/1` → run `snapshot_config` → read `router://baseline`. Prompts tab → `troubleshoot_interface`. Then the 2-minute reality check: flip to LibreChat, show there is no resources/prompts UI for MCP, and put the capability matrix on screen. Name the trap: LibreChat's "Prompts" feature ≠ MCP prompts.

Discussion answer (why running-config is a resource but not an allowed command): the model must not pull the full config on its own initiative (credential exposure); a human deliberately loading it as context is a different trust decision, and both sit behind the bearer token.

### Lab 5 — Notifications & elicitation (Inspector)

Script: `enable_config_tools false` → watch `tools/list_changed` + list shrink to 5 → re-enable. Subscribe to `router://running-config` → `create_loopback <seat range>` → `notifications/resources/updated` arrives. Then elicitation: `configure_interface` → dialog → **Decline** first (result: "Change cancelled by user.") → then Accept. Finally the punchline: same tool from LibreChat applies immediately with the degradation warning. Quote the spec rule: elicitation never collects secrets.

### M6 wrap

Put up the capability matrix; walk the safety recap (annotations → allowlist → confirmation gate → snapshots → reset); hand out the take-home (`Bonus_Assignment_Prompts_Resources` — decide and announce whether attendees get lab access post-session or run their own server locally; `run.sh` self-bootstraps from a clone).

## 4. Live incident runbook (field-tested — every entry below actually happened)

| Symptom | Root cause | Fix |
|---|---|---|
| `./run.sh` → `No module named uvicorn` | wrong interpreter had the deps | current run.sh bootstraps `.venv` automatically; if hand-run, use `.venv/bin/python` |
| `run.sh` → `address already in use` | something else on :8000 | `PORT=8123 ./run.sh`, update client URLs |
| Inspector `npx …@latest` → `EBADENGINE`, undici errors | Node 20 vs Inspector 2.x needing ≥22.19 | lab image has Node 22; else `nvm install 22`; pin `@2.0.0` |
| Inspector connects but 401 | token field entered with `Bearer ` prefix | server terminal prints this exact reason; re-enter token only |
| Old cached Inspector ignores auth field | stale npx cache | `rm -rf ~/.npm/_npx`, rerun pinned version |
| LibreChat log `Domain … is not allowed` | SSRF guard | `mcpSettings.allowedAddresses: ["172.18.1.2:8000"]`, restart api |
| LibreChat `OAuth Required: true`, `Tools: undefined`, `0 tools` | 401 during inspection → OAuth auto-detect; token env empty | set `CISCO_MCP_TOKEN`, **force-recreate** api (restart is not enough) |
| Chat: `404 No endpoints available … data policy` | conversation pinned to delisted/blocked model | select `anthropic/claude-haiku-4.5`; keep `fetch: false` |
| `docker compose` permission denied | user not in docker group | `sudo`, or `usermod -aG docker ubuntu` + relogin |
| UID/GID warnings on compose | vars unset | `UID=1000`, `GID=1000` in `.env` |
| Compose v1/v2 mixed stacks | container naming differs (`_` vs `-`) | `docker-compose down` with v1 once, then v2 only |
| Model chats but never calls tools | MCP server not toggled in this conversation | MCP menu → enable; new chat |

Debugging axiom to repeat all day: **server terminal first, api logs second, browser last.** The server's 401 log names the exact auth mistake; LibreChat's log names the exact config gate.

## 5. Reset between cohorts

```bash
# on linuxdesktop4
cd ~/cisco_mcp
python3 reset_lab.py            # dry run — lists MCP_CREATED loopbacks
python3 reset_lab.py --apply    # removes them + saves config
./smoke_test.sh                 # 13 passed
rm -rf snapshots/               # optional: clear students' snapshots
```

Interface IPs changed via `configure_interface` are NOT auto-reverted — diff the latest snapshot in `snapshots/` against `show running-config` and restore by hand (or keep a golden config on the router and `configure replace`). On desktop3: no reset needed; optionally delete student conversations via the UI.

## 6. Assets inventory

| Asset | Location |
|---|---|
| Server code / smoke test / reset | `code/server/` |
| Reference client config | `code/server/librechat.reference.yaml` |
| Student docs v2 | `content/v2/participants/` |
| Instructor docs (this file + deck memo) | `content/v2/instructor/` |
| Run-of-show | `docs/workshop-flow-4h.md` |
| Capability matrix (canonical) | `docs/mcp-server-improvement-plan.md` §4 |
| Deck + corrections memo | `content/PDFModel_Context_Protocol_WaterMarked.pdf` + `content/v2/instructor/06_Deck_Corrections_Memo` |
