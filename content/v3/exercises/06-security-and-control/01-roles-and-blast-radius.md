# Roles & Blast Radius

**Category:** 06 · MCP Security & Control · **Duration:** 12 min · **Runs on:** `linuxdesktop64` · **Targets:** `sdceightkv24` (allowed) vs `sdceightkv11` (refused)

**Devices in play:** `sdceightkv24` (DR, writable) vs `sdceightkv11` and `cisconexusnkv12` (DC production — writes refused).

## Introduction

A server protects a production network in two very different ways, and confusing them is the most common MCP security mistake. This exercise makes the distinction concrete:

- **Hiding** a tool — not showing it in `tools/list` — is *UX*. It shapes what a model is likely to try.
- **Refusing** a call — enforcing a rule when the tool actually runs — is *authorization*. It is what actually protects the device.

In this server, hiding is done by toggling the config tools on and off (`enable_config_tools`), and authorization is done by the **inventory's role model**: `WRITABLE_ROLES = {"prod-rep"}`, production deliberately absent. You will watch a write to a DR device succeed and the *same* write to a DC (production) device be refused **before any SSH is attempted**.

> **Scope note.** The strongest form of hiding — a per-*token* role so a read-only user never even sees the destructive tools — is a later hardening lab. This server has a single bearer token; its authorization is enforced by **device role**, which is the part that actually protects production. That is what you exercise here.

## What You'll Learn

- The difference between hiding a tool and refusing a call
- How the safety rule is stated once, in the inventory, not in each tool
- Why role is checked before reachability
- Why "shorter tools/list" is UX and "refused with no SSH" is enforcement

## Before You Start

- Exercise 4.4 complete

## Architecture Overview

| Mechanism | Where | Kind |
|---|---|---|
| `enable_config_tools(false)` → `tools/list_changed` | `main.py:390` | **hiding** (UX) — removes config tools from discovery |
| `may_write_to(device)` → `"Refusing to configure..."` | `inventory.py:149` | **authorization** (enforcement) — role checked first |
| `WRITABLE_ROLES = {"prod-rep"}` | `inventory.py` | the rule, stated **once** |

```text
write to sdceightkv24 (prod-rep)  -> may_write_to -> allowed -> SSH -> change
write to sdceightkv11 (production) -> may_write_to -> REFUSED (no SSH) -> device untouched
```

## Setup

### Step 1 — server up, config tools on

```bash
cd code/server && ./run.sh
```

Connect Inspector (or keep fast-agent handy). Config tools are enabled at startup.

## Exercises

### Part 1 — hiding is UX (3 min)

In Inspector, note `tools/list` includes `configure_interface` and `create_loopback`. Now call `enable_config_tools` with `enabled: false` and re-list.

**A1.** The two destructive tools disappear from `tools/list` (the server fired `tools/list_changed`). Did disabling them change anything on any device?

> Answer to check yourself: no. Hiding changes *discovery*, not state. It makes a model less likely to try a destructive tool — it does not stop one that tries anyway. Re-enable them (`enabled: true`) for Part 2.

### Part 2 — authorization is enforcement (5 min)

With config tools enabled, do the same write to two devices.

Allowed (DR, `prod-rep`):

```text
create_loopback(loopback_id=901, device=sdceightkv24)
```

Refused (DC, `production`):

```text
create_loopback(loopback_id=901, device=sdceightkv11)
```

**B1.** The DC call returns, as a tool *result*:

```text
Refusing to configure 'sdceightkv11': it is a production device in DC.
Configuration changes are only applied to production-representative devices
(sdceightkv24, cisconexusnkv30, cisconexusnkv41, cisconexusnkv52). To change
production, validate the change on a production-representative device first,
then promote it.
```

Verified timing from the build log: this refusal returns in **~33 ms with no SSH attempted** — the role is checked *before* reachability, so a production device is refused for the right reason even if it has no management address yet.

**Checkpoint 1:** the DC write is refused as a tool result; the DR write is accepted (or, off-network, fails only at the SSH step — which still proves the *role* gate let it through).

> [SCREENSHOT 1: Inspector — create_loopback on sdceightkv11 returning the "Refusing to configure" result] <!-- captured at dry-run -->

### Part 3 — prove the device is unchanged (4 min)

The refusal says no SSH happened — prove it. `snapshot_config` is read-only, so you may read production. Snapshot `sdceightkv11` before and after the refused write and diff:

```text
snapshot_config(device=sdceightkv11)      # before (also: the refused write)
snapshot_config(device=sdceightkv11)      # after
```

Diff the two files under `code/server/snapshots/` — they are identical.

> Off-network shortcut: you don't even need the device. The device-free test suite asserts this exact property — `pytest -k "production_is_never_writable or never_reaches_production"` is green, and goes red if you add `"production"` to `WRITABLE_ROLES` (exercise 4.4). Enforcement is proven in CI, not just by eye.

**Reflection Questions**

1. Why is the rule written once in `inventory.py` instead of repeated as an `if` at the top of every config tool?
2. Role is checked *before* reachability. Give a scenario where that ordering gives a better error than the reverse.
3. Hiding the config tools AND the role gate are both on. If you could keep only one, which actually protects production — and what does the other still buy you?

> Answer to check yourself (Q3): keep the **role gate** — it is enforcement; a tool called by name anyway is still refused. Hiding only reduces the *chance* a model tries. Defense is the gate; hiding is hygiene.

## Verify

**Success Criteria**

- With `enable_config_tools(false)`, `tools/list` is shorter — the destructive tools are gone (hiding)
- A write aimed at a DC (production) device is refused with no SSH attempted (enforcement), while the same write to `sdceightkv24` passes the role gate
- You proved the DC device is unchanged — by snapshot diff, or by the device-free test that asserts it

**Done when:** you have watched hiding (shorter list) and enforcement (refused DC write, no SSH) as two *different* mechanisms, and shown the DC device is unchanged.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| config tools missing from `tools/list` | left disabled from Part 1 | call `enable_config_tools(enabled=true)` |
| DC write "succeeded"? | you targeted a prod-rep device by mistake | target `sdceightkv11` (DC, production) explicitly |
| DR write errors "no management address" | pod off-network | the **role** gate still passed; that's the lesson. SSH failure is environmental |
| expected an "authorization error" code | enforcement returns a *result* string, not a transport error | read the tool result text: "Refusing to configure ..." |
| snapshots differ | you wrote to the DR device, not DC | diff `sdceightkv11`, not `sdceightkv24` |

## Quick Reference

- **Hiding** (`enable_config_tools false`) = UX; removes tools from `tools/list`. Changes no state.
- **Authorization** (`may_write_to`) = enforcement; `WRITABLE_ROLES = {"prod-rep"}`, production never writable.
- Refusal is a **tool result** ("Refusing to configure..."), returned in ~33 ms, **no SSH**. Role checked before reachability.
- Per-*token* read-only RBAC = a later hardening lab; here the protection is **device role**.

---

**Source material:** `WRITABLE_ROLES` / `PROMOTABLE_ROLES` in `code/server/app/inventory.py`; refusal matrix in `docs/lab-device-map.md`
