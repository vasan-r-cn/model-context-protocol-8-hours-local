# Workshop Catalog — MCP in Practice, 8 Hours

The day as the sandbox publishes it: **8 categories, 28 exercises**.
Left column is the sandbox category, the table under it is that category's
exercises. One markdown file per exercise under `exercises/<category>/`.

**Day budget:** 330 min hands-on · 90 min lecture (separate deck) · 60 min
breaks and lunch = 480 min.

The arc: **make a model answer → make it act → read the protocol underneath →
build a server → consume servers you didn't write → control them → orchestrate
them.** Category 2 ends by hitting the wall that Category 3 exists to remove.

---

## Category map

| # | Category | Min | Exercises | What a participant leaves with |
|---|---|---|---|---|
| 1 | LLM Foundations | 20 | 2 | A working sandbox and one model call they made themselves |
| 2 | AI Agents | 40 | 4 | An agent with hand-wired tools — and a concrete reason that stops scaling |
| 3 | MCP Protocol | 45 | 3 | They have read MCP off the wire; none of it is magic |
| 4 | Build an MCP Server | 60 | 4 | A tool they wrote, callable by a model, tested with no device plugged in |
| 5 | MCP Servers You Didn't Write | 50 | 3 | Composition across servers they cannot change |
| 6 | MCP Security & Control | 45 | 4 | Blast radius, human approval, injection, scanning — proven, not asserted |
| 7 | Multi-Agent Capstone | 70 | 4 | A root cause from evidence, and a change promoted to production only after DR validated it |
| 8 | Take-Home | — | 4 | The four things that did not fit, documented to lab standard |

---

## 1 · LLM Foundations — 20 min

Get the sandbox working and make one model call by hand, so every later
exercise has a known-good starting point.

| # | Exercise | Min | Targets |
|---|---|---|---|
| 1.1 | [Environment Setup & Sandbox Tour](exercises/01-llm-foundations/01-environment-setup.md) | 12 | — |
| 1.2 | [First LLM Call](exercises/01-llm-foundations/02-first-llm-call.md) | 8 | — |

## 2 · AI Agents — 40 min

Build an agent whose tools are wired in by hand — then feel why that does not
scale. This is the problem MCP exists to solve.

| # | Exercise | Min | Targets |
|---|---|---|---|
| 2.1 | [Simple Agent — Tools Wired by Hand](exercises/02-ai-agents/01-simple-agent.md) | 18 | `ciscovmanage3` (read-only) |
| 2.2 | [Agent with Memory](exercises/02-ai-agents/02-agent-with-memory.md) | 9 | `ciscovmanage3` (read-only) |
| 2.3 | [Agent with Streaming](exercises/02-ai-agents/03-agent-with-streaming.md) | 8 | — |
| 2.4 | [The Integration Wall](exercises/02-ai-agents/04-the-integration-wall.md) | 5 | — |

> 2.4 is a written exercise, not code. It is the hinge into Category 3 — do not cut it.

## 3 · MCP Protocol — 45 min

Read the protocol off the wire before trusting any abstraction over it.

| # | Exercise | Min | Client |
|---|---|---|---|
| 3.1 | [Protocol on the Wire](exercises/03-mcp-protocol/01-protocol-on-the-wire.md) | 20 | MCP Inspector |
| 3.2 | [Raw Session by Hand](exercises/03-mcp-protocol/02-raw-session-by-hand.md) | 13 | `curl` |
| 3.3 | [First MCP Agent](exercises/03-mcp-protocol/03-first-mcp-agent.md) | 12 | fast-agent |

## 4 · Build an MCP Server — 60 min

Write a tool a model can discover and call, and prove it works with no device
plugged in.

| # | Exercise | Min | Targets |
|---|---|---|---|
| 4.1 | [Run and Read the Server](exercises/04-build-mcp-server/01-run-and-read.md) | 12 | `sdceightkv24` |
| 4.2 | [Build a Read-Only Tool](exercises/04-build-mcp-server/02-build-a-read-only-tool.md) | 25 | `sdceightkv24` → `sdceightkv11` |
| 4.3 | [Tool Design — Granularity, Schema, Errors](exercises/04-build-mcp-server/03-tool-design.md) | 8 | — |
| 4.4 | [Test Without a Device](exercises/04-build-mcp-server/04-test-without-a-device.md) | 15 | none — runs offline |

## 5 · MCP Servers You Didn't Write — 50 min

Consume servers you cannot change, on their terms — then compose them.

| # | Exercise | Min | Server |
|---|---|---|---|
| 5.1 | [SD-WAN MCP Server](exercises/05-servers-you-didnt-write/01-sdwan-mcp-server.md) | 22 | `code/server-sdwan` → vManage, `:7004` |
| 5.2 | [Splunk MCP Server — a Vendor Server on Its Terms](exercises/05-servers-you-didnt-write/02-splunk-mcp-server.md) | 13 | `splunk-mcp-server2` (SSE `:8050`) → Splunk `:8089` |
| 5.3 | [Three Servers, One Agent](exercises/05-servers-you-didnt-write/03-three-servers-one-agent.md) | 15 | all three |

> **Leave 5.1's server running** — Exercise 6.4 scans it.

## 6 · MCP Security & Control — 45 min

Identity, blast radius, human approval, injection and scanning — before any
tool is allowed to change state.

| # | Exercise | Min | Targets |
|---|---|---|---|
| 6.1 | [Roles & Blast Radius](exercises/06-security-and-control/01-roles-and-blast-radius.md) | 12 | `sdceightkv24` allowed · `sdceightkv11` refused |
| 6.2 | [Human Approval — the Elicitation Gate](exercises/06-security-and-control/02-elicitation-gate.md) | 12 | `sdceightkv24` |
| 6.3 | [Prompt Injection via Tool Results](exercises/06-security-and-control/03-prompt-injection.md) | 8 | `sdceightkv24` |
| 6.4 | [MCP Defence — Scanning a Server](exercises/06-security-and-control/04-mcp-defence.md) | 13 | the 5.1 server |

## 7 · Multi-Agent Capstone — 70 min

Diagnose a real fault with an orchestrator, then promote a fix to production
only after it has been validated on DR.

| # | Exercise | Min | Targets |
|---|---|---|---|
| 7.1 | [Orchestrator Walkthrough](exercises/07-capstone/01-orchestrator-walkthrough.md) | 15 | read-only |
| 7.2 | [Wire Your MCP Server into a Specialist](exercises/07-capstone/02-wire-your-mcp-server.md) | 15 | `sdceightkv24` |
| 7.3 | [Diagnose the Fault](exercises/07-capstone/03-diagnose-the-fault.md) | 25 | Site-10 → DC path |
| 7.4 | [Validated Change — DR, Then DC](exercises/07-capstone/04-validated-change.md) | 15 | validate `sdceightkv24` → promote `sdceightkv11` |

## 8 · Take-Home — not clocked

| # | Exercise | Source |
|---|---|---|
| 8.1 | [AI Workflow Deployment — Docker & Tracing](takehome/01-deployment-observability.md) | `expansion/ai-workflow-deploymeny.md` |
| 8.2 | [Kubernetes MCP Server](takehome/02-kubernetes-mcp-server.md) | `expansion/k8s-mcp-erver.md` — no cluster in this topology |
| 8.3 | [Build Your Own MCP Client](takehome/03-build-your-own-mcp-client.md) | net-new |
| 8.4 | [Remote MCP Hardening](takehome/04-remote-mcp-hardening.md) | net-new |

---

## Dependencies that are not just "the previous exercise"

| This | Needs | Why |
|---|---|---|
| 6.4 MCP Defence | 5.1 SD-WAN MCP **still running** | The scan targets that server |
| 7.2 Wire Your Server | 4.2 Build a Tool | It is *that* tool the orchestrator calls |
| 7.4 Validated Change | 7.3 Diagnose | The change is the one 7.3 recommended |
| 5.3 Three Servers | 5.1 **and** 5.2 | Composition needs more than one server to compose |

## Skip ladder

Cut in this order when the clock slips. Re-time at the end of a category,
never mid-exercise.

1. 6.4 MCP Defence → take-home (−13)
2. 2.3 Agent with Streaming → instructor demo (−8)
3. 4.4 Test Without a Device → take-home (−15)
4. 3.2 Raw Session by Hand → dissect `smoke_test.sh` instead (−13)
5. 7.4 Validated Change → instructor drives it, participants watch (−15)
6. 7.2 Wire Your MCP Server → ship it pre-wired (−15)

**Never cut:** 1.1 · 2.4 · 3.1 · 4.2 · 6.1 · 6.2 · 7.1 · 7.3.

## Clock checkpoints

| By | Category complete |
|---|---|
| +0:20 | 1 — LLM Foundations |
| +1:00 | 2 — AI Agents |
| +1:45 | 3 — MCP Protocol |
| +2:45 | 4 — Build an MCP Server |
| +3:35 | 5 — Servers You Didn't Write |
| +4:20 | 6 — Security & Control |
| +5:30 | 7 — Capstone |

Hands-on time only; lecture and breaks sit between categories and are the
instructor guide's problem, not this file's.

---

## Conventions

- **`.md` is the source of truth.** Regenerate a Word copy only where one is
  needed: `python3 scripts/md2docx.py <name>.md <name>.docx`.
- **Every exercise uses the same section order** — see any file under
  `exercises/`. Introduction · What You'll Learn · Before You Start ·
  Architecture Overview · Setup · Exercises · Verify · Troubleshooting ·
  Quick Reference.
- **Screenshots are placeholders** written as `[SCREENSHOT n: description]`
  and pasted in manually. Do not reuse the external image URLs in
  `expansion/` — they show the previous sandbox.
- **No invented output.** Every command and every result pasted into an
  exercise was run on a participant desktop first.
- `content/v2/` is frozen and describes the retired two-router lab. Do not
  hand it to participants.
