# Workshop Content Improvement Plan

**Scope:** the five student-facing documents in `content/`. Server-code improvements are covered separately in [mcp-server-improvement-plan.md](mcp-server-improvement-plan.md); the 4-hour delivery structure is in [workshop-flow-4h.md](workshop-flow-4h.md).

**Basis:** full audit of all five documents, cross-checked against the actual repo code (`code/server/app/main.py`, vendored LibreChat v0.8.7 at `code/client/LibreChat/`).

---

## 1. Scorecard

| Document | Verdict | Effort | Summary |
|---|---|---|---|
| `Initial Setup Instructions.docx` | **Rewrite** | Low (1 page) | Screenshot-driven, outdated Inspector usage, no verification checkpoint |
| `Student_Guide_Formatted.docx` | **Heavy fix** | High | Good skeleton; missing promised sections, factual errors, LLM artifacts, must track server rewrite |
| `Student_GuideBonus.docx` | **Light fix** | Medium | Strongest hands-on doc; internal contradictions and a weak security claim |
| `EndToEndFlow.docx` | **Rewrite as a lab** | Medium | Pure narrative with protocol errors; convert to Inspector-observed wire trace |
| `PDFModel_Context_Protocol_WaterMarked.pdf` | **Fix list for deck owner** | Medium | Most complete MCP coverage but has hard factual errors and zero NetOps tie-in |

---

## 2. Per-Document Fixes

### 2.1 Initial Setup Instructions — rewrite

Current problems:
- Teaches `DANGEROUSLY_OMIT_AUTH=true npx @modelcontextprotocol/inspector` as the default path. Current Inspector auto-generates a session token and prints a pre-authed URL — disabling auth is unnecessary and models a bad habit in a workshop that now *teaches* auth.
- Unpinned `npx @modelcontextprotocol/inspector` means the UI drifts from the screenshots, and newer Inspector versions require explicitly choosing the transport type.
- Model instruction says "OpenRouter → Anthropic Claude-3.5-haiku" — legacy model name, and contradicts the other two documents (see §3.2).
- Unexplained IP `172.18.77.2` in the sample log; host naming (`linuxdesktop4`) collides with other docs.
- No prerequisites, no failure path, no "you are ready when…" checkpoint.

Rewrite as a one-page **pre-flight checklist**:
1. Prerequisites (browser, SSH client, credentials handed out).
2. Steps as copy-pasteable commands (not screenshots) with expected output snippets.
3. Pin the Inspector version (`npx @modelcontextprotocol/inspector@<pinned>`) and use the token URL it prints — remove `DANGEROUSLY_OMIT_AUTH`.
4. Explicit transport selection step for Inspector (Streamable HTTP, URL `http://172.18.1.2:8000/mcp` once the server is upgraded).
5. End with a green-light checklist: LibreChat login OK → server health `curl http://172.18.1.2:8000/` OK → Inspector connected and `tools/list` shows expected tools.

### 2.2 Student Guide (Formatted) — heavy fix

**Structural defects (content promised but absent):**
- ToC lists "Troubleshooting Common Issues" — **the section does not exist in the body.** Write it (source material: Bonus guide's troubleshooting + the new matrix in §4.3).
- "Network Configuration" heading has **no table under it.** Insert the canonical topology table (§3.1).

**Factual errors:**
- SSE described as "bidirectional" twice, then correctly described as one-way in Section 7. Fix the two wrong instances; once the server moves to Streamable HTTP, reframe the transport section entirely (SSE becomes a "legacy transport" sidebar).
- `librechat.yaml` `version: 1.2.8` — the vendored client uses **`1.3.13`** (`code/client/LibreChat/librechat.example.yaml`).
- "All three components are connected on the same network" — they sit on three different /24s (172.18.0.x / 172.18.1.x / 172.18.2.x). Correct and use it as a teaching point (why the MCP server URL is not `localhost` from LibreChat's perspective).
- Corrupted code line: `await mcp_server.run (streams, streams[^19], ...)` — real code is `mcp_server.run(streams[0], streams[1], mcp_server.create_initialization_options())`. (This whole section is replaced by the FastMCP walkthrough after the server rewrite.)
- Sample router output contradicts EndToEndFlow (Gi0/0 vs Gi0/1 up/down reversed). Capture one real `show ip interface brief` from Router1 and use it verbatim in **both** documents.

**Editorial:**
- Purge residual LLM citation artifacts: `[1]`, `[3]`, `[^0]`, `[^19]`, `[^12345]`.
- Remove hype phrasing ("This is not science fiction", "the future of network management") — replace with plain operational language.
- Standardize on Docker Compose v2 syntax (`docker compose`, no hyphen) and consistent `sudo` usage.
- `request._send` (private ASGI attribute) — disappears with the FastMCP rewrite; until then add a "lab shortcut, not production practice" caveat.

**Content updates tied to the server rewrite:**
- The line-by-line code deep dive (Sections 1–8) must be rewritten against the new FastMCP server: decorators instead of `list_tools()`/`call_tool()` dispatch, `/mcp` Streamable HTTP endpoint instead of `/sse` + `/messages/`, bearer-token middleware section, env-var credentials instead of the hardcoded `ROUTER_CONFIG` block.
- Add short sections introducing the primitives students will now touch in labs: resources, prompts, notifications, elicitation — each one paragraph plus a pointer to the lab where they practice it (coverage map, §4.4).
- Add a hardcoded-credentials exercise: the guide already has a good security note; turn it into a 5-minute "move creds to env vars" task with acceptance criterion.

### 2.3 Student Guide Bonus — light fix

This is the strongest artifact (real build exercise, real troubleshooting). Keep its shape; fix:

- **Contradictory edit paths:** PART 1 says create `app/newmain.py` + repoint `run.sh`; the DETAILS section says edit `main.py`; Step 1 title references a nonexistent `mcp_server.py`. Standardize on **one** path (recommend: edit `app/main.py` directly, with `git`/backup note) and fix all references.
- **Directory drift:** `~/cisco_mcp` vs `~/ciscomcp` (the latter fails), log path `/home/ubuntu/ciscomcp/command_history.log`. Standardize on `~/cisco_mcp`.
- Host naming "Desktop 14/13" → `linuxdesktop4`/`linuxdesktop3` per the canonical table.
- `sudo docker-compose down` / `up` foreground → `docker compose restart api` (v2, detached, doesn't block the terminal).
- Log expectation `POST /messages HTTP/1.1` → actual mount is `/messages/` (trailing slash); after the transport upgrade this becomes `POST /mcp`.
- **Overstated security claim.** "Only show commands are allowed — security is maintained" is false: `startswith("show")` permits `show running-config` (credential exposure) and IOS pipe/redirect abuse (`show run | redirect tftp://…`). Fix the exercise: exact-command allowlist, reject `|` and `>`, and keep `show running-config` **out** of the allowlist. Frame the bypass itself as a teaching moment ("why prefix matching is not a guardrail").
- **Add tool annotations** (`readOnlyHint`, `destructiveHint`) to the exercise — the entire premise is read-only vs config-writing tools and MCP has a first-class mechanism for exactly this that no document mentions.
- Add timeboxes: main build ~45 min; Advanced Exercises A/B/C ~15 min each, marked optional/take-home.
- Test Case 3 (invalid command → LLM retries): add one line on where the tool error appears in LibreChat's UI/logs so students can tell "good failure" from "broken lab".

### 2.4 EndToEndFlow — rewrite as an observed-wire-trace lab

The narrative has protocol errors and duplicates what students can *watch live* in Inspector. Convert to **Lab 1** (see flow doc): students trigger each step and observe real traffic.

Errors to fix in whatever prose remains:
- The **`initialize` → `notifications/initialized` handshake is skipped entirely** — the flow jumps from connection to `tools/list`. Add it; it's where capability negotiation (the reason the workshop needs two clients) becomes visible.
- Step 3 labels the `tools/list` request "MCP Client responds" — the client *initiates*; and the JSON-RPC object omits `"id"`, which would make it a notification, not a request.
- Step 5 shows a tool passed to the Anthropic API without `input_schema` — invalid tool block.
- `claude-3-5-sonnet-20241022` called directly against `api.anthropic.com` — wrong model generation and wrong provider path for this lab (goes via OpenRouter). Align with the single model story (§3.2).
- Fabricated LibreChat request shape (`{"message", "model", "mcp_server"}`).
- Protocol table says "HTTPS/WebSocket" browser↔LibreChat while Step 13 says SSE — LibreChat streams over SSE; pick one.
- Router output must match the Student Guide's (same captured output, §2.2).
- Transport story updates to Streamable HTTP after the server rewrite.

### 2.5 Concepts deck (PDF) — fix list for the deck owner

The deck is the only artifact covering all six primitives — keep it as the lecture backbone, but it needs a correction pass. In priority order:

1. **Termination slide shows LSP, not MCP.** `{"method":"shutdown"}` / `{"method":"exit"}` do not exist in MCP; termination is transport-level close (or HTTP `DELETE` of the Streamable HTTP session).
2. **Elicitation slide is wrong twice.** Real method is `elicitation/create` with a flat `requestedSchema` (JSON Schema, primitive properties) and result `{action: accept|decline|cancel, content}` — not `elicitation/request` with `inputType`. Worse, the example elicits an **API key**: the spec explicitly forbids using elicitation for secrets. Replace with the lab's own example (confirm before router config change).
3. **`notifications/initialized` is sent by the client**, not the server ("Server ready after initialization" is backwards).
4. **Spec version:** update `2025-06-18` → `2025-11-25`; add the revision's additions where relevant (structured tool output / `outputSchema`, tool annotations, tasks).
5. **Transport slide consistency:** one slide lists "HTTP+SSE" as a current transport, another correctly says Streamable HTTP. Label HTTP+SSE as *deprecated (2025-03-26)* / legacy.
6. **Fabricated SDK code:** `from mcp import Client; client = Client(...); await client.connect()` is not the Python SDK. Use real `ClientSession` + `streamablehttp_client` snippet, or the server-side FastMCP decorator example that matches the lab.
7. `hints: ["claude-3-5-sonnet"]` in the sampling example → current model naming; add the missing `modelPreferences` priority fields if the slide keeps that depth.
8. Sampling human-in-the-loop stated as MUST → spec says SHOULD (design principle).
9. **Uncited quantitative claims** ("60-70% of development time", "90% less maintenance", "67% reduction", "150+ lines per tool") — cite a source or cut. Same for the "— Anthropic, 2024" quote.
10. Ecosystem slide is 2024-vintage (Zed/Replit/Sourcegraph) — refresh; mention the MCP Registry.
11. **Zero network-operations content despite the title.** Add 2–3 slides bridging concepts → this lab: the Cisco router tool example, read-only vs destructive tools on network gear, and where validation gates belong before an AI agent touches production config. This is the biggest audience mismatch.
12. Mechanical: font/ligature corruption ("Solu-on", "condiAons", "noQﬁcaQons"), typos ("Expertize", "AreLarge"), duplicated/out-of-order MxN slides, unreliable footer numbering, image-only slides have no text layer (searchability/accessibility), copyright footer says 2021 on a 2025 deck, and Section 5's agenda promises an "Implementation guide" that doesn't exist — either add it (pointer to the labs) or fix the agenda.

---

## 3. Cross-Cutting Fixes (single-source these once)

### 3.1 Canonical lab topology table

Create once (in the Student Guide), reference from every other doc. Resolve naming collisions (`linuxdesktop3/4` vs "Desktop 13/14", `~/cisco_mcp` vs `~/ciscomcp`).

| Component | Host | Address | Notes |
|---|---|---|---|
| LibreChat (MCP client) | `linuxdesktop3` | `172.18.0.2:3080` (browser: `127.0.0.1:3080`) | login `student@email.local` / `password` |
| MCP server | `linuxdesktop4` | `172.18.1.2:8000` | code at `~/cisco_mcp/app/main.py`, start with `./run.sh` |
| Router1 | — | `172.18.2.6` | cisco_ios, admin/admin, enable admin |
| Router2 (Bonus Ex. B) | — | `172.18.2.10` | confirmed on lab topology diagram 2026-08-04 (Bonus guide wrongly says `.7` — fix it) |
| MCP Inspector | on `linuxdesktop4` | UI `127.0.0.1:6274`, proxy `127.0.0.1:6277` | pinned version |
| Containers on desktop3 | — | — | `LibreChat`, `chat-mongodb`, `chat-meilisearch`, `rag_api`, `vectordb` |

Open item for the lab owner: explain or remove the `172.18.77.2` client IP that appears once in the Setup doc's sample log.

### 3.2 One model story

Three documents currently name three different models via two different provider paths. **DECIDED (2026-08-04): `anthropic/claude-haiku-4.5` via OpenRouter.** The old default `meta-llama/llama-3-70b-instruct` is delisted from OpenRouter entirely ("No endpoints found" — verified against the lab key); claude-haiku-4.5 verified working on the same key. Use this exact model ID in every document and JSON example. Remaining before publishing: verify it reliably emits tool calls in the actual Lab 2/3 prompts (initial chat test passed).

### 3.3 Editorial conventions

- Docker Compose v2 (`docker compose`) everywhere; consistent `sudo`.
- One directory (`~/cisco_mcp`), one entry file (`app/main.py`), one server start command (`./run.sh`).
- Copy-pasteable commands over screenshots; screenshots only for UI orientation.
- No unedited LLM output: strip citation markers, verify every code block imports/runs, no empty promised sections.
- Tone per house style: practical operational language; no "future of networking" flourishes.

---

## 4. New Content Needed (currently missing entirely)

### 4.1 Instructor guide
Pacing notes per module (see [workshop-flow-4h.md](workshop-flow-4h.md)), answer key for exercises, what-to-cut-when-behind order, pre-workshop checklist (router reachable, OpenRouter credit, containers up, Inspector version pinned).

### 4.2 Lab reset procedure
`configure_interface` and the loopback exercises mutate live router config, and nothing restores baseline between cohorts. Provide: baseline `show running-config` capture, a reset command set (delete `Loopback*` with `MCP_CREATED` description, restore interface IPs), and a pre-flight "router state matches baseline" check.

### 4.3 Troubleshooting matrix
One table shared by Student Guide (new section) and instructor guide:

| Symptom | First check | Fix |
|---|---|---|
| Tool missing from `tools/list` | Inspector `tools/list` | server not restarted after edit; decorator/schema error |
| LibreChat shows no MCP tools | `docker compose logs api` for MCP init errors | `librechat.yaml` URL/type; SSRF `allowedAddresses`; auth header |
| 401 from server | `curl -H "Authorization: Bearer $TOKEN" http://172.18.1.2:8000/mcp` | token mismatch env vs yaml |
| Model never calls the tool | tool description quality; try Inspector manual call | improve description; check chosen model supports tool use |
| OpenRouter 401/402 | LibreChat logs | key invalid / out of credit |
| SSH timeout to router | `ping 172.18.2.6`, then manual `ssh admin@172.18.2.6` | lab network / router down |
| Blank output / `read_timeout` | command takes >30 s | Netmiko `read_timeout`, command whitelist |

### 4.4 Concept coverage map
The deck teaches six primitives; the labs currently practice one. Target state (kept in the flow doc, summarized in the Student Guide):

| MCP concept | Taught (deck §) | Practiced (lab) | Client |
|---|---|---|---|
| Tools | 4 | Labs 1–3 | Inspector + LibreChat |
| Auth (bearer) | 4 | Lab 2 | LibreChat |
| Resources | 4 | Lab 4 | Inspector |
| Prompts | 4 | Lab 4 | Inspector |
| Notifications / subscriptions | 4 | Lab 5 | Inspector |
| Elicitation | 4 | Lab 5 | Inspector |
| Sampling | 4 | lecture only (no client support) | — |

### 4.5 Packaging
- `requirements.txt` for the server (currently absent — students cannot rebuild the environment).
- Reference `librechat.yaml` checked into the repo (currently no yaml/env exists anywhere in the workshop tree).
- Pin the Inspector version in every doc that launches it.

---

## 5. Sequencing

1. **First:** canonical topology table + model story decision (§3.1, §3.2) — every other fix references them.
2. Server rewrite lands (separate plan) → freeze the new code.
3. Rewrite Setup doc and EndToEndFlow lab against the new server.
4. Heavy-fix Student Guide (code deep dive against new server; add missing sections).
5. Light-fix Bonus guide.
6. Deck correction pass (can run in parallel; owned by deck author).
7. New content: instructor guide, reset procedure, troubleshooting matrix.
8. Final editorial pass across all docs (artifacts, tone, consistency) + dry run against the 4-hour flow.
