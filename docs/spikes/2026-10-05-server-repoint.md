# Phase 1 — server re-pointed onto the new topology

**Date:** 5 Oct 2026 · **Result: GREEN**, with the lab devices still unreachable
from the build host. Everything below was verified without touching a device.

## What changed

The server no longer knows about a router. It knows about an **inventory**, and
the inventory carries the safety model.

| Before | After |
|---|---|
| `ROUTER_CONFIG` — one hardcoded IOS router | `inventory.yaml` → `app/inventory.py`, 9 devices across DC / DR / branches / legacy |
| `run_show(cmd)` | `run_show(cmd, device)`, Netmiko platform from the inventory (`cisco_nxos` / `cisco_xe`) |
| tools act on "Router1" | every device-touching tool takes `device`, typed as an **enum of real device names** |
| nothing stops a config write | config tools call `inv.may_write_to(device)` first |
| `router://…` resources | `device://{device}/running-config`, `device://{device}/interfaces/{name}` templates |
| — | new read-only `list_devices` tool, so a model asking about "DC" can find the device names |

## The blast-radius rule

Stated once, in `app/inventory.py`:

```python
WRITABLE_ROLES  = frozenset({"prod-rep"})     # production is deliberately absent
PROMOTABLE_ROLES = frozenset({"production"})  # only change_workflow asks this
```

`default_device: sdceightkv24` (DR). The inventory **refuses to load** if the
default device is not writable — so a tool call that omits `device` cannot be
pointed at production by a later edit to a data file.

Role is checked **before** reachability, so a production device is refused for
the right reason whether or not it has a management address yet:

```
create_loopback device=cisconexusnkv12  →  "Refusing to configure
'cisconexusnkv12': it is a production device in DC. Configuration changes are
only applied to production-representative devices (…). To change production,
validate the change on a production-representative device first, then promote."
```

Observed over the wire through fast-agent: **33 ms, no SSH attempted.**

## Verification

```bash
cd code/server
./run.sh                              # rebuilds .venv if it is unusable
./smoke_test.sh http://127.0.0.1:8099 # 17 passed, 0 failed
.venv/bin/python -m pytest            # 29 passed
```

`tests/` runs the **real protocol surface** over the SDK's in-memory transport —
no uvicorn, no network, no device — so it is a usable CI gate. It asserts:

- production is never writable, and no config tool reaches it;
- a call that **omits** `device` never lands on production;
- `device` is an enum of real device names, defaulting to the safe device;
- read-only tools carry `readOnlyHint`, config tools carry `destructiveHint`;
- `dynamic_show` is still exact-match (`show run | redirect …` and friends rejected).

**The suite was mutation-tested.** Adding `"production"` to `WRITABLE_ROLES`
turns six tests red; reverting turns them green. A safety test that cannot fail
is decoration.

## Two traps found, both fixed

1. **`pytest-asyncio` cannot tear down the SDK's in-memory session.** It creates
   the fixture in one task and exits the anyio cancel scope in another:
   `RuntimeError: Attempted to exit cancel scope in a different task`. Tests pass
   and *then* error. Use anyio's own pytest plugin (`pytestmark =
   pytest.mark.anyio`, `anyio_backend` fixture) — `requirements-dev.txt` pins
   `trio` for it and does **not** install pytest-asyncio.
2. **A venv breaks silently when its directory is renamed.** This repo was
   `mcp-one-day-worksop`; `.venv/bin/pip` still carried that shebang and
   installed into a path that no longer existed, reporting success. `run.sh` now
   probes the venv and rebuilds it, and prefers Python 3.12. Worth repeating in
   pre-flight: the lab image's prebuilt venvs must be built at their final path.

## Still blocked on lab access

**Which device is used where is written up in
[`docs/lab-device-map.md`](../lab-device-map.md)** — per-site roles, a per-lab
device table, seat scoping, and the facts still to be confirmed.

**Update (6 Oct):** resolved. `code/server/custom-underlay.yaml` (the sandbox
topology spec) supplied every device name, management address and per-platform
credential; `inventory.yaml` is now generated from it, with 11 devices. Two
diagram labels that were unreadable turned out to be `cisconexusnkv13` and
`cisconexusnkv41`, and the whole `ciscoexrusnkv*` family was a misreading of
`cisconexusnkv*`. Credentials differ per platform, so the inventory carries them
per device rather than globally.

What remains is a routing question, not a data question: the build host has no
route to `192.168.116.0/24`. Run `./scripts/sanity_check.sh` on a participant
desktop to settle it.
