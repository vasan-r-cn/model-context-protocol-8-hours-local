# Orchestrator Walkthrough

<!-- STUB: generated skeleton, not yet authored -->

**Category:** 07 · Multi-Agent Capstone · **Duration:** 15 min · **Runs on:** `linuxdesktop64` · **Targets:** read-only across the topology

**Devices in play:** Read-only across the whole topology via the orchestrator — SD-WAN (`ciscovmanage3`), ThousandEyes, and ServiceNow.

## Introduction

_To be written._

## What You'll Learn

- Where MCP sits inside a larger system — a layer, not the system
- How a planner routes a question to a specialist agent
- How shared state carries evidence between agents
- How to read the trace and tell routing failures from tool failures

## Before You Start

- Category 6 complete
- Orchestrator venv built (Python 3.11+); `.env` filled

## Architecture Overview

_Component / role table — to be written._

## Setup

### Step 1 — …

_To be written._

## Exercises

### Part 1 — …

_To be written._

**Reflection Questions**

_To be written._

## Verify

**Success Criteria**

- The app is running and you asked it one question end to end
- You traced that request: planner → specialist → state → response
- You can name each specialist agent and the system it talks to

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| _to be written_ | | |

## Quick Reference

_To be written._

---

**Source material:** `multi_agent_v2` — vendor into `code/multi-agent/`
