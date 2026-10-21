# Participant Q&A — Instructor Reference

Answers to the questions participants actually ask, grounded in **this** workshop's stack (FastMCP server on Streamable HTTP, bearer auth, LibreChat v0.8.7 + Inspector + Claude Code). Where a claim is verifiable in the lab, the answer says how to show it live — always stronger than telling.

Sections: A. Tools & discovery · B. Transports & connections · C. Multiple servers & scale · D. Auth & security · E. The other primitives · F. The model & tool-calling · G. Protocol mechanics · H. Production & real-world · I. Troubleshooting patterns · J. Ecosystem & "what next".

---

## A. Tools and discovery

**A1. I added 2 new tools to the server. How does the client discover them?**

Discovery happens at `tools/list`. When and whether a client re-runs it is the whole answer, and it differs by client:

- **The server announces the change.** On our server, tools registered/removed at runtime fire `notifications/tools/list_changed` (that's exactly what `enable_config_tools` does). A capable client hears it and re-fetches `tools/list`.
- **Inspector** honors it — you saw the tool list change live in Lab 5.
- **LibreChat does NOT.** It discovers tools once, at MCP-server initialization (startup or manual reinitialize), and ignores `list_changed`. So new tools appear only after you **reinitialize the server** from the MCP menu, or restart the `api` container.
- **If you just edited `main.py`:** the *server process itself* must reload first — stop and `./run.sh`, or the tools don't exist yet to be discovered. Verify in Inspector, then reinitialize LibreChat.

Live demo: add a trivial tool, restart the server, show it instantly in Inspector, show it absent in LibreChat until reinitialize. That contrast is the lesson.

**A2. How does the model know when to call a tool, and which one?**

It reads the tool **description** (from the docstring) and the parameter schema (from the type hints), which LibreChat passes to the model alongside your message. The model matches intent to description. This is why "the docstring is prompt engineering" — a vague description means wrong or missing calls. Show it: sharpen a docstring, watch selection improve.

**A3. Do I have to restart everything when I change a tool's code?**

Restart the **server** (the Python process) — always, because the code is loaded in memory. Then re-discover on the client (Inspector auto, LibreChat manual). You do **not** restart LibreChat's containers for a tool change — just reinitialize the server from its MCP menu.

**A4. Can one tool call another tool?**

Not through the protocol — tools are called by the client, not by each other. But inside your Python you can freely call shared helpers (all our tools call `run_show`/`run_config`). If you want composed behavior, write a helper and have both tools use it, or let the *model* chain calls (it happily calls tool B after seeing tool A's result).

**A5. How many tools is too many?**

Practical limits are the model's, not the protocol's: every tool's description sits in the context window on every turn, and too many similar tools degrade selection accuracy. Dozens are fine; hundreds start to hurt tool-choice quality and cost. Mitigations: sharp, distinct descriptions; the runtime toggle pattern (`enable_config_tools`) to expose only relevant tools; or splitting across multiple servers (section C).

---

## B. Transports and connections

**B1. Why Streamable HTTP and not SSE? What happened to the old `/sse`?**

SSE (the two-endpoint HTTP+SSE transport) was **deprecated in the MCP spec revision 2025-03-26**. Streamable HTTP replaced it: one endpoint (`/mcp`), supports request/response, server-to-client streaming, and resumable sessions. The v1 workshop used SSE; the rebuilt server uses Streamable HTTP, which is why the old `librechat.yaml` (`type: sse`, url `/sse`) failed to connect — the endpoint no longer exists.

**B2. What are the transport options, and when do you use each?**

| Transport | Where it runs | Use |
|---|---|---|
| **stdio** | client launches the server as a local subprocess | local tools, desktop clients, CLIs |
| **Streamable HTTP** | server runs as a network service | remote/shared servers — our lab |
| HTTP+SSE | — | deprecated; legacy only |

Our server is a shared network service reached by clients on other hosts, so Streamable HTTP is the natural fit. A purely local tool (say, one that reads your filesystem) would use stdio.

**B3. Can a stdio-only client use our HTTP server?**

Yes, via a bridge: `mcp-remote` turns a Streamable HTTP server into a stdio one. This is in the take-home assignment for Codex CLI. Useful trick — it makes any HTTP MCP server reachable from any client, whatever transport it speaks.

**B4. Is the connection persistent? What is a session?**

Streamable HTTP maintains a **session** (you saw the `mcp-session-id` header in the smoke test). The client initializes once, then reuses the session for many tool calls. Our server is stateful (`stateless_http=False`) specifically so subscriptions and the elicitation round-trip work — those need continuity between requests.

**B5. Does the router SSH connection stay open?**

No — each tool call opens an SSH session, runs its command(s), and disconnects (see the `run_show`/`run_config` helpers). Simple and robust for a lab; a high-throughput production server would pool connections. Worth mentioning as a "what you'd change for scale" point.

---

## C. Multiple MCP servers and scalability

**C1. How do I connect multiple MCP servers?**

Every client supports many servers at once — MCP is designed for it. In LibreChat, add more entries under `mcpServers:`:

```yaml
mcpServers:
  cisco-router:
    type: streamable-http
    url: "http://172.18.1.2:8000/mcp"
    headers: { Authorization: "Bearer ${CISCO_MCP_TOKEN}" }
  monitoring:
    type: streamable-http
    url: "http://172.18.1.5:9000/mcp"
    headers: { Authorization: "Bearer ${MONITORING_TOKEN}" }
```

The client connects to each independently, runs `tools/list` on each, and presents the **union** of tools to the model, namespaced by server. The model then picks tools across servers in one conversation — ask a question that needs a router check *and* a monitoring lookup, and it calls one tool from each.

**C2. What if two servers have a tool with the same name?**

Clients namespace tools by server (LibreChat prefixes internally; Claude Code exposes them as `mcp__<server>__<tool>`). No collision — the server identity disambiguates. Keep names descriptive anyway; the model reads names too.

**C3. Does MCP scale? What are the limits?**

Distinguish three axes:

- **Servers per client:** effectively unlimited; the ceiling is the model's context (every server's tool list is in the prompt) and tool-selection accuracy, not the protocol. Same limit as A5.
- **Concurrent clients per server:** an async HTTP service scales like any web service — behind a load balancer, horizontally. Our lab server is single-process (fine for a classroom); production runs multiple workers/replicas.
- **Throughput per server:** bounded by the backend it fronts. Ours is bounded by SSH to one router (each call opens a session). A real deployment pools connections, caches, and rate-limits.

The honest framing: **MCP the protocol scales; your server scales like whatever it wraps.** The protocol adds negligible overhead — it's JSON-RPC over HTTP.

**C4. Can multiple clients hit the same server at once? (30 students, one server?)**

Yes — that's our classroom setup. The server is async and runs each blocking SSH call in a worker thread (`anyio.to_thread.run_sync`), so one student's slow call doesn't block others. The real contention in the lab is the **router**, not the server: many simultaneous `configure_interface` calls against one Router1 will collide at the device. That's why config exercises assign per-student interface/loopback ranges. Read-only calls are safe to overlap.

**C5. How would I make this server highly available?**

Run several instances behind a load balancer; keep them stateless where possible (or use sticky sessions / a shared session store for the stateful bits); pool or externalize the backend connections. Nothing MCP-specific — it's standard web-service HA. The one MCP wrinkle: session affinity, because Streamable HTTP sessions are per-connection.

**C6. Server composition — can a server aggregate other servers?**

Yes, this is a real pattern: a "gateway" MCP server that is itself a client to several downstream servers, presenting them as one. Useful for centralizing auth, policy, and audit across many backend servers. Out of scope for the lab, but the honest answer to "how do big orgs manage 50 servers" — a gateway plus the MCP Registry for discovery.

---

## D. Auth and security

**D1. How does authentication actually work here?**

MCP doesn't invent auth — remote servers use ordinary HTTP auth. Ours checks `Authorization: Bearer <token>` on every request to `/mcp` (constant-time compare), returns 401 with a hint otherwise. The health check `GET /` is intentionally open. The client sends the header from `librechat.yaml` (`headers:`), Inspector from its Bearer Token field.

**D2. Is a bearer token enough for production?**

For a shared lab, yes. For production, the spec supports **OAuth 2.1** (PKCE, dynamic client registration, token refresh, scopes) — LibreChat implements it fully. Use OAuth when you need per-user identity, scoped permissions, token expiry/revocation, or integration with an existing IdP (Entra, Okta). Bearer tokens are fine for service-to-service with a secret manager and rotation.

**D3. The router password is hardcoded/in the environment. Isn't that bad?**

In the lab, the credentials are on your handout — no secret to protect. The *pattern* the code demonstrates is correct: credentials come from environment variables (`ROUTER_*`), never from client input, and the model never sees them. In production those env vars come from a secret manager (Vault, cloud secret store), and you rotate them. Section 9 exercise 4 in the guide has students rotate the MCP token to feel this.

**D4. Can the AI do something destructive I didn't intend?**

Only what your tools allow — that's the entire design. The server is the boundary: read-only vs destructive annotations, the exact-command allowlist (the model literally cannot run `show running-config` or pipe to tftp), input validation on every argument, the elicitation confirmation gate, and pre-change snapshots for rollback. The model is a user with exactly the permissions your tools grant. Repeat the mantra: **the server is the security boundary; the model is a user.**

**D5. What about prompt injection — a malicious instruction in tool output?**

Real threat class. If a tool returns attacker-controlled text (e.g. a config field someone else set), the model reads it and could be steered. Defenses in our design: tools do narrowly-scoped things (no "run arbitrary command"), destructive actions are gated, and outputs are data the model summarizes rather than instructions it obeys. Production adds output sanitization and keeps high-privilege tools behind human approval. Good question to acknowledge honestly — MCP doesn't magically solve it; tool design does.

**D6. Why does elicitation refuse to handle secrets?**

Spec rule: elicitation must never be used to collect passwords/API keys. Reason: the elicited value passes through the client and model context — exactly where a secret must not go. Elicitation is for confirmations, choices, and non-sensitive parameters. Credentials belong in the server's environment/secret store, never in a protocol round-trip.

---

## E. Resources, prompts, notifications, elicitation

**E1. Why can't I see resources/prompts in LibreChat?**

Because LibreChat v0.8.7's client doesn't implement them — `resources/list` and `prompts/list` exist in its code but are never called. Not your config. This is capability reality, not a bug you can fix. Explore them in Inspector (Labs 4–5) or Claude Code (take-home). The capability matrix (Student Guide §8) is the reference.

**E2. Tools vs resources — when do I use which?**

Control point decides:

- **Tool** = the *model* decides to act ("call get_interfaces"). For actions and computed answers.
- **Resource** = the *application/user* decides to load context ("attach the running config"). For data you want available without the model choosing to fetch it.

Our `router://running-config` is a resource precisely so a human loads it deliberately, while the model can't pull full config on its own initiative (it's not an allowed command). Same data, different trust decision.

**E3. What's a prompt, versus the LibreChat "Prompts" feature?**

An MCP prompt is a server-provided, parameterized template the user invokes (our `troubleshoot_interface`). LibreChat's built-in "Prompts" is an unrelated local prompt library — pure naming collision. In Claude Code, MCP prompts appear as slash commands.

**E4. What is sampling, and why didn't we use it?**

Sampling lets the *server* ask the *client* to run an LLM completion — so the server can use AI without its own API key. Rare in current clients (LibreChat: no; Inspector: mock only), so it's lecture-only here. Real use: a server that needs to summarize or classify something mid-tool-call, borrowing the client's model.

**E5. How do subscriptions/notifications work?**

The client subscribes to a resource; the server pushes `notifications/resources/updated` when it changes. Our server notifies subscribers of `router://running-config` after any config write. Plus `tools/list_changed` when the toolset changes. These are the "server speaks first" half of the protocol — everything else is client-initiated request/response.

---

## F. The model and tool-calling

**F1. Which model are we using, and does the choice matter?**

`anthropic/claude-haiku-4.5` via OpenRouter. The choice matters a lot: the entire workshop depends on the model reliably emitting tool calls, and not every model does that well. The old default (`llama-3-70b`) was both delisted from OpenRouter and mediocre at tool use. Any current tool-calling-capable model works; verify before relying on it.

**F2. Does OpenRouter/the model see my router or credentials?**

No. The model sees: your message, the tool *descriptions and schemas*, and tool *results* (the command output). It never sees the SSH connection, the router credentials, or the bearer token. It emits a request; LibreChat and the server do the privileged work.

**F3. Why did the model not call my tool / call the wrong one?**

Almost always the description. If two tools sound similar, or a description doesn't say *when* to use the tool, the model guesses. Fix the docstring. Secondary causes: the server isn't toggled on in that conversation's MCP menu; or the model genuinely lacks a needed value (give it in the prompt).

**F4. Can I force the model to call a specific tool?**

Not through MCP — tool choice is the model's. You influence it via descriptions and your prompt. (Some APIs support forced tool choice, but that's an application-layer feature, not part of MCP.)

**F5. Is the model deterministic? Will the same prompt always call the same tool?**

No — LLMs are probabilistic. Usually consistent for clear prompts, but not guaranteed. This is why validation lives in the server, not in trusting the model to behave.

---

## G. Protocol mechanics

**G1. What is JSON-RPC and why does MCP use it?**

A simple, mature RPC format: requests (with `id`), responses (matching `id`), notifications (no `id`). MCP is essentially a set of JSON-RPC methods (`initialize`, `tools/list`, `tools/call`, …) over a transport. You read the actual messages in Lab 1.

**G2. What happens in `initialize`?**

Client and server exchange protocol versions and **capabilities**, and the server sends its instructions. This is capability negotiation — each side then only uses features the other declared. It's why the same `configure_interface` gets a confirmation dialog in Inspector but a warning in LibreChat: they declared different capabilities here.

**G3. Request vs notification?**

Requests carry an `id` and expect exactly one matching response. Notifications have no `id` and get no reply — fire-and-forget, either direction (progress, list_changed, resources/updated). `notifications/initialized` is a notification sent by the client after initialize.

**G4. What protocol version are we on?**

The current spec revision is 2025-11-25; the SDK negotiates the version during initialize. Version is exchanged so client and server can agree on a mutually supported feature set.

**G5. How are errors represented?**

Two distinct things. **Protocol errors** (bad method, auth failure) are JSON-RPC errors. **Tool errors** (SSH failed, command rejected) are *successful* responses with `isError` / error text in the content — deliberately, so the model can read and react to them. Our tools return error strings, never raise. Lab 1 C3 makes this concrete.

---

## H. Production and real-world use

**H1. Is this how MCP is used in production, or just a teaching toy?**

The *shape* is real: a network service exposing tools over Streamable HTTP with auth is exactly a production MCP server. What a lab omits: secret management, connection pooling, rate limiting, observability, HA, and usually OAuth. The mental model transfers directly.

**H2. Who consumes MCP servers in the real world?**

Today, mostly IDE-class clients (Claude Code, VS Code/Copilot, Cursor) and custom in-house agents built on the SDKs — these consume the deep primitives. Chat products consume tools. When your company writes its own agent, *you* choose which capabilities the client implements, and that's where subscriptions feed dashboards, elicitation gates approvals, prompts encode runbooks.

**H3. What would I actually build with this at work?**

Anything with an API or CLI becomes tool-able: query monitoring, open/annotate tickets, check config compliance, run diagnostics, draft (gated) changes. The pattern that fits regulated/production infra: read-only and diagnostic tools freely available, change-making tools behind validation gates and human approval — precisely the guardrail stack in this lab.

**H4. How do teams manage many servers and access control?**

A gateway/aggregator server centralizes auth, policy, and audit across downstream servers; the MCP Registry handles discovery; OAuth scopes handle per-user permissions. For a regulated enterprise the important part is that every tool call is auditable and every change is gated and reversible — build that in, don't bolt it on.

**H5. What's the cost model?**

Two costs: the LLM tokens (every tool description and result passes through the model — more/verbose tools cost more per turn) and the infrastructure running your servers (ordinary compute). The protocol itself is free and light. Cost discipline = few sharp tools, concise results, and not attaching servers a conversation doesn't need.

---

## I. Troubleshooting patterns (the meta-answer)

**I1. General debugging order?**

Server terminal first, client logs second, browser last. The server's 401 log names the exact auth mistake; LibreChat's api log names the exact config gate; the browser only shows the symptom. And: **verify in Inspector before debugging in LibreChat** — Inspector talks to the server with nothing in between, so if it works there, the problem is client config.

**I2. "It worked in Inspector but not LibreChat."**

Classic, and expected. Different client, different capabilities and config. Check, in order: is the token set in LibreChat's `.env` (and did you *recreate*, not just restart, after editing it)? Is `mcpSettings.allowedAddresses` present (SSRF guard)? Did you reinitialize the server so LibreChat re-ran `tools/list`? All three bit us during setup this week.

**I3. Why "recreate" and not "restart"?**

`.env` is read when a container is **created**. `docker compose restart` reuses the existing container with its old environment. `.env` changes need `docker compose up -d --force-recreate api`. yaml changes are read at startup, so `restart` suffices for those.

---

## J. Ecosystem and what's next

**J1. Who created MCP? Is it open?**

Introduced by Anthropic (late 2024), open specification and open-source SDKs, now with broad multi-vendor adoption. Spec and SDKs: modelcontextprotocol.io and github.com/modelcontextprotocol. It is not tied to one model or vendor — that's the point.

**J2. What languages have SDKs?**

Python, TypeScript, Java, Kotlin, C#, Go, Swift, Ruby, PHP, Rust (first-party set has grown well beyond the original two). We used the Python SDK's FastMCP.

**J3. How do I find existing servers instead of building one?**

The MCP Registry lists published servers; many vendors ship official ones (databases, SaaS tools, cloud providers). The build-vs-adopt question is real — often a server already exists for a common system.

**J4. Where do I go deeper after today?**

Spec (modelcontextprotocol.io) for the protocol; the SDK repos for building; the take-home assignment to consume our server from Claude Code; and the Server Code Walkthrough to understand every design choice in the server you ran. Next build: pick something at work with an API, expose three read-only tools, connect it to Claude Code.

---

## Quick-fire answers (rapid-fire round)

- **Does MCP need the internet?** No — stdio and local HTTP work fully offline; only the *model* (OpenRouter) needs egress in our setup.
- **Can I use MCP without an LLM?** Yes — Inspector does. MCP is a client-server protocol; the AI is one kind of client.
- **Is MCP just OpenAI function-calling?** No — function-calling is one model's API feature; MCP is a vendor-neutral protocol standardizing tools *and* resources, prompts, notifications, elicitation across clients and servers.
- **Can two clients share one session?** No — a session is per client connection. Two clients = two sessions.
- **Does the server store conversation state?** No — the server is stateless about conversations; it holds MCP session state (subscriptions, etc.), while the conversation lives in the client/model.
- **Can a tool return an image/file?** Yes — results support text, images, and embedded resources (blobs). LibreChat renders embedded resources returned in tool results.
- **What if the server crashes mid-call?** The client sees a transport/connection error; it can reconnect and reinitialize. Our tools are stateless per call, so a retry is safe.
- **Can I version my tools?** Not in the protocol — version via names/descriptions or separate servers. Server and protocol versions are exchanged at initialize.
