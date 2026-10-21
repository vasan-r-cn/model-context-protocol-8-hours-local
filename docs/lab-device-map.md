# Lab Device Map — which device to use, and for what

Single source of truth for "which box do I point at". Derived from
`expansion/new-topo.png`. Device **names** are reliable; **management
addresses are not in the diagram** and must come from the sandbox (see
[Must be confirmed](#must-be-confirmed)).

Fill addresses into `code/server/inventory.yaml`, or per device without editing
that shared file:

```bash
export MCP_DEV_SDCEIGHTKV24_HOST=<mgmt-ip>      # name uppercased, non-alnum -> _
```

---

## The one-line answer

| Question | Device |
|---|---|
| What do tools hit when nobody says otherwise? | **`sdceightkv24`** (DR SD-WAN edge) — the `default_device` |
| Where may students change configuration? | **DR only:** `sdceightkv24`, `cisconexusnkv30`, `cisconexusnkv41`, `cisconexusnkv52` |
| What must never be changed by a tool call? | **DC:** `sdceightkv11`, `cisconexusnkv12`, `cisconexusnkv13`, `cisconexusnkv14` |
| Where does a validated change get promoted to? | **`sdceightkv11`** (DC SD-WAN edge) |
| Where do participants sit? | **`linuxdesktop64`** (Site-10), **`linuxdesktop65`** (Site-20) |

The DC/DR split is the workshop's argument in hardware: **DR is the
production-representative environment, DC is production.** Validate on DR,
promote to DC.

---

## Inventory by site

Names, management addresses and credentials below come from
`code/server/custom-underlay.yaml` (the sandbox topology spec) and are generated
into `code/server/inventory.yaml` — not transcribed from the diagram.
`nat` is the hypervisor's SSH port-forward, an alternative access path.

### DC — production (read-only to every tool)

| Device | Mgmt | Platform | nat | Role in the lab |
|---|---|---|---|---|
| `sdceightkv11` | `192.168.116.85` | c8000v SD-WAN, `cisco_xe` | 20004 | **Promotion target.** The only device a validated change reaches |
| `cisconexusnkv12` | `192.168.116.19` | Nexus, `cisco_nxos` | 20005 | DC aggregation; twin of `cisconexusnkv30` |
| `cisconexusnkv13` | `192.168.116.9` | Nexus, `cisco_nxos` | 20006 | DC access; serves `linuxdesktop19` |
| `cisconexusnkv14` | `192.168.116.21` | Nexus, `cisco_nxos` | 20007 | DC access; serves `linuxdesktop20` |
| `linuxdesktop19` / `linuxdesktop20` | `.93` / `.5` | ubuntu | 20008 / 20010 | The "DC app" the capstone cannot reach |

### DR — production-representative (the write target)

| Device | Mgmt | Platform | nat | Role in the lab |
|---|---|---|---|---|
| `sdceightkv24` | `192.168.116.51` | c8000v SD-WAN, `cisco_xe` | 20012 | **`default_device`.** Read in Labs 1–4, written in Lab 4, validated on in Lab 5 |
| `cisconexusnkv30` | `192.168.116.91` | Nexus, `cisco_nxos` | 20013 | DR aggregation, twin of `cisconexusnkv12`. Writable |
| `cisconexusnkv41` | `192.168.116.18` | Nexus, `cisco_nxos` | 20014 | DR access, twin of `cisconexusnkv13`. Writable |
| `cisconexusnkv52` | `192.168.116.14` | Nexus, `cisco_nxos` | 20015 | DR access, twin of `cisconexusnkv14`. Writable |
| `linuxdesktop53` / `linuxdesktop54` | `.40` / `.26` | ubuntu | 20016 / 20018 | DR application endpoints |

### Branches — read-only, and where people sit

| Device | Mgmt | nat | Role in the lab |
|---|---|---|---|
| `sdceightkv62` | `192.168.116.52` | 20021 | Site-10 edge. **Source of the capstone fault path** |
| `linuxdesktop64` | `192.168.116.28` | 20023 | **Participant workstation (Site-10).** Runs their MCP server, fast-agent, the orchestrator, the ThousandEyes agent |
| `sdceightkv63` | `192.168.116.94` | 20022 | Site-20 edge |
| `linuxdesktop65` | `192.168.116.32` | 20025 | **Participant workstation (Site-20).** DefenseClaw host in `expansion/mcp-server-security.md` |

### Legacy site — read-only

| Device | Mgmt | nat | Role in the lab |
|---|---|---|---|
| `ciscoeightkv73` | `192.168.116.70` | 20027 | Autonomous c8000v, **not SD-WAN managed**. The "not everything is a fabric" beat, and the fallback write target |
| `linuxdesktop74` | `192.168.116.34` | 20028 | Legacy endpoint |

### Services host — `cclorchestrator78`

`192.168.116.16`, eth1 `172.18.7.1`, ubuntu/`password`, SSH nat 20030.
**Splunk runs here as a service** — in the underlay it is the VM entry keyed
`splunk78`, whose hostname is `cclorchestrator78`. Splunk's REST/management port:

```
https://cclorchestrator78:8089          # Splunk REST — Module 5 and the capstone
```

The **Splunk MCP server** is `splunk/splunk-mcp-server2` (MIT, unofficial), run
**locally on the participant desktop** (`code/server-splunk/`, SSE on `:8050`)
pointed at this Splunk over REST with a **read-only Splunk account**. Nothing is
installed inside Splunk. The SD-WAN MCP server (`code/server-sdwan/`, `:7004`)
is also run on the desktop against vManage.

Not a network device — no MCP tool of ours SSHes to `cclorchestrator78`, so it
is deliberately **not** in `inventory.yaml`.

### SD-WAN control plane — read-only, via the SD-WAN agent (Lab 5)

`ciscovmanage3` (`192.168.116.55`, nat 20000) · `ciscovbond4` (`.24`, 20001) ·
`ciscovsmart5` (`.17`, 20002). All `admin`/`admin123`. Students never edit a
template.

### Transports

`public-internet6` (`192.168.116.78`) and `mpls55` (`192.168.116.81`), both
`cisco`/`cisco`. **The capstone fault moves traffic between them.** Also present:
`inetrouter` (`192.168.116.84`).

### Credentials differ by platform

Not a single lab password — this is why `inventory.yaml` carries credentials per
device rather than globally:

| Platform | User / password |
|---|---|
| Nexus (`cisconexusnkv*`) | `admin` / `cisco` |
| SD-WAN edges (`sdceightkv*`), vManage/vBond/vSmart | `admin` / `admin123` |
| Legacy `ciscoeightkv73` | `admin` / `admin` |
| Linux desktops, `cclorchestrator78` | `ubuntu` / `password` |
| Transports | `cisco` / `cisco` |

Override per device without editing the shared file:
`MCP_DEV_<NAME>_HOST`, `_USER`, `_PASSWORD`, `_SECRET`.

## Which device each lab uses

| Lab | Reads | Writes | Why this device |
|---|---|---|---|
| **1 · Protocol on the wire** | `sdceightkv24` | — | Default device; the point is the protocol, not the platform |
| **2 · Build a tool** | `sdceightkv24` → pings `sdceightkv11` | — | A reachability tool has to cross the WAN to be interesting |
| **3 · vendor MCP server** | `sdceightkv24` + the Splunk index on `cclorchestrator78` | — | Device state from your server, log evidence from Splunk — cross-domain composition, not two views of one device |
| **4 · Control + security** | `sdceightkv24` | `sdceightkv24` | Write refusal is demonstrated against `sdceightkv11` (production) and succeeds on `sdceightkv24` |
| **5 · Capstone** | `sdceightkv62`, vManage, ThousandEyes, DC devices | validate `sdceightkv24` → promote `sdceightkv11` | The fault is on the Site-10 → DC path; the fix is proven on DR before DC |

### Lab 4, the refusal demo, concretely

```
create_loopback device=sdceightkv11   → refused, no SSH attempted   (production)
create_loopback device=sdceightkv62   → refused                      (branch)
create_loopback device=sdceightkv24   → allowed, elicitation gate    (prod-rep)
create_loopback  (device omitted)     → sdceightkv24                 (safe default)
```

### No seat scoping — every participant has their own pod

Each participant gets a **complete, isolated copy of this topology**. Nothing on
this page is shared between students, so:

- **No per-seat loopback ranges or address arithmetic.** Everyone uses the same
  IDs and the same addresses. Lab sheets carry one set of values.
- **No VTY or SSH contention**, and no "16 students queuing on one Splunk".
- **Blast radius is one pod.** A student who shuts the wrong interface breaks
  only their own lab, which is what makes the DC/DR validate-then-promote
  exercise real rather than theatrical.

The `role` model in `inventory.yaml` is therefore not there to protect other
students — it is there to teach the operational discipline. That distinction is
worth saying out loud in Lab 4: the guard rail exists because production
deserves one, not because the lab is fragile.

**Consequence for the lab design:** anything written as "the instructor
pre-sets…" has nothing central to pre-set. The capstone fault and the Lab 4
tool-poisoning seed become scripts each student runs in their own pod.

---

## Must be confirmed

Most of this list was answered by `code/server/custom-underlay.yaml`. What
remains:

1. **Can the participant desktops reach `192.168.116.0/24`?** Every management
   address is on that subnet; `linuxdesktop64`/`65` sit at `.28`/`.32`, so it is
   very likely, but it has not been proven. Run
   `./scripts/sanity_check.sh` on a desktop — check 3 answers this in one step.
2. **Resolved by per-pod topologies:** config writes are a student's own
   business. DR writes, and the promotion to their own DC, affect nobody else.
3. **Splunk on `cclorchestrator78`:** Splunk running with a **read-only
   account**, **device syslog actually indexed**, tcp/8089 reachable from the
   desktops, self-signed cert handled (`VERIFY_SSL=false`). The MCP layer is the
   local `splunk/splunk-mcp-server2` (`code/server-splunk/`, SSE `:8050`) — no
   Splunk app to install.
4. **vManage API account** (`admin`/`admin123`) exposed per pod as
   `VMANAGE_HOST=<pod FQDN>:<port>` for `code/server-sdwan/` and the Module 2
   agents; ThousandEyes account and test IDs; ServiceNow instance and incident
   number (capstone).
5. **Resolved:** each participant gets their own pod, with both desktops
   (`linuxdesktop64`, `linuxdesktop65`) to themselves. Remaining question is
   whether management addresses are **identical across pods** — if so
   `inventory.yaml` ships unchanged to everyone; if not, it must be generated
   per pod. See [`where-things-run.md`](where-things-run.md).
6. **`172.18.0.0/16` collides with a default Docker bridge**, and the underlay
   uses that range for the SD-WAN transport side. Anything containerised on a
   lab host must be given a different subnet.

**Resolved** by the underlay: all device names (the diagram's occluded labels are
`cisconexusnkv13` and `cisconexusnkv41`), every management address, per-platform
credentials, and the Splunk host.
