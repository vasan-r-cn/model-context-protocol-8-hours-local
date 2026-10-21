# Test Without a Device

**Category:** 04 · Build an MCP Server · **Duration:** 15 min · **Runs on:** `linuxdesktop64` · **Targets:** none — this exercise needs no network

**Devices in play:** None — device-free tests over the SDK in-memory transport. No network device is reached.

## Introduction

Your server's most important promise is a *negative* one: a tool call **cannot** change a production device. How do you test a promise like that without a lab full of routers in CI?

The answer is the SDK's **in-memory transport**: it connects a real MCP client to your real server in the same process — no uvicorn, no network — so your tests exercise the true protocol surface (schemas, annotations, tool results) at unit-test speed. Then you **monkeypatch the SSH layer** so a test records what *would* have been sent to a device. If a test ever finds a recorded call to a production device, the blast-radius rule is broken and the test goes red.

The rule you'll internalize: **a safety rule that cannot fail a test is decoration.** You'll prove your test can fail by breaking the rule it guards — then revert.

## What You'll Learn

- How to exercise the real protocol surface with the SDK's in-memory transport
- How to monkeypatch device I/O so a test never opens an SSH session
- Why a safety rule that cannot fail a test is decoration
- What belongs in CI versus what needs the lab

## Before You Start

- Exercise 4.2 complete

## Architecture Overview

| Fixture | File | What it gives you |
|---|---|---|
| `session` | `tests/conftest.py` | a connected MCP client↔server, **in memory** (no network) |
| `no_ssh` | `tests/conftest.py` | monkeypatches `run_show`/`run_config`; records attempted device I/O |
| `anyio_backend` | `tests/conftest.py` | runs async tests on asyncio (anyio plugin, **not** pytest-asyncio) |

```text
test ---> session (real MCP client) ---> your server (real) ---> no_ssh (fake SSH, records calls)
                        no uvicorn, no router, no network
```

## Setup

### Step 1 — run the suite with every device unreachable

```bash
cd code/server
.venv/bin/python -m pytest        # device-free; reference: ~31 passed
```

It passes with no lab network because the `no_ssh` fixture replaces the SSH layer entirely.

> Why anyio, not pytest-asyncio: `requirements-dev.txt` pins the **anyio** plugin on purpose — pytest-asyncio can't tear down the SDK's in-memory cancel scope cleanly. Don't swap it.

## Exercises

### Part 1 — read how the trap is set (4 min)

Open `tests/conftest.py`. The `no_ssh` fixture:

```python
async def fake_show(command, device=server_main.DEFAULT_DEVICE):
    calls.append(("show", device, command))
    return f"<fake output of {command!r} from {device}>"
...
monkeypatch.setattr(server_main, "run_show", fake_show)
monkeypatch.setattr(server_main, "run_config", fake_config)
return calls
```

**A1.** The fake doesn't talk to a device — it *records* `(kind, device, command)`. How does a test use that list to prove a config tool never reached production?

> Answer to check yourself: after calling the tool it asserts `no_ssh == []` (nothing was sent) or that no recorded `device` is in the production set. A recorded production call = a broken rule = a red test.

Now read `tests/test_safety.py::TestConfigToolsRefuse`:

```python
result = await session.call_tool(tool, _args(tool, device))
assert "Refusing to configure" in _text(result)
assert no_ssh == [], f"{tool} reached {device}: {no_ssh}"
```

### Part 2 — write two tests (7 min)

Add these to `tests/test_safety.py` (or a new `tests/test_mine.py`). At least one must assert a **safety** rule.

Test 1 — your new tool is annotated read-only:

```python
async def test_ping_tool_is_read_only(session):
    tools = {t.name: t for t in (await session.list_tools()).tools}
    assert tools["ping_from_device"].annotations.readOnlyHint is True
```

Test 2 — a safety rule: a read-only tool never triggers a *config* write:

```python
async def test_ping_never_writes(session, no_ssh):
    await session.call_tool("ping_from_device", {"target": "10.2.0.1", "device": "sdceightkv24"})
    assert all(kind != "config" for kind, _, _ in no_ssh)
```

```bash
.venv/bin/python -m pytest -q
```

**Checkpoint 1:** both new tests pass, device-free.

### Part 3 — prove the test can fail (4 min)

A test that can't fail guards nothing. Temporarily break the rule `test_production_is_never_writable` guards — add `"production"` to `WRITABLE_ROLES` in `inventory.py`:

```python
WRITABLE_ROLES = frozenset({"prod-rep", "production"})   # TEMPORARY — will revert
```

```bash
.venv/bin/python -m pytest -q
```

**Checkpoint 2:** several tests go **red** (the recorded blast-radius suite catches it). Now **revert** the line and confirm green again.

> This is the mutation test from the build log: adding `"production"` turns six tests red. If it *didn't*, the tests would be decoration.

**Reflection Questions**

1. The suite needs no device. Which of your server's behaviours *can't* be tested this way, and must wait for the lab?
2. Why assert `no_ssh == []` (nothing sent) rather than just checking the tool's return string?
3. You proved the test fails when the rule breaks. Why is that step not optional?

## Verify

**Success Criteria**

- `pytest -q` is green with every device unreachable
- You wrote two tests, at least one asserting a safety rule
- You proved your test can fail by breaking the rule it guards, then reverting

**Done when:** your two tests pass device-free, you watched the suite go red on a broken `WRITABLE_ROLES`, and it's green again after revert.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `pytest` errors on teardown (cancel scope) | pytest-asyncio installed instead of anyio plugin | use `requirements-dev.txt` as pinned; don't swap the plugin |
| test "reaches a device" / hangs | you didn't request the `no_ssh` fixture | add `no_ssh` to the test's arguments |
| `KeyError: 'ping_from_device'` | tool not added in 4.2, or server import stale | complete 4.2; re-run from `code/server` |
| mutation didn't turn anything red | you edited the wrong file/line | edit `WRITABLE_ROLES` in `app/inventory.py`; re-run |
| suite green but you expected a device call | that's the point — `no_ssh` fakes all I/O | assert on the recorded `calls`, not on real output |

## Quick Reference

```bash
cd code/server
.venv/bin/python -m pytest          # ~31 passed, device-free
```

- `session` fixture = real MCP client↔server **in memory**.
- `no_ssh` fixture = fake SSH that **records** attempted device I/O.
- Prove a safety test fails: add `"production"` to `WRITABLE_ROLES` → red → revert.
- CI-safe checks: pytest, blast radius, allowlist. Needs-lab: real device output, elicitation against a reachable device.

---

**Source material:** `code/server/tests/`, `code/server/requirements-dev.txt` (anyio plugin — not pytest-asyncio)
