# Instructor Guide — MCP in Practice, 8 Hours

<!-- STUB: generated skeleton, not yet authored -->

**Do not hand this to participants.**

## 1. Day Plan

_Category-by-category pacing against the clock checkpoints in
[the catalog](../00_Catalog.md), with the lecture blocks interleaved._

## 2. Pre-Delivery Checklist

_What must be true before the room arrives: device reachability from both
participant desktops, DR write access, VTY capacity, Splunk token and indexed
syslog, vManage / ThousandEyes / ServiceNow accounts, provider budget._

## 3. Fault Injection

_The Category 6.3 planted interface description and the Category 7.3 path
fault: scripts, how to verify they took, and how to restore. **To be written** —
the scripts do not exist yet._

## 4. The Chaos Beat

_Break DR reachability during 7.4 so validation fails and promotion refuses,
with DC untouched. Three minutes, on the projector._

## 5. Answer Keys

_One file per exercise under `answer-keys/`, written from captured real output.
Never from expectation._

## 6. Skip Ladder

_See the catalog. Decide at a category boundary, announce it, do not
silently rush._

## 7. Incident Runbook

_What to do when: a device stops answering, VTY limits hit, a participant's
server will not start, the provider rate-limits, Splunk is down._

## 8. Reset Between Cohorts

```bash
cd code/server && python3 reset_lab.py          # dry run
cd code/server && python3 reset_lab.py --apply
```

_Plus: restore the planted interface description, clear snapshots and change
records, rotate the audit log. A second clean run must report nothing to do._
