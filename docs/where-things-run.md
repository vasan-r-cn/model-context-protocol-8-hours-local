# Where Things Run — host placement and sanity checks

Companion to [`lab-device-map.md`](lab-device-map.md), which says *which network
device* to point at. This file says *which machine runs which process*, and how
to prove the whole chain works before a class starts.

---

## Placement

**Each participant gets their own full topology pod.** Nothing is shared — not
the devices, not Splunk, not the controllers. Every participant has their own
DC, DR, branches, legacy site, SD-WAN control plane and orchestrator.

That makes the placement question almost trivial, and it removes the three
things that would otherwise have shaped the day: per-seat port numbers, device
contention, and blast radius between students.

| Component | Runs on | Port | Started by |
|---|---|---|---|
| **Student MCP server** (`code/server/`) | the participant's own desktop | `8000` (localhost) | the participant, `./run.sh` |
| **fast-agent** (`code/client-fastagent/`) | same desktop | — (CLI) | the participant |
| **MCP Inspector** | same desktop, browser | `6274` | the participant, `npx` |
| **Multi-agent orchestrator** (Lab 5) | same desktop | `7860` Gradio | the participant |
| **ThousandEyes agent** (Lab 5) | same desktop | — | pre-installed on the image |
| **DefenseClaw** (Lab 4/6) | `linuxdesktop65` | — | the participant |
| **SD-WAN MCP Server** (`code/server-sdwan/`) | same desktop | `7004` `/mcp` | the participant, `./run.sh` → pod vManage |
| **Splunk MCP Server** (`code/server-splunk/`, `splunk/splunk-mcp-server2`) | same desktop | `8050` `/sse` | the participant, `./run.sh` → pod Splunk `:8089` |
| **Splunk service** | **their own pod's `cclorchestrator78`** | `8089` (REST) | already running in the pod |
| **Network devices** | the lab topology | SSH 22 | nobody — reached over SSH |

Participant desktops, per the topology: **`linuxdesktop64`** (Site-10) and
**`linuxdesktop65`** (Site-20). With more seats than desktops, the seat → desktop
map is an open item — see [Open](#open).

### What per-pod topologies buy us

- **Every command in every lab guide is identical for everyone.** No seat
  numbers, no per-seat ports, no per-seat loopback ranges, no `10.<seat>.x.x`
  arithmetic on a lab sheet. `localhost:8000` and `sdceightkv24` for everybody.
- **Config changes are genuinely safe.** A student can shut an interface on
  their own DC and only break their own pod. The DC/DR validate-then-promote
  lesson is real rather than simulated, and the capstone can inject a real
  fault.
- **No contention.** The VTY-limit problem, SSH session pressure, and "16
  students queuing on one Splunk" all disappear.
- **Splunk is still not ours.** It runs in their pod, but the MCP server is a
  Splunk app on the management port — nothing to install, read-only token, and
  the lesson stands: you consume a vendor server on its terms.

### The one thing that must be true

```
their desktop  --SSH-->  their sdceightkv24 (DR)     # or the server is useless
their desktop  --HTTPS-> their cclorchestrator78:8089 # or Lab 3 is a demo
their desktop  --HTTPS-> openrouter.ai                # or the model cannot run
their desktop  --HTTPS-> their vmanage / ThousandEyes # or Lab 5 is a demo
```

All of these are **inside one pod** except OpenRouter and ThousandEyes, which
leave it.

Check 3 below is the one that decides whether the workshop is hands-on or a
presentation. Run it on a real participant desktop **before** the build
continues, not on the day.

---

## Sanity checks

Run `./scripts/sanity_check.sh` on a participant desktop. It works through the
chain in dependency order and stops being useful the moment one link is broken,
so **read the first failure, not the last**.

First time on a pod desktop:

```bash
./bootstrap_desktop.sh        # uv's private Python 3.12, both venvs, offline tests
```

Then:

```bash
./sanity_check.sh                      # full ladder
./sanity_check.sh --quick              # skip the device/network checks
SPLUNK_HOST=cclorchestrator78 SPLUNK_PORT=8089 ./sanity_check.sh   # probes pod Splunk REST
```

Both scripts locate the workshop files themselves, so it does not matter whether
they sit in `scripts/`, next to `code/` in a home directory, or are called by
absolute path from anywhere. If the layout is unusual, point them at it with
`WORKSHOP_ROOT=<dir containing code/>`.

The pod image ships Python 3.10. `bootstrap_desktop.sh` has `uv` fetch a private
3.12 rather than upgrading the system Python, which fast-agent requires and the
image's own tooling does not.

What it checks, in order:

| # | Check | Needs | Fails when |
|---|---|---|---|
| 1 | Python 3.12 and `uv` present | desktop image | image is wrong or `uv` not on `PATH` |
| 2 | Server venv builds and imports | desktop | network to PyPI is blocked |
| 3 | **Inventory devices reachable over SSH** | lab network | `inventory.yaml` has no addresses, or the desktop has no route |
| 4 | MCP server starts, health endpoint answers | 2 | port 8000 already taken |
| 5 | `/mcp` rejects an unauthenticated request (401) | 4 | auth middleware regressed |
| 6 | Protocol smoke test (`smoke_test.sh`) | 4 | handshake, session id, or tool list broken |
| 7 | Offline test suite (`pytest`) | 2 | a safety rule regressed — **this one never needs a device** |
| 8 | fast-agent connects and calls a tool, no LLM | 4 | client config or bearer token wrong |
| 9 | **Blast radius:** write to a production device is refused | 8 | the safety model regressed |
| 10 | **Elicitation gate** fires (`auto-cancel` vs `none`) | 8 + a reachable device | fast-agent version or elicitation config wrong. Reports BLOCKED until the default device has a management address — the write is refused before the gate is reached |
| 11 | Pod Splunk REST reachable (`cclorchestrator78:8089`) | `cclorchestrator78` | no route to `8089`, or Splunk account wrong (the Splunk MCP server runs locally via `code/server-splunk/`) |
| 12 | OpenRouter key works | key | key missing, unfunded, or rate-limited |

Checks 7, 9 and 10 need **no device and no lab network** — they are the
regression gate for the code itself and run anywhere, including CI.

### Current state on a build host with no lab access

```
11 passed, 0 failed, 2 blocked, 2 skipped
```

Blocked: device reachability, and the elicitation gate (it cannot be exercised
until the default device has a management address). Skipped: Splunk and
OpenRouter, neither configured yet. Everything that can be checked without the
lab passes.

### Reading the result

- `PASS` — verified, with the evidence printed.
- `FAIL` — broken; fix before moving on. The ladder is ordered, so the first
  `FAIL` is usually the only real problem.
- `BLOCKED` — cannot be checked yet because something upstream is missing
  (typically: no management addresses in `inventory.yaml`). Not a code fault.
- `SKIP` — deliberately not run (`--quick`, or no key configured).

---

## Open

- **Are management addresses identical in every pod?** `inventory.yaml` ships
  `192.168.116.0/24` for all 11 devices. If pods are cloned from one spec, that
  file is universal and nobody edits anything. If each pod is addressed
  differently, every student needs their own values — in which case generate
  `inventory.yaml` per pod from that pod's underlay, or set
  `MCP_DEV_<NAME>_HOST` per seat. **Cheapest test: run
  `./scripts/sanity_check.sh` in two different pods and compare check 3.**
- **Splunk per pod:** the Splunk service running on `cclorchestrator78:8089`
  with a **read-only account** and **device syslog actually indexed**. The
  Splunk MCP server is now `splunk/splunk-mcp-server2`, run **locally on the
  desktop** (`code/server-splunk/`, SSE `:8050`) against that Splunk — nothing
  to install inside Splunk. Per-pod means the Splunk data has to be baked into
  the image.
- **Fault injection is now per pod.** The capstone fault and the Lab 4
  tool-poisoning beat were written as "the instructor pre-sets X". With isolated
  pods there is nothing central to pre-set, so both become **scripts the student
  runs in their own pod** (`scripts/inject_fault.sh`, `scripts/seed_injection.sh`).
  Arguably better — they see before and after — but it is a real change to both
  lab guides and to the instructor's answer key.
- **Reset between cohorts** is now pod re-provisioning rather than
  `reset_lab.py`. The script stays useful for a student who wants to re-run a
  lab inside their own pod, but it is no longer the between-cohort mechanism.
- **Two desktops per pod** (`linuxdesktop64`, `linuxdesktop65`). One participant
  owns both: run the MCP server, fast-agent and the orchestrator on `64`, and
  use `65` as the DefenseClaw host, matching
  `expansion/mcp-server-security.md`.
- **`172.18.0.0/16` collides with a default Docker bridge**, and the underlay
  uses that range for the SD-WAN transport side. Anything containerised on a
  desktop must be given a different subnet.
