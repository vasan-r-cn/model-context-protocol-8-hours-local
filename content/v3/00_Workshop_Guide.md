# Workshop Guide — MCP in Practice

<!-- STUB: generated skeleton, not yet authored -->

Your reference for the day. The exercises have their own files; come back here
for the topology, credentials, ports, and when something breaks.

Start at [the catalog](00_Catalog.md). Do [Setup & Pre-Flight](01_Setup_PreFlight.md) first.
=
## 1. The Big Picture

_Diagram and one-paragraph walkthrough of the chain: you → client → MCP server
→ device. To be written._

## 2. Lab Topology

_Participant-facing device table. **Generate from `docs/lab-device-map.md`** —
do not transcribe by hand, it drifts. Sites: DC (production, read-only), DR
(production-representative, the write target), Site-10 / Site-20 (branches,
where you sit), Legacy, SD-WAN control plane, and the services host
`cclorchestrator78`._

## 3. Credentials and Access

_Per-platform, not one lab password. Source: `docs/lab-device-map.md`._

## 4. What Runs Where

_Host, port, and who starts it, per component. Source: `docs/where-things-run.md`._

## 5. The Safety Model

_Why DC is never written to by a tool call, why `sdceightkv24` is the default
device, and what your seat scoping is. Source: `code/server/app/inventory.py`._

## 6. Verifying Your Stack

_The `sanity_check.sh` ladder, and how to read a `BLOCKED` versus a `FAIL`._

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| _to be written_ | | |

## 8. Glossary

_MCP terms used all day: host, client, server, session, tool, resource, prompt,
notification, elicitation, capability, transport._
