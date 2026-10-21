# Run and Read the Server

**Category:** 04 · Build an MCP Server · **Duration:** 12 min · **Runs on:** `linuxdesktop64` · **Targets:** `sdceightkv24`

**Devices in play:** `sdceightkv24` (DR SD-WAN edge).

## Introduction

You have driven this server from Inspector, from curl, and from a model. Now open the hood. You are about to add a tool to it (exercise 4.2), so first you need a map: where the inventory lives, what a tool looks like, how auth is applied, and why every device call is bounced onto a worker thread.

The whole server is one file plus a data file: `code/server/app/main.py` (the decorators) and `code/server/inventory.yaml` (the devices). That is the point of FastMCP — **decorators in, protocol out**. You write a Python function; the SDK turns its signature and docstring into a JSON-RPC tool with a schema.

## What You'll Learn

- The shape of a FastMCP server: decorators in, protocol out
- Where the device inventory lives and why it is data, not code
- How bearer auth is applied, and what an unauthenticated request gets back
- Why every router call goes through a worker thread

## Before You Start

- Exercise 3.3 complete

## Architecture Overview

| Landmark | File · lines | What it is |
|---|---|---|
| **Server object** | `main.py:72` `FastMCP("cisco-router-mcp", instructions=...)` | the server + its model-facing `instructions` |
| **Inventory (data)** | `inventory.yaml` + `app/inventory.py` | 11 devices, roles, default device — *data, not code* |
| **A read-only tool** | `main.py:216` `get_interfaces` | `@mcp.tool(... readOnlyHint=True)` |
| **A config tool** | `main.py:316` `configure_interface` | `destructiveHint=True`, role-gated |
| **Auth middleware** | `main.py` `BearerAuthMiddleware` | guards `/mcp`; leaves `GET /` open |
| **SSH helpers** | `main.py:94–123` `run_show`/`run_config` | blocking Netmiko, run in a worker thread |

## Setup

### Step 1 — run it and prove it

```bash
cd code/server && ./run.sh      # first run builds the venv
./smoke_test.sh                 # verified reference: 17 passed, 0 failed
```

`run.sh` sources `.env` if present, (re)builds `.venv`, and `exec`s uvicorn on `0.0.0.0:8000`.

## Exercises

### Part 1 — the inventory is data, not code (4 min)

Open `code/server/inventory.yaml`. Each device has a `role`. Then open `app/inventory.py` and find:

```python
WRITABLE_ROLES = frozenset({"prod-rep"})      # production deliberately absent
PROMOTABLE_ROLES = frozenset({"production"})
```

**A1.** The default device is `sdceightkv24`, role `prod-rep`. `inventory.py` *refuses to load* if the default device's role is not in `WRITABLE_ROLES`. Why is that a safety property and not just a sanity check?

> Answer to check yourself: a tool call that omits `device` falls back to the default. If the default could ever be a production device, a careless call could change production. Refusing to boot with an unsafe default makes "omitted device is safe" a guarantee, not a hope.

**A2.** List the four writable devices. (Hint: the four with role `prod-rep`.)

### Part 2 — read one tool top to bottom (4 min)

Read `get_interfaces` (`main.py:216`):

```python
@mcp.tool(annotations=types.ToolAnnotations(readOnlyHint=True))
async def get_interfaces(ctx: Context, device: DeviceName = DEFAULT_DEVICE) -> str:
    """Get a device's interfaces and their status (show ip interface brief)."""
    await ctx.report_progress(0, 1, f"Connecting to {device} over SSH...")
    output = await run_show("show ip interface brief", device)
    ...
```

Every line is doing a named job:

- `@mcp.tool(... readOnlyHint=True)` → registers it *and* tells clients it changes nothing.
- the **docstring** → becomes the tool *description the model reads*. This is prompt engineering, not a comment.
- `device: DeviceName` → `DeviceName` is a `Literal` of the inventory, so the schema's `device` is an **enum** of real devices.
- `= DEFAULT_DEVICE` → omit it and you safely hit DR.
- `await run_show(...)` → the SSH call, bounced to a thread (Part 3).

### Part 3 — why a worker thread (2 min)

Read `run_show` (`main.py:111`):

```python
async def run_show(command, device=inv.DEFAULT_DEVICE):
    if not inv.get(device).reachable:
        raise RuntimeError(...)
    return await anyio.to_thread.run_sync(_run_show, command, device)
```

**B1.** Netmiko's SSH is **blocking**. The server is async. What would happen to every *other* in-flight request if this blocked the event loop instead of going to a thread?

> Answer to check yourself: the whole server would freeze until the SSH call returned — one slow device would stall everyone. `anyio.to_thread.run_sync` keeps the event loop free.

### Part 4 — auth (2 min)

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8000/        # 200 (open health check)
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://localhost:8000/mcp -d '{}'   # 401
```

**C1.** `/` is open; `/mcp` without a bearer token is 401. Why keep the health check unauthenticated?

**Reflection Questions**

1. The inventory is YAML, not Python. What does "data, not code" buy you when a pod has different IPs?
2. The docstring is the tool description. What does that mean for how carefully you write it?
3. `readOnlyHint` and `destructiveHint` are *hints*. Who enforces that a read-only tool really is read-only — the hint, or something else? (You'll answer this hard in Lab 4.)

## Verify

**Success Criteria**

- `./run.sh` starts the server and `./smoke_test.sh` passes
- You can point at the inventory, a read-only tool, a config tool, and the auth middleware
- You can explain what `readOnlyHint` and `destructiveHint` are for

**Done when:** the smoke test passes and you can point — by file and rough line — at the four landmarks in the table above.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `./run.sh` fails building the venv | PyPI blocked, or a stale `.venv` from a moved dir | delete `.venv`, re-run; `run.sh` rebuilds |
| `smoke_test.sh` FAIL on step 1 | server not up / wrong port | confirm `run.sh` is running on `:8000` |
| `/mcp` returns 200 without a token | auth middleware regressed | check `BearerAuthMiddleware` is mounted; re-run smoke test |
| tool call errors "no management address" | device unreachable from this pod | expected off-network; see exercise 1.1 check 3 |

## Quick Reference

- Server: `FastMCP("cisco-router-mcp", instructions=...)`, `main.py:72`.
- Inventory: `inventory.yaml` (data) + `app/inventory.py`; `WRITABLE_ROLES={"prod-rep"}`.
- Read-only tool: `@mcp.tool(... readOnlyHint=True)`; docstring = model-facing description.
- Device I/O: always through `run_show`/`run_config` (worker thread). Auth: `/mcp` bearer-guarded, `/` open.

---

**Source material:** `code/server/app/main.py`, `code/server/app/inventory.py`, `code/server/inventory.yaml`
