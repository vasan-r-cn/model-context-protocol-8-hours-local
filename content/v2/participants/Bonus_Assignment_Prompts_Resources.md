# Bonus Assignment — MCP Prompts & Resources with a Real Client

## Take-home lab: consume what LibreChat can't, using Claude Code (or Codex CLI)

**Time:** 45–60 minutes, self-paced.
**Prerequisite:** the workshop MCP server running and reachable (`http://172.18.1.2:8000/mcp`, or your own copy on `localhost`), plus the bearer token from your lab sheet.

### Why this assignment exists

In the workshop you saw the capability table: LibreChat consumes **tools** and **auth**, but its client implements neither MCP **prompts** nor **resources** — you inspected those in MCP Inspector instead. Inspector is a debugging lens, though, not a product. This assignment closes the loop: you will consume prompts and resources from a **production-grade client** — a coding agent on your own machine — and see why a server author ships them even when one popular client ignores them.

Claude Code is the primary path below. Codex CLI notes are at the end — the concepts are identical.

---

## Part 1 — Register the workshop server (10 min)

Claude Code is a full MCP client. Add the server with the same URL and bearer token LibreChat used:

```bash
claude mcp add --transport http cisco-router http://172.18.1.2:8000/mcp \
  --header "Authorization: Bearer cisco-mcp-workshop"
```

Verify, inside a Claude Code session:

```
/mcp
```

You should see `cisco-router` listed as connected, with its tool count.

**Checkpoint 1:** `/mcp` shows the server connected. If it shows a failure: same debugging order as the workshop — is the server up (`curl http://172.18.1.2:8000/`)? Is the token right (server terminal prints the 401 reason)?

**Think about what just happened:** no yaml on someone else's desktop, no container restart. You attached a network-operations server to your personal coding agent with one command. That is the M+N promise from the lecture, experienced first-hand.

---

## Part 2 — Prompts as slash commands (15 min)

The server defines two MCP prompts (`troubleshoot_interface`, `audit_router_config` — see the Server Code Walkthrough, section 9). Claude Code surfaces every MCP prompt as a **slash command** named:

```
/mcp__<server>__<prompt>
```

1. Type `/mcp__cisco-router__` and let autocomplete show you both prompts. This list came from `prompts/list` — the request LibreChat never sends.
2. Run the parameterized one:

```
/mcp__cisco-router__troubleshoot_interface GigabitEthernet0/1
```

3. Watch what happens: the server-authored diagnostic template (with your interface name substituted) becomes the user message, and the agent starts working through it — checking status via the `get_interfaces` tool, reading detail, reasoning about causes.
4. Now run `/mcp__cisco-router__audit_router_config` and watch the agent audit the running config against the server's checklist.

**Checkpoint 2:** both prompts run; the agent calls at least one MCP tool while executing them.

**Questions to answer in your write-up:**
- Who wrote the words the agent is following — you, the client, or the server author? Why does that division of labor matter for a network operations team?
- The prompt told the agent to only use commands `dynamic_show` allows. Did it comply?
- Real-world mapping: what team runbook would you encode as an MCP prompt tomorrow?

---

## Part 3 — Resources as on-demand context (15 min)

The server exposes four resources (`router://interfaces`, `router://running-config`, `router://baseline`, and the template `router://interfaces/{name}`). Claude Code lets you **@-mention** a resource to pull it into context:

```
@cisco-router:router://interfaces
```

1. Start a fresh conversation. Type `@cisco-router:` and let autocomplete list the resources — that's `resources/list` on the wire.
2. Mention `@cisco-router:router://interfaces` and ask: *"which interfaces are administratively down?"* The interface table was fetched by the **client at your request** — the model never called a tool.
3. Now the sharper experiment. Ask the same question in a fresh conversation **without** the mention. The agent must call `get_interfaces` itself. Same data, two control points:

| | Resource (@-mention) | Tool call |
|---|---|---|
| Who decided to fetch | you (the user) | the model |
| When | before the model ran | mid-reasoning |
| Server-side guardrail | auth only | auth + allowlist + annotations |

4. Recall from the workshop: `show running-config` is *rejected* by `dynamic_show` but *served* as `router://running-config`. Mention it — `@cisco-router:router://running-config` — and ask for an audit. You have just used the design distinction the walkthrough explained: the model can't grab the full config on its own initiative, but a human deliberately loading it as context is a different trust decision.

**Checkpoint 3:** you can explain, in two sentences, why the same data is a blocked command but an available resource.

---

## Part 4 — Stretch goals (optional)

- **Templated resource:** mention `@cisco-router:router://interfaces/GigabitEthernet0/1` — the client filled a URI template (`resources/templates/list` on the wire).
- **Baseline diff:** run the `snapshot_config` tool, make a config change (`create_loopback 250`), then give the agent both `@cisco-router:router://running-config` and `@cisco-router:router://baseline` and ask for the diff. You've built a change-review workflow from primitives.
- **Clean up after yourself:** ask the agent to remove the loopback you created — or run the instructor's `reset_lab.py` if you're on the shared router.
- **Codex CLI users:** register the same server (see below) and repeat Parts 2–3 with its equivalents.

---

## Deliverable

A short document (markdown or docx, 1–2 pages) containing:

1. Screenshot or transcript of `/mcp` showing the connected server.
2. Transcript excerpt of one prompt run (Part 2) and one resource-driven answer (Part 3).
3. Your answers to the Part 2 and Part 3 questions.
4. A completed comparison row: for each of tools / prompts / resources / elicitation — which of the three clients you used this week (LibreChat, Inspector, Claude Code) consumed it, and who controls each primitive.

Submit to the instructor channel. Done when all four items are present.

---

## Codex CLI alternative

Codex CLI is also an MCP client. Registration differs by version — check `codex mcp --help`. Current versions support adding servers via CLI or in `~/.codex/config.toml`. If your version only supports stdio servers, bridge our HTTP server through `mcp-remote`:

```toml
[mcp_servers.cisco-router]
command = "npx"
args = ["-y", "mcp-remote", "http://172.18.1.2:8000/mcp",
        "--header", "Authorization: Bearer cisco-mcp-workshop"]
```

The `mcp-remote` bridge trick is worth knowing on its own: it converts any Streamable HTTP MCP server into a stdio one, which makes our server usable from **any** MCP client, whatever transport it speaks.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `/mcp` shows connection failed | server down / URL wrong / port blocked | `curl http://172.18.1.2:8000/` first |
| 401 in server terminal | token typo — terminal prints the exact reason | fix the `--header` value; `claude mcp remove cisco-router` and re-add |
| slash commands don't appear | prompts not fetched | check `/mcp` shows the server connected; restart the session |
| `@cisco-router:` shows no resources | resource listing failed | verify in Inspector that resources list; then reconnect the client |
| resource read hangs | router unreachable from the server | test `get_interfaces` from Inspector — same SSH path |
