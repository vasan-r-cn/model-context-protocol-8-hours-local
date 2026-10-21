# MCP Workshop — 4-Hour End-to-End Flow

**Audience:** network/infra engineers; no MCP experience assumed, basic CLI comfort required.
**Format:** instructor-led, individual lab pods (LibreChat + MCP server host + Router1 per pod or shared per lab design).
**Design target:** ≈60% hands-on / 40% lecture (inverts the current material's ratio).
**Two-client strategy (load-bearing):** LibreChat demonstrates the *product* experience — tools, auth, chat-driven operations. MCP Inspector demonstrates the *protocol* — wire traffic, resources, prompts, notifications, elicitation. LibreChat cannot consume the advanced primitives (verified against the vendored v0.8.7); do not improvise demos of them in LibreChat — they will fail in front of students.

---

## Agenda at a Glance (240 min)

| Time | Dur | Module | Mode | Client |
|---|---|---|---|---|
| 0:00–0:10 | 10 | M0 · Welcome & pre-flight | hands-on | — |
| 0:10–0:50 | 40 | M1 · Concepts lecture | lecture | — |
| 0:50–1:15 | 25 | Lab 1 · Protocol on the wire | hands-on | Inspector |
| 1:15–1:45 | 30 | Lab 2 · LibreChat end-to-end + auth | hands-on | LibreChat |
| 1:45–1:55 | 10 | Break | — | — |
| 1:55–2:40 | 45 | Lab 3 · Build your own tool | hands-on | both |
| 2:40–3:15 | 35 | Lab 4 · Resources & prompts | hands-on | Inspector |
| 3:15–3:45 | 30 | Lab 5 · Notifications & elicitation | hands-on | Inspector |
| 3:45–4:00 | 15 | M6 · Wrap-up & operational takeaways | lecture | — |

Hands-on total: 145 min · Lecture: 55 min · Break: 10 min · Wrap: 15 min. Buffer lives inside each lab's stretch goals, plus the skip ladder (below) absorbs overruns.

**Skip ladder (when behind, cut in this order):**
1. Lab 5 second half (elicitation) → instructor demo instead of student exercise (−10)
2. Lab 4 prompts section → show only (−10)
3. Lab 3 stretch goals (history logging / multi-router) → take-home (−10)
4. M1 LLM-fundamentals slides → 2-minute recap (−10)

**Never cut:** M0 pre-flight, Lab 1, Lab 2, Lab 3 core build — they are the workshop's spine.

---

## M0 · Welcome & Pre-Flight (0:00–0:10)

**Goal:** every student at green before the lecture starts, so lab time is never spent on setup.

- Students execute the pre-flight checklist (rewritten Setup doc): LibreChat login at `127.0.0.1:3080` → `curl http://172.18.1.2:8000/` health check → Inspector (pinned version) connects to `http://172.18.1.2:8000/mcp` (Streamable HTTP + bearer token) → `tools/list` non-empty.
- Instructor projects the canonical topology table; students identify the three subnets.

**Done when:** every student shows the Inspector tool list. Anyone red gets the TA/instructor during M1.

**Instructor notes:** router baseline must be verified *before* the session (reset script — see server plan §6.7). Have 2 spare OpenRouter keys.

## M1 · Concepts Lecture (0:10–0:50)

**Goal:** just enough theory to make every lab observation meaningful. Trimmed deck (corrected per content plan §2.5).

- 0:10–0:20 — Why MCP: LLM → tool use → MxN integration problem → M+N. (LLM-fundamentals slides compressed; this audience needs the integration story, not transformer internals.)
- 0:20–0:35 — The protocol: host/client/server, JSON-RPC 2.0, lifecycle (`initialize` → capability negotiation → operation), transports (Streamable HTTP current, stdio local, HTTP+SSE legacy).
- 0:35–0:48 — The six primitives in one table (tools / resources / prompts / notifications / elicitation / sampling), each with its Cisco-lab example and *which client can consume it* — plant the two-client story now.
- 0:48–0:50 — What we build today: agenda walk-through.

**Instructor notes:** capability negotiation is the single concept that pays off most later (Lab 5's LibreChat-vs-Inspector split) — spend the extra minute on it.

## Lab 1 · Protocol on the Wire (0:50–1:15) — Inspector

**Goal:** demystify the protocol by watching real traffic. Replaces the old EndToEndFlow narrative doc with live observation.

1. Restart the MCP server in a visible terminal (`./run.sh`) — keep logs on screen all day.
2. Inspector: connect → observe `initialize` request/response — find the server's declared capabilities and `instructions` string.
3. `tools/list` — inspect `inputSchema` and annotations (`readOnlyHint` vs `destructiveHint`); why the annotation difference matters on network gear.
4. `tools/call` → `get_interfaces` — watch progress notifications during the SSH round-trip; router output returns.
5. Worksheet: label each observed message as request / response / notification; identify who initiated it.

**Done when:** student produces Router1's interface table via Inspector and can point at the `initialize` handshake in the history pane.
**Stretch:** call `get_router_info`, compare structured output vs plain text result.

## Lab 2 · LibreChat End-to-End + Auth (1:15–1:45) — LibreChat

**Goal:** the product experience — chat drives a router — plus transport-level auth, learned through deliberate failure.

1. Start from a `librechat.yaml` with the bearer token **wrong/absent** (instructor-prepared). LibreChat: MCP server fails → students find the 401 in `docker compose logs api`.
2. Fix the token (`${CISCO_MCP_TOKEN}` in `.env`) → restart → `cisco-router` tools appear in chat.
3. Prompt: *"Show me the router interfaces"* → watch the full chain: chat → tool call in server logs → SSH → answer rendered.
4. Prompt: *"Configure interface GigabitEthernet0/2 with IP 10.0.0.1"* → destructive tool path; note the change lands **without** confirmation here — hold that thought for Lab 5.
5. Trace one exchange end-to-end against the server terminal logs: LibreChat → `/mcp` → Netmiko → Router1 and back.

**Done when:** both prompts succeed and the student can point to the corresponding `tools/call` in the server log.
**Instructor notes:** SSRF `allowedAddresses` is the classic silent failure — if tools never appear and there's no 401, check that first. Verify the chosen OpenRouter model reliably emits tool calls during the dry run, not on workshop day.

## Break (1:45–1:55)

## Lab 3 · Build Your Own Tool (1:55–2:40) — both clients

**Goal:** the core build. Students extend the server with `dynamic_show` (evolved Bonus-guide exercise on the FastMCP codebase).

1. Add `dynamic_show(command: str)` with the FastMCP decorator — docstring *is* the tool description; discuss description-as-prompt-engineering.
2. Guardrail: exact-command allowlist; reject `|` and `>`; `show running-config` deliberately excluded. Test the bypass that defeats naive `startswith("show")` prefix matching — why prefix checks are not guardrails.
3. Mark it `readOnlyHint: true`; restart; verify in **Inspector** first (`tools/list` → schema → manual call) — establish "Inspector before chat" as the debugging habit.
4. Then **LibreChat**: *"Is OSPF running on the router?"*, *"Show the routing table"* — the LLM chooses the command; whitelist rejects an invalid one; watch the model read the error and retry (errors returned as tool results, not exceptions — this loop is why).

**Done when:** an OSPF/routing-table question answered in LibreChat through the student's own tool, and the blocked-command test rejected cleanly.
**Stretch (take-home if time is short):** command-history logging; multi-router support (`ROUTERS` dict + enum param, Router2 `172.18.2.7`).

## Lab 4 · Resources & Prompts (2:40–3:15) — Inspector

**Goal:** the primitives beyond tools; who controls what (model-controlled tools vs application-controlled resources vs user-controlled prompts).

1. Resources tab: read `router://interfaces`, `router://running-config`; resource *template* `router://interfaces/{name}` with a parameter.
2. Discussion beat: why running-config as a **resource** rather than a tool — the client/user decides to load context; the model decides to act.
3. Prompts tab: render `troubleshoot_interface("GigabitEthernet0/1")`; inspect the message structure it returns.
4. **Reality check (2 min, explicit):** flip to LibreChat — no resources, no MCP prompts. Dead code in the client; capability tables in the wrap-up show what production clients do and don't implement. The one LibreChat-visible crossover: embedded resources inside tool results.

**Done when:** student reads a templated resource with a parameter and renders one prompt in Inspector.
**Instructor notes:** name the collision — LibreChat's "Prompts" UI feature is its own local library, unrelated to MCP prompts.

## Lab 5 · Notifications & Elicitation (3:15–3:45) — Inspector

**Goal:** the dynamic protocol — servers that change at runtime and ask before acting.

1. Call `enable_config_tools` toggle → `notifications/tools/list_changed` arrives → tool list updates live. Operational framing: destructive capability off by default, explicitly enabled.
2. Subscribe to `router://running-config` → run `create_loopback` → `notifications/resources/updated` arrives.
3. Elicitation: call `configure_interface` in Inspector → confirmation dialog (schema-driven accept/decline/cancel) → **Decline** → change aborted. Recall Lab 2, where the same tool wrote config with no gate.
4. Same call in LibreChat → completes with the "client does not support elicitation — applied without confirmation" warning. Capability negotiation, observed end-to-end.
5. Spec rule (say it out loud): elicitation must never collect secrets or credentials.

**Done when:** student has declined one config change via elicitation and seen both notification types arrive.
**Skip variant:** steps 3–4 as instructor demo (−10 min).

## M6 · Wrap-Up & Operational Takeaways (3:45–4:00)

- Recap against the client-capability matrix (server plan §4): what LibreChat consumed vs Inspector — what "MCP support" actually means varies by client; check capabilities before designing a server.
- Operational safety recap: read-only vs destructive annotations, allowlist over prefix match, confirmation gates, pre-change snapshots, reset-to-baseline. An AI agent touching production network config deserves validation gates before, not apologies after.
- Sampling in two minutes (lecture-only: no lab client supports it) + pointers: MCP Registry, spec 2025-11-25 additions, OAuth 2.1 bonus doc.
- Take-home: **Bonus Assignment — Prompts & Resources with a real client** (`content/v2/participants/Bonus_Assignment_Prompts_Resources.docx`: register the server in Claude Code/Codex CLI, run MCP prompts as slash commands, pull resources via @-mentions, submit a short write-up); plus Lab 3 stretch goals, Bonus guide advanced exercises, hardcoded-credentials fix.
- Troubleshooting clinic with remaining minutes: fix stragglers' pods live using the troubleshooting matrix.

---

## Instructor Pre-Flight (before students arrive)

1. Run the lab reset script; verify Router1 matches baseline (`snapshot_config` diff clean).
2. `./run.sh` on the server host; `curl` health check; smoke script (raw JSON-RPC with bearer token) passes.
3. LibreChat containers up; OpenRouter key valid and funded; chosen model verified to emit tool calls.
4. Prepare the broken-token `librechat.yaml` for Lab 2's deliberate failure.
5. Inspector pinned version cached (`npx @modelcontextprotocol/inspector@<pinned>` pre-fetched — venue bandwidth is never trustworthy).
6. Project the topology table; print or link the troubleshooting matrix.

## Module → Material Map

| Module | Supporting document (`content/v2/participants/` unless noted; instructor docs in `content/v2/instructor/`) |
|---|---|
| M0 | `01_Setup_PreFlight` |
| M1 | `content/v2/MCP_Essentials_Deck_v2.pptx` (corrected deck; `06_Deck_Corrections_Memo` documents the fixes vs the original PDF) |
| Lab 1 | `03_Lab1_WireTrace` worksheet |
| Lab 2 | `02_Student_Guide` §4 (yaml + UI connector + auth) |
| Lab 3 | `04_Lab3_Build_Guide` + `Server_Code_Walkthrough` §4–5 |
| Labs 4–5 | `02_Student_Guide` §6 + `05_Instructor_Guide` §3 scripts |
| M6 | capability matrix (`02_Student_Guide` §6) + take-home `Bonus_Assignment_Prompts_Resources` |
| Instructor | `05_Instructor_Guide` (pre-flight, answer keys, incident runbook, reset) |

## Assumptions to Verify Before First Delivery

- Router2 (`172.18.2.7`) exists and is reachable — referenced only by a bonus exercise; confirm or drop.
- Pod count vs shared router: concurrent `send_config_set` from many students against one Router1 will collide. Either per-pod routers, or Lab 2/5 config steps run on instructor demo + students use distinct interface/loopback number ranges (assign per seat).
- Venue machines can reach OpenRouter (egress) and run `npx`.
