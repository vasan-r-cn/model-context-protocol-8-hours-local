# MCP Inspector Showcase Checklist

What to demonstrate in each MCP Inspector tab against the workshop server
(`http://<server>:8000/mcp`, Streamable HTTP, header `Authorization: Bearer cisco-mcp-workshop`).

Launch: `npx @modelcontextprotocol/inspector`, open the token URL it prints, set transport to
**Streamable HTTP**, paste the URL and the bearer token header, click **Connect**.

Why Inspector matters in this workshop: LibreChat only consumes **tools**. Resources, resource
templates, prompts, subscriptions, notifications, and elicitation are invisible there — Inspector
is where students see the rest of the protocol.

---

## 1. Connection pane (capability negotiation)

Showcase before touching any tab:

- **initialize handshake** — expand the server capabilities in the connection/History pane:
  - `tools.listChanged: true` — server may change its tool list at runtime
  - `resources.subscribe: true` and `resources.listChanged: true` — subscriptions supported
    (point out this required a server-side SDK workaround; see `main.py` bottom)
  - `prompts` capability present
- **Auth failure demo** — reconnect once with a wrong/missing bearer token → 401. Shows the
  auth middleware guarding `/mcp` while `GET /` health check stays open.
- **serverInfo + instructions** — the server self-describes as operating a live Cisco lab router.

## 2. Tools tab

All 7 tools with schemas generated from Python signatures + docstrings:

| Tool | What to show |
|------|--------------|
| `get_interfaces` | Plain call; `readOnlyHint: true` annotation visible in the listing |
| `get_router_info` | **Structured output** — returns a typed `RouterInfo` object, not just text |
| `dynamic_show` | Run `show ip route` (works), then `show running-config` (**rejected** — exact-match allowlist; error text lists allowed commands) |
| `snapshot_config` | Creates a timestamped snapshot file; feeds the `router://baseline` resource |
| `enable_config_tools` | Toggle `true`/`false` → watch **`tools/list_changed` notification** arrive and the tool list grow/shrink from 7 to 5 and back |
| `configure_interface` | Call it → **elicitation dialog pops up in Inspector** asking to confirm; accept and decline once each |
| `create_loopback` | Same elicitation gate; creates a loopback described `MCP_CREATED` |

### Exact inputs for the config tools

Neither tool takes raw IOS commands — both take simple parameters and the server builds the
config commands itself.

**`create_loopback`** — one parameter:

```json
{ "loopback_id": 101 }
```

Server pushes: `interface Loopback101` + `description MCP_CREATED` (no IP address).
The `MCP_CREATED` description is what `reset_lab.py` keys on for cleanup.

**`configure_interface`** — two parameters:

```json
{ "interface": "Loopback101", "ip_address": "192.168.101.1" }
```

Server pushes: `interface Loopback101` + `ip address 192.168.101.1 255.255.255.0` +
`no shutdown`. The /24 mask is hardcoded — pass a plain IP with **no** `/24` or mask.
A pre-change snapshot of the running config is taken automatically; its path appears in the
tool result.

**Safe demo order** (loopbacks on purpose — never target the real uplink interfaces):

1. `create_loopback` → `{ "loopback_id": 101 }`
2. `configure_interface` → `{ "interface": "Loopback101", "ip_address": "192.168.101.1" }`
3. Verify with `dynamic_show` → `show ip interface brief`

Also visible per call:

- **Progress notifications** — `dynamic_show` / config tools emit `ctx.report_progress`
  ("Running 'show …' on Router1…") — watch the notifications pane during a call.
- **Errors as results, not protocol errors** — enter a bad interface name; the error comes back
  as tool result text the LLM could read and retry on, not a JSON-RPC error.

## 3. Resources tab

3 concrete resources + 1 template (LibreChat never shows these):

- `router://interfaces` — live `show ip interface brief`
- `router://running-config` — live running config (the subscribable one)
- `router://baseline` — most recent snapshot (rollback anchor; empty-state message until
  `snapshot_config` has run once — show that ordering)
- **Resource template** `router://interfaces/{name}` — fill in `GigabitEthernet1` (or `Loopback55`)
  and read it; shows parameterized URIs

### Subscription + notification flow (the headline demo)

1. Open `router://running-config` and click **Subscribe**.
2. In the Tools tab, run `create_loopback` (config tools enabled), confirm the elicitation.
3. Watch the **`notifications/resources/updated`** message arrive for `router://running-config`.
4. Re-read the resource — the new loopback is in the config.

This is the full loop: change on the wire → server-side notify → client refresh.

## 4. Prompts tab

2 prompts (user-controlled templates — distinct from LibreChat's unrelated local "Prompts" feature):

- **`troubleshoot_interface`** — takes an `interface` argument; render it with `Loopback55` and
  show the generated step-by-step message that references the server's own tools and resources.
- **`audit_router_config`** — no arguments; renders an audit checklist that points at
  `router://running-config`.

Point out: prompts are *user-invoked*, tools are *model-invoked*, resources are *app-controlled* —
the three interaction models of MCP in one server.

## 5. Elicitation (cross-tab behavior)

- In Inspector: `configure_interface` / `create_loopback` trigger a confirmation dialog
  (schema-driven: a single `confirm` boolean). Demonstrate **accept**, **decline**, and **cancel**.
- Contrast with LibreChat: it advertises no elicitation capability, so the server detects that via
  `check_client_capability` and applies the change with a `WARNING:` prefix instead of blocking.
  Run the same tool from LibreChat afterward to show the degraded path — that split is the lesson.
- Mention the spec rule shown in the code: elicitation must never collect secrets/credentials.

## 6. Notifications summary (where to watch)

| Notification | Trigger |
|--------------|---------|
| `notifications/tools/list_changed` | `enable_config_tools` toggled |
| `notifications/resources/updated` | Config change while subscribed to `router://running-config` |
| Progress notifications | Any tool using `ctx.report_progress` |

---

## Runtime tool changes in the real world (talking points)

`enable_config_tools` demos the mechanism; production servers use the same wire protocol with
different triggers. The protocol side never changes: server updates its tool registry → sends
`notifications/tools/list_changed` → client re-calls `tools/list` → the LLM sees the new toolset
on its next turn.

Common real-world triggers:

1. **Auth / RBAC (most common)** — user identity from the OAuth token decides the tool list: a
   read-only analyst gets `get_*` tools, an admin also gets write tools. The workshop's
   `enable_config_tools` is the honor-system version of this — a real server derives it from token
   scopes/claims rather than exposing a callable toggle.
2. **Feature flags / remote config** — server watches a flag service (LaunchDarkly, Unleash, an
   internal config API); flipping a flag adds/removes tools across all sessions. Useful for staged
   rollout of risky tools.
3. **Backend discovery** — the server proxies downstream systems and generates tools as they
   appear: a network MCP server that grows a toolset per router found in inventory, or an MCP
   gateway aggregating other servers as they connect/disconnect.
4. **Session state / workflow stage** — tools unlock as a workflow progresses (`connect_database`
   first; `run_query` appears after it succeeds). Cuts context bloat and stops the LLM calling
   tools that cannot work yet.
5. **Plugin / hot reload** — tool modules loaded from disk or a registry at runtime; drop in a new
   plugin and its tools appear without a server restart.
6. **Maintenance / circuit breaker** — backend down or change-freeze window → hide write tools
   instead of returning errors; the LLM cannot call what it cannot see.

Implementation notes (Python SDK):

- The workshop pattern (`mcp.add_tool` / `remove_tool` + notify) is **global** — it changes the
  list for every connected session.
- Per-user visibility is usually better done in the `list_tools` handler: keep the registry full
  and filter the response per session identity. No notification needed — each client sees its own
  slice at connect time.
- Client support varies: Inspector re-lists on the notification, but some clients ignore
  `list_changed` and only list at connect. Design so a hidden tool that gets called anyway still
  returns a proper authorization error — **hiding is UX, authorization is enforcement**. Never
  rely on visibility alone for security.

---

## The MCP Registry (server discovery ecosystem)

Two different "registry" concepts — keep them apart in the session:

| Concept | Scope | What it holds |
|---------|-------|---------------|
| **Tool registry** (previous section) | Inside one server | Which tools that server exposes right now |
| **MCP Registry** | Ecosystem-wide | Which MCP *servers* exist and how to install/reach them |

### What the official MCP Registry is

- Open catalog + API at `registry.modelcontextprotocol.io` — the community-run "app store index"
  for MCP servers (launched as a preview in September 2025, open source).
- Each entry is a `server.json`: server name, description, version, transport (stdio /
  Streamable HTTP), install packages (npm, PyPI, Docker, NuGet) and/or remote endpoint URL,
  and required configuration/environment variables.
- Namespaced identities, e.g. `io.github.<user>/<server>` — GitHub-auth namespaces or
  DNS-verified reverse-domain names for company namespaces.
- Publishing: `mcp-publisher` CLI → validate `server.json` → authenticate (GitHub or DNS) →
  publish. Versioned; entries can be deprecated/delisted.
- It is **metadata only** — the registry hosts no code and does not proxy traffic. Clients still
  fetch packages from npm/PyPI/etc. or connect directly to the remote URL.

### Sub-registries and clients

The official registry is designed as an upstream source: vendors run **sub-registries** that
mirror/curate it and add their own vetting (e.g. the GitHub MCP Registry; client apps like
Claude, Cursor, and VS Code surface curated server directories in-product). Enterprises can run a
private internal registry with only approved servers — same API shape, curated contents.

### Why it matters for this workshop's story

- Discovery: instead of hand-editing `librechat.reference.yaml` with a URL + token, a registry
  lets a client find the server by name and read its transport/config requirements from metadata.
- Trust boundary talking point: a registry entry is a claim, not an audit — installing a server
  from a registry still grants it whatever its tools can do. Enterprise pattern is a curated
  private registry + the per-server auth this lab demos (bearer token today, OAuth in production).
- Our workshop server would publish as a **remote** Streamable HTTP entry (endpoint URL +
  "requires bearer token" in the config metadata) — students can map every `server.json` field to
  something they configured by hand in Lab 1.

---

## Suggested 10-minute run order

1. Connect → inspect capabilities in initialize response (1 min)
2. Wrong-token reconnect → 401 → reconnect correctly (1 min)
3. Tools: `get_interfaces`, `get_router_info` (structured), `dynamic_show` allow + reject (3 min)
4. `enable_config_tools true` → `tools/list_changed` (1 min)
5. Subscribe to `router://running-config` → `create_loopback` with elicitation accept →
   `resources/updated` → re-read config (3 min)
6. Prompts: render `troubleshoot_interface` for the new loopback (1 min)

Cleanup between cohorts: `python3 reset_lab.py --apply` (removes `MCP_CREATED` loopbacks).
