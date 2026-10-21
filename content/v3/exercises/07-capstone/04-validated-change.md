# Validated Change — DR, Then DC

<!-- STUB: generated skeleton, not yet authored -->

**Category:** 07 · Multi-Agent Capstone · **Duration:** 15 min · **Runs on:** `linuxdesktop64` · **Targets:** validate `sdceightkv24` → promote `sdceightkv11`

**Devices in play:** `sdceightkv24` (DR — validate the change here) → `sdceightkv11` (DC production — promote here).

## Introduction

_To be written._

## What You'll Learn

- Why a change is validated on a production-representative device first
- What a promotion gate refuses, and what evidence it demands
- How rollback is planned before the change, not after
- What an audit record has to contain to reconstruct the event later

## Before You Start

- Exercise 7.3 complete
- `MCP_ENABLE_CHANGE_WORKFLOW=1`

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

- A change was proposed, validated on DR, and promoted to DC with its DR evidence attached
- The promotion was refused when validation was missing
- You rolled the change back and DC is at baseline
- You can reconstruct the whole sequence from the audit record alone

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| _to be written_ | | |

## Quick Reference

_To be written._

---

**Source material:** BLOCKED: `app/change_workflow.py` does not exist yet. See the plan's Open Items.
