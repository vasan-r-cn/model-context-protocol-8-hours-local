# MCP Workshop — 4h → 8h Expansion Plan (v2, new topology)

> **SUPERSEDED** by `content/v3/00_Catalog.md` (6 Oct 2026). The day is now
> published as 8 sandbox categories / 28 exercises with an LLM + agent on-ramp,
> not the 5-lab agenda below. Splunk and the DC/DR safety model carry over;
> the Kubernetes MCP lab is dropped (no cluster in the topology) and the
> 5-lab agenda, build timeline and `content/v3` doc list below are history.
> Kept for its lab deltas, device rationale and open items.

**Status:** plan, approved for build. Supersedes `docs/workshop-flow-8h.md` (v1 design, LibreChat + two-router lab, never built).
**Written:** 30 Sep 2026. **Freeze target:** Fri 16 Oct 2026.

---

## Context

The delivered workshop is a 4-hour beginner track: a FastMCP server exposing 7 Cisco IOS tools (`code/server/app/main.py`) against two routers, driven from LibreChat, with MCP Inspector covering everything LibreChat cannot consume. A prior 8-hour design exists (`docs/workshop-flow-8h.md`) but was never built and still assumes LibreChat and the two-router lab.

Four things now change that design:

1. **The lab topology is replaced.** The `172.18.2.6 / .10` two-router lab is gone. The new environment is a production-shaped NetDevOps topology: **DC** and **DR** sites (Nexus pairs + SD-WAN edge), **SD-WAN controllers** (vManage / vBond / vSmart), **MPLS** and **public-internet** transports, **Site-10** and **Site-20** branch edges with participant Linux desktops, and a **legacy site** on an autonomous c8000v. Every IP, device name, credential and reset path in the existing content is invalidated. Reference: `expansion/new-topo.png`.
2. **LibreChat is retired as the harness.** Its MCP support is tools-only (verified against the vendored v0.8.7), which forces half the protocol into Inspector-only demos. Replaced by **fast-agent** (`fast-agent-mcp`, Apache-2.0) — the only framework with end-to-end tested tools + resources + prompts + elicitation + sampling + roots, over Streamable HTTP with bearer auth.
3. **A vendor-published Cisco MCP server joins the day.** **[Splunk MCP Server](https://github.com/CiscoDevNet/Splunk-MCP-Server-official)** (CiscoDevNet, Splunkbase app 7931, v1.0.1, Splunk-supported beta). It is **not** a repo you clone and run: it installs *into* a Splunk Enterprise/Cloud instance (8.0–10.2) and is served on the Splunk management port at `https://<splunk>:8089/services/mcp`, bearer-token authenticated, with RBAC in `authorize.conf`. Note it is **tools-only — no resources, no prompts**, and it ships under Splunk General Terms rather than an OSS licence. That is the point: it is the "you do not write every server, and you do not control the ones you do not write" lesson from `meet-notes.md`.
4. **Multi-agent orchestration and security become hands-on.** The LangGraph hub-and-spoke app (planner + SD-WAN / ThousandEyes / ServiceNow specialists) already exists at `Workshop/building-ai-agents-and-workflow-orchestration/agentic-ai-workshop/multi_agent_v2` and is vendored in, not rebuilt. The DefenseClaw exercise in `expansion/mcp-server-security.md` becomes the control lab.

Customer-facing structure follows `expansion/MCP_Workshop_1_Day_Outline-v1_0.docx` (6 modules, 5 labs). The 4-hour track and `content/v2/` are frozen as-is and will no longer run — the old topology is gone.

**Outcome:** a lab-driven 8-hour day, ~58% hands-on, arc = protocol → build a server → consume someone else's → control it → orchestrate it, ending in a multi-agent troubleshooting capstone with a human-approved remediation validated on DR before it touches DC.

---

## Decisions (locked)

| Decision | Choice |
|---|---|
| Production / production-representative | **DC = production. DR = production-representative.** Config writes land on DR first, then promote to the DC mirror |
| Protocol harness | **fast-agent** — Labs 1–4. LibreChat retired from the student path |
| Orchestration harness | **LangGraph + Gradio** (`multi_agent_v2`, vendored) — Lab 5 only. MCP is one layer inside it |
| External Cisco MCP | **Splunk MCP Server** (CiscoDevNet, official), one shared Splunk instance, read-only |
| Security lab | **DefenseClaw** from `expansion/mcp-server-security.md` |
| Demos / take-home only | SD-WAN MCP server (`expansion/sdwam-mcp.md`), deployment + LangSmith (`expansion/ai-workflow-deploymeny.md`), k8s agent (`expansion/k8s-mcp-erver.md`) |
| LLM provider | OpenRouter — fast-agent's native `openrouter` provider; the multi-agent app already uses OpenRouter |
| Time | **8 hours, hard cap.** Anything below the line ships as documented take-home, not as an overrun |
| Build window | Wed 30 Sep → Fri 16 Oct 2026, dry run Thu 15 Oct |

**Cut from the v1 plan and from `docs/workshop-flow-8h.md`:**

- The 90-minute "build your own MCP client" lab → take-home (`Takehome_Build_Your_Client`). fast-agent and the LangGraph app both show the host loop; writing a third one does not earn 90 minutes.
- Sampling (`explain_interface_state`) → take-home. Least operationally relevant primitive for this audience.
- The three-client capability matrix becomes four columns but is discussed, not exercised.

---

## Agenda (480 min)

| Time | Dur | Block | Mode | Client |
|---|---|---|---|---|
| 0:00–0:10 | 10 | M0 · Pre-flight | hands-on | fast-agent, Inspector |
| 0:10–0:40 | 30 | M1 · Automation → agentic netops; why MCP; MCP vs A2A | lecture | — |
| 0:40–1:05 | 25 | M2 · The protocol: JSON-RPC, lifecycle, primitives, transports | lecture | — |
| 1:05–1:45 | 40 | **Lab 1** · Protocol on the wire + first agent | hands-on | Inspector, curl, fast-agent |
| 1:45–1:55 | 10 | Break | — | — |
| 1:55–2:45 | 50 | **Lab 2** · Design and build self-describing tools | hands-on | Inspector, fast-agent, pytest |
| 2:45–3:10 | 25 | M3 · MCP for Cisco network operations + trust boundaries | lecture | — |
| 3:10–3:55 | 45 | Lunch | — | — |
| 3:55–4:50 | 55 | **Lab 3** · Add a vendor MCP server — two servers, one agent | hands-on | fast-agent, Inspector |
| 4:50–5:00 | 10 | Break | — | — |
| 5:00–5:20 | 20 | M4 · Safety, identity and control | lecture | — |
| 5:20–6:10 | 50 | **Lab 4** · Roles, elicitation gate, injection, DefenseClaw | hands-on | fast-agent, DefenseClaw |
| 6:10–6:30 | 20 | M5 · Multi-agent orchestration — where MCP sits | lecture | — |
| 6:30–7:45 | 75 | **Lab 5** · Capstone — orchestrated diagnosis + validated change | hands-on | LangGraph/Gradio, fast-agent |
| 7:45–8:00 | 15 | M6 · Wrap-up, hardening + deployment roadmap, clinic | lecture | — |

Hands-on 280 min (58%) · lecture 135 · breaks/lunch 65.

**Clock checkpoints — apply the skip ladder the moment one is missed:** Lab 1 done 1:45 · Lab 2 done 2:45 · lunch starts 3:10 · Lab 3 done 4:50 · Lab 4 done 6:10 · Lab 5 starts 6:30.

**Skip ladder (cut in this order):**

1. Lab 4 D DefenseClaw scan of *own* server → take-home; keep the vulnerable-server scan (−10)
2. Lab 3 C resource template → instructor demo (−10)
3. Lab 2 pytest section → take-home (−12)
4. Lab 1 B raw curl session → dissect `smoke_test.sh` instead (−12)
5. Lab 5 D gated promote → instructor drives it on the projector, students watch (−15)
6. Lab 5 B (wire own MCP server into a specialist agent) → pre-wired in the supplied code (−15)

**Never cut:** M0 · Lab 1 A · Lab 2 build · Lab 3 B two-server agent · Lab 4 A+B roles and elicitation gate · Lab 5 A+C orchestration and diagnosis.

---

## Topology Roles

**Full device-by-device breakdown: [`docs/lab-device-map.md`](lab-device-map.md)** —
per-site roles, which device each lab uses, seat scoping, and the facts still to
be confirmed against the sandbox. Summary:

| Role | Devices | Students may |
|---|---|---|
| **Production** | DC — `sdceightkv11` (edge), `cisconexusnkv12/13/14`, `linuxdesktop19/20` | read only; `sdceightkv11` receives the promoted change in Lab 5 D |
| **Production-representative** | DR — `sdceightkv24` (edge, **`default_device`**), `cisconexusnkv30/41/52` | read; **all validation writes land here** |
| **Branch** | Site-10 `sdceightkv62` + `linuxdesktop64`, Site-20 `sdceightkv63` + `linuxdesktop65` | read; the desktops are the participant workstations |
| **Legacy** | `ciscoeightkv73` (autonomous c8000v) + `linuxdesktop74` | read; the "not everything is SD-WAN" beat in M3, and the fallback write target |
| **Control plane** | `ciscovmanage3` / `ciscovbond4` / `ciscovsmart5` | read via the SD-WAN specialist agent; no template edits |
| **Transports** | `public-internet6`, `mpls55` | the two paths the capstone fault moves between |

**Every participant gets their own complete copy of this topology.** No seat
scoping, no per-seat ports, no shared-device contention — every lab command is
identical for everyone, and a student's mistakes are confined to their own pod.
The `role` guard rails therefore teach operational discipline rather than
protect other students; say that out loud in Lab 4.

Device names, management addresses and per-platform credentials are **generated
from `code/server/custom-underlay.yaml`** into `code/server/inventory.yaml`.
Still to confirm: whether the participant desktops can reach `192.168.116.0/24`,
whether DR accepts student config writes, the vManage API account, and the
seat → desktop map.

## Lab Deltas

### Lab 1 · Protocol on the Wire + First Agent (40)

- **A (18):** Inspector → `initialize` capabilities + `instructions` → `tools/list` annotations → `tools/call get_interfaces` against a DR device, with progress notifications. Then the same thing through `fast-agent go`: same server, same tools, a model choosing them. Worksheet: label request / response / notification.
- **B (12):** Raw session by hand with `curl` — obtain `Mcp-Session-Id`, send `notifications/initialized`, open the SSE stream in a second terminal, trigger `tools/list_changed`, `DELETE` the session. Map each step to a line in `code/server/smoke_test.sh`.
- **C (10):** fast-agent `/mcp`, `/tools`, `/prompts`, `/resources` — the client's own view of the same six primitives.
- **Done when:** the student has a session ID they obtained by hand, and one prompt answered through fast-agent.

### Lab 2 · Design and Build Self-Describing Tools (50)

- Build `ping_from_device(target, device=...)` against the new inventory, extending `content/v2/participants/04_Lab3_Build_Guide.md`. Docstring-as-description; `readOnlyHint`; Inspector-before-chat habit.
- Design beat: tool granularity (operator intent vs API endpoint), error semantics, and why NX-OS and IOS-XE output shapes force a decision about parsing.
- `code/server/tests/test_tools.py` — SDK in-memory transport, `run_show` monkeypatched, two student-written tests, `pytest -q` green with no device reachable.
- **Done when:** the new tool answers a DC↔DR reachability question from fast-agent, and pytest is green.

### Lab 3 · Add a Vendor MCP Server (55) — NEW

The server students did not write, cannot change, and must still reason about.

- **A (12):** Point Inspector at the Splunk MCP Server on `cclorchestrator78`
  (`https://cclorchestrator78:8089/services/mcp`, bearer token). Read its `tools/list`.
  Note what is **missing**: no resources, no prompts. Most servers in the wild
  are tools-only — the richness students built in Lab 4 is a choice, not a given.
- **B (18) — tool design, argued from two real examples.** Their server exposes
  ~8 narrow tools (`get_interfaces`, `dynamic_show` with an exact allowlist).
  Splunk exposes `splunk_run_query`, which takes **arbitrary SPL**. One tool,
  unbounded power. Which is easier for a model to use? Which is safer? Which
  would you put behind RBAC? This is `dynamic_show`'s allowlist lesson told from
  the other side, and it sets up Lab 4's scan.
- **C (15):** Add Splunk as a second server in `fastagent.config.yaml` next to
  their own. Ask one question that needs both — device state from their server,
  log evidence from Splunk. Observe namespacing and how the model chooses
  between servers that answer about **different domains**, not the same one.
- **D (10):** Read the RBAC model: `authorize.conf`, `mcp_tool_execute`, token
  scoping. Compare with the role map they built on their own server. A vendor
  server enforces authorization the same way — the boundary is the lesson.
- **Done when:** one fast-agent session answers a question using tools from both
  servers, and the student can say which server answered which part and why.

> **Changed from pyATS_MCP.** pyATS would have given an apples-to-apples contrast
> (two servers describing the *same* device, raw text vs Genie-parsed). Splunk
> instead gives **cross-domain composition**, which is closer to real operations
> and feeds the capstone directly: device state + telemetry evidence. The cost is
> a Splunk instance — see Open Items.

### Lab 4 · Control, Identity and Security Scanning (50) — NEW

- **A (15):** Role-filtered `tools/list` — `MCP_TOKENS` map (admin / readonly). Reconnect fast-agent with the readonly token, count tools. Then call a hidden config tool by name anyway → the server returns an authorization error as a tool result and the device is unchanged. *Hiding is UX; authorization is enforcement.*
- **B (15):** Elicitation confirm gate — `elicitation: mode: forms`; run a config tool against DR, accept once, decline once. First confirm gate of the day inside a chat client rather than Inspector.
- **C (8):** Tool-result injection — the instructor pre-sets an interface description on a DR device carrying an instruction aimed at the agent. Students ask for an interface summary and classify what happened, and which control would have stopped it.
- **D (12):** DefenseClaw Sections 1–2 against the planted vulnerable server: baseline scan, then LLM-enhanced scan. Read the report for tool poisoning, over-broad capability, hardcoded secret, injected prompt template. Stretch: scan your own server and fix one finding.
- **Done when:** a readonly call to a config tool is refused *and* the device is provably unchanged; the DefenseClaw report names the planted issues.

### Lab 5 · Capstone — Orchestrated Diagnosis + Validated Change (75)

Runs on the vendored `multi_agent_v2` LangGraph app (Gradio UI), with fast-agent alongside for the gated change.

- **A (15):** Start the app; walk the graph — planner/router → SD-WAN node / ThousandEyes node / ServiceNow node → shared state → response. Run the routing tests from `expansion/multi-agent-testing.md` §5. Keep the terminal log visible.
- **B (15):** Register the student's **own MCP server** as a tool source for one specialist agent (`MultiServerMCPClient`, `transport: http`). Their Lab 2 tool becomes callable by the orchestrator. This is the lesson: MCP is a layer inside the system, not the system.
- **C (30):** The instructor injects a path fault (Site-10 traffic to the DC application degrades / fails over between MPLS and internet). Students drive the orchestrator: SD-WAN specialist on tunnel and BFD state, ThousandEyes specialist on the end-to-end path, their own MCP server on device state, ServiceNow specialist for the incident. Produce evidence → root cause → recommendation.
- **D (15):** Remediate under control. The orchestrator proposes; the student executes in **fast-agent**, where the gate actually lives: `propose_change` → `validate_change` on **DR** (snapshot → apply → verify → revert, evidence retained) → `promote_change` to **DC**, refused unless validated, elicitation-confirmed → verify → `rollback_change`. Read the audit JSONL: could you reconstruct what happened to production from this file alone?
- **Chaos beat (3 min):** break DR reachability → validation fails → promote refuses → DC untouched. The gate held. With per-pod topologies each student runs this themselves (`scripts/break_dr.sh`) rather than watching the instructor do it.
- **Done when:** a root cause backed by evidence from at least two specialists, and one change promoted to DC carrying DR evidence, then rolled back.

---

## What Gets Built

### 1. Harness — `code/client-fastagent/` (new)

- `fastagent.config.yaml`: `mcp.servers.my_server` (`transport: http`, `url: http://<host>:80<seat>/mcp`, `headers.Authorization: "Bearer ${MCP_AUTH_TOKEN}"`), `mcp.servers.splunk` (`https://cclorchestrator78:8089/services/mcp`, bearer token), `elicitation: mode: forms`, OpenRouter provider block.
- Per-lab variants: `lab1.yaml` (own server), `lab3.yaml` (both servers), `lab4-readonly.yaml` (readonly token), `lab5.yaml` (own server + change workflow).
- `fastagent.secrets.yaml.example`, `requirements.txt`, `README.md` with the command set used all day.

### 2. External server — Splunk MCP Server (install, do not vendor)

Nothing of ours is built here. What we produce is the **access path and the lab
data**:

- `code/splunk/README.md` — what it is, who publishes it, why we did not write
  it; the `cclorchestrator78` endpoint, app 7931, and the `authorize.conf`
  capabilities a workshop role needs.
- `code/splunk/fastagent-splunk.yaml` snippet — `transport`, URL, bearer header,
  and the TLS setting for Splunk's self-signed management port.
- **Lab data**: syslog from the DC/DR/branch devices landing in a Splunk index
  on `cclorchestrator78`, so the capstone has real evidence to correlate. A
  lab-build task, not a student task — and the one most likely to be missing,
  since a Splunk instance can be healthy and empty.
- Read-only workshop role; students get a token that can run queries and nothing
  else.

### 3. Own server — `code/server/` (re-pointed at the new topology)

| Item | Notes |
|---|---|
| `DEVICES` inventory replacing `ROUTERS` | name → host, `device_type` (`cisco_nxos` / `cisco_xe`), role (`production` / `prod-rep` / `branch` / `legacy`) |
| `device` param on every device-touching tool | `Literal[...]` from the inventory; default = a DR device, so a careless call cannot touch DC |
| `run_show` / `run_config` | keep the worker-thread pattern; take `device_type` from the inventory instead of hardcoding |
| `MCP_TOKENS` role map + role in request context | Lab 4 A |
| Role-filtered `list_tools` handler + enforcement inside config tools | returns `isError` as a tool result, never raises |
| Resource template `device://{name}/running-config` | Lab 3 C |
| `app/change_workflow.py` behind `MCP_ENABLE_CHANGE_WORKFLOW=1` | `propose / validate / promote / rollback_change`; validate targets DR, promote targets DC and refuses unless validated; `change://{id}` resource + subscription; `change_request` prompt; config allowlist mirroring the `dynamic_show` exact-match discipline |
| Audit JSONL wrapper around the low-level `call_tool` handler | Lab 5 D |
| `tests/test_tools.py` + `requirements-dev.txt` | in-memory transport, `run_show` monkeypatched |
| `reset_lab.py` rewrite | new inventory; `MCP_CREATED` loopbacks on DR; injected interface description restored; `changes/`, `snapshots/` cleared; audit rotated |
| `smoke_test.sh` extension | readonly tool count; DR + DC reachability |
| `security/vulnerable_server.py` | verbatim from `expansion/mcp-server-security.md`, clearly labelled, never started by `run.sh` |
| `solutions/` per lab | copy-in fallbacks so one stuck student never blocks the room |
| `librechat.reference.yaml` | moved to `deprecated/` |

Reuse, do not reinvent — all in `code/server/app/main.py`: the `run_show` / `run_config` worker-thread helpers, `_confirm_change`, `_CONFIG_TOOLS` registration, `_notify_config_changed()`, and the `create_initialization_options` subscribe wrapper.

### 4. Orchestrator — `code/multi-agent/` (vendored, not authored)

- Copy `multi_agent_v2` from `Workshop/building-ai-agents-and-workflow-orchestration/agentic-ai-workshop/`; pin its `requirements.txt`; strip anything not used on the day.
- **Our additions:** MCP tool-source wiring so a specialist agent consumes the student's own server; `.env.example` for the new topology; the capstone fault-injection and restore scripts; the routing/negative test sheet adapted from `expansion/multi-agent-testing.md`.
- ThousandEyes agent install on the participant desktop follows `multi-agent-testing.md` §1 — **done in the pre-flight image, not on the day**.

### 5. Content — `content/v3/` (new; `content/v2/` frozen)

| Doc | Source |
|---|---|
| `00_EndToEnd_Flow` | fork v2; new topology chapter; fast-agent replaces the LibreChat chapter; trust boundaries; session mechanics |
| `01_Setup_PreFlight` | rewrite: seat → desktop map, own server port, fast-agent install, OpenRouter key, Splunk endpoint + token, two server tokens, multi-agent venv |
| `02_Student_Guide` | rewrite to the 5-lab structure; capability matrix (fast-agent / Inspector / LangGraph app / Claude Code take-home) |
| `03_Lab1_Wire_And_Agent` | extend v2 Lab 1 |
| `04_Lab2_Build_Guide` | extend v2 Lab 3 guide + pytest |
| `05_Lab3_External_Server_Guide` | **new** |
| `06_Lab4_Control_And_Security` | **new** — role worksheet, injection worksheet, DefenseClaw run sheet |
| `07_Lab5_Capstone_Guide` | **new** — graph walkthrough, MCP wiring, fault scenario, change-record schema, evidence expectations |
| `Server_Code_Walkthrough` | extend: inventory, roles, change workflow, audit |
| `Takehome_Build_Your_Client`, `Takehome_Deployment_Observability`, `Takehome_SDWAN_MCP`, `Takehome_OAuth21_Docker_Registry` | **new** — the four things cut from the day, documented to lab standard |
| `Bonus_Assignment_Prompts_Resources` | reuse as-is |
| Instructor `08_Instructor_Guide_8h` | **new** — pacing, answer keys incl. observed injection behaviour, fault-injection and chaos-beat scripts, reset runbook, SSH/VTY capacity runbook |
| Deck | `scripts/build_deck.py --track 8h`, ~+18 slides: beginner booking example (per `meet-notes.md`), JSON-RPC on screen, new topology → tools/resources/prompts map, vendor-MCP value story, trust boundaries, validate-before-promote, hub-and-spoke orchestration, deployment roadmap |
| Syllabus | regenerate `MCP_Workshop_1_Day_Outline` → v1.1 naming fast-agent, the Splunk MCP Server, DefenseClaw, LangGraph, and the DC/DR split |

`.md` stays source of truth: `python3 scripts/md2docx.py <name>.md <name>.docx`.

---

## Timeline — 13 working days, Wed 30 Sep → Fri 16 Oct 2026

**Week 1 — de-risk and re-point (Wed 30 Sep – Fri 2 Oct).** Nothing is authored until the environment is proven.

- **D1 (30 Sep):** Sandbox inventory capture — every device, management address, credential, `device_type`, and what accepts config. fast-agent spike: install, connect to the existing server with the bearer header, confirm `/tools` `/prompts` `/resources`, confirm the elicitation gate fires, confirm the OpenRouter provider. Record the config that actually worked.
- **D2 (1 Oct):** Splunk MCP spike against `cclorchestrator78` — confirm app 7931 and the Splunk version, create the read-only workshop role and token, confirm an index holding device syslog, connect Inspector **and** fast-agent to `https://cclorchestrator78:8089/services/mcp`. Two unknowns to settle here: whether the endpoint is Streamable HTTP or SSE (fast-agent needs the right `transport:`), and how to handle Splunk's self-signed management cert. Own server re-pointed: `DEVICES` inventory + `device_type`-aware `run_show`.
- **D3 (2 Oct):** DefenseClaw spike (Python 3.11 path + vulnerable server). Multi-agent app vendored and started against the new topology + vManage. `reset_lab.py` and `smoke_test.sh` rewritten. **Gate: all four spikes green, or the affected lab is re-scoped today, not in week 3.**

**Week 2 — build (Mon 5 – Fri 9 Oct).**

- **D4–D5:** Roles + role-filtered listing + enforcement; `tests/test_tools.py`; resource template. Lab 1 and Lab 2 guides written against captured output.
- **D6–D7:** `change_workflow.py` (validate-on-DR / promote-to-DC) + audit wrapper + `change_request` prompt. fast-agent config pack, all variants. Lab 3 guide.
- **D8:** Multi-agent MCP tool-source wiring; capstone fault-injection + restore scripts; dry-run the fault end to end and record what the orchestrator actually says.

**Week 3 — content, rehearse, freeze (Mon 12 – Fri 16 Oct).**

- **D9:** Lab 4 guide, with a live DefenseClaw run captured for the answer key.
- **D10:** Lab 5 capstone guide + instructor guide + reset/capacity runbooks.
- **D11:** Deck (+18 slides), syllabus v1.1, pre-flight rewrite, four take-home docs; all `.docx` regenerated.
- **D12 (Thu 15 Oct):** **Full-day dry run**, two seats simultaneously. Clock every block against the agenda; run the fault and the chaos beat; record injection behaviour.
- **D13 (Fri 16 Oct):** Dry-run fixes, skip-ladder retuning, **freeze**.

**Critical path:** inventory capture (D1) → Splunk instance + token (D2) → change workflow on DR/DC (D6–D7) → capstone fault (D8) → dry run (D12).

**If D1 inventory or DR write access slips:** Lab 5 D drops to an instructor demo and the change workflow is validated against the legacy c8000v instead. Decided on D3, not later.

---

## Verification

- **Per spike (week 1):** each recorded in `docs/spikes/` as a command sequence reproducible from a clean shell. No spike output reaches a lab guide unverified.
- **Server:** `cd code/server && ./run.sh` then `./smoke_test.sh` — health, 401, `initialize`, `tools/list`, plus readonly tool count and DC/DR reachability. `pytest -q` green with no device reachable.
- **Blast-radius check (non-negotiable):** with the default `device` argument and the readonly token, no tool can reach a DC device. Verified by test, not by inspection.
- **Harness:** `fast-agent go --config code/client-fastagent/lab3.yaml` → `/mcp` lists both servers; one prompt answered using tools from each; a config tool raises a form, and accept and decline both behave correctly.
- **External server:** Inspector and fast-agent both reach `https://cclorchestrator78:8089/services/mcp` with the workshop token; `splunk_run_query` returns rows from the lab index; the token cannot do anything but query.
- **Security:** DefenseClaw against `vulnerable_server.py` reports every planted issue; against the student server it produces a clean baseline plus the one deliberate finding.
- **Capstone:** the injected fault is diagnosable from evidence produced by at least two specialists; one change is promoted to DC carrying DR evidence in its record, then rolled back, DC at baseline, and the audit JSONL reconstructs the sequence. Chaos beat: validation fails → promote refuses → DC untouched.
- **Reset:** between cohorts, pods are re-provisioned — that is the reset. `reset_lab.py --apply` remains useful *inside* a pod for a student re-running a lab, and is verified by a second clean run reporting nothing to do.
- **Whole day:** the D12 dry run is the acceptance test. Every block inside its clocked duration, or the skip ladder is retuned before freeze.

---

## Open Items

- **D1 — resolved.** Device names, management addresses (`192.168.116.0/24`) and
  per-platform credentials all came from `custom-underlay.yaml`. Per-pod
  topologies also settle the seat→desktop and write-approval questions. One
  thing left to prove: that a desktop can reach the management subnet, and
  whether those addresses are **identical in every pod** (if not,
  `inventory.yaml` must be generated per pod). Run
  `./scripts/sanity_check.sh` in two pods and compare check 3.
- **D2 — Splunk runs on each pod's `cclorchestrator78`** (confirmed). Because pods are isolated, every item below must be baked into the **pod image**, not configured once on the day. Splunk running does
  not make the MCP server usable, so verify in order: app 7931 installed on a
  supported version (8.0–10.2); read-only workshop role in `authorize.conf` and
  a bearer token; **device syslog actually indexed** (no data, no lab); tcp/8089
  reachable from the participant desktops; and the self-signed management
  certificate handled deliberately. **Fallback if the app cannot be installed on
  that instance:** pyATS_MCP (`automateyournetwork/pyATS_MCP`, MIT) runs against
  the existing devices with no new infrastructure. Decide on D3, not in week 3.
- vManage API account for the SD-WAN specialist agent; ThousandEyes account and test IDs; ServiceNow instance and a valid incident number.
- OpenRouter budget and rate limits — ~16 seats running fast-agent *and* a LangGraph orchestrator; cap `max_tokens`.
- **Per-pod topologies remove the capacity question** — no shared devices, no shared Splunk, no VTY contention. What remains shared and therefore rate-limited is **OpenRouter**: ~16 concurrent fast-agent loops plus a LangGraph orchestrator each. Cap `max_tokens`.
- Participants are told in the joining instructions that the day is terminal-first (Gradio appears only in Lab 5).
- `code/client/LibreChat/` and `content/v2/` stay on disk, marked frozen in `CLAUDE.md`. Deleting the vendored LibreChat monorepo is a separate explicit decision — this repo is not under git, so removal is irreversible.

---

## Sources

- [evalstate/fast-agent](https://github.com/evalstate/fast-agent) · [config reference](https://fast-agent.ai/ref/config_file/) · [elicitations](https://fast-agent.ai/mcp/elicitations/) · [providers](https://fast-agent.ai/models/providers/additional/)
- [CiscoDevNet/Splunk-MCP-Server-official](https://github.com/CiscoDevNet/Splunk-MCP-Server-official) · [MCP Server for Splunk platform docs](https://help.splunk.com/en/splunk-enterprise/mcp-server-for-splunk-platform/2.0/mcp-server-tools)
- [cisco-ai-defense/defenseclaw](https://github.com/cisco-ai-defense/defenseclaw) (via `expansion/mcp-server-security.md`)
- Local: `Workshop/building-ai-agents-and-workflow-orchestration/agentic-ai-workshop/` → `multi_agent_v2`, `deployment/sdwan_agent`, `mcp/sdwan`, `k8s-agent`
- [CiscoDevNet/cisco-meraki-mcp-official](https://github.com/CiscoDevNet/cisco-meraki-mcp-official) — not adopted; kept as the vendor-hosted-MCP slide example
