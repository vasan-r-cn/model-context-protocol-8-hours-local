# The Integration Wall

**Category:** 02 · AI Agents · **Duration:** 5 min · **Runs on:** — · **Targets:** —

**Devices in play:** None — a thinking exercise. No network device is reached.

## Introduction

In exercises 2.1–2.3 you gave one agent one tool, then a second, then a third. It worked. It always works at three. This exercise is the moment you look at what you built and ask: *what happens at thirty?*

This is a thinking exercise, not a coding one. No terminal, no model. By the end you will have written down — in your own words — the exact problem the rest of the day exists to solve. When MCP is introduced in Category 3, it will not be an abstract protocol. It will be the answer to the wall you are about to hit.

## What You'll Learn

- Why hand-wiring tools stops scaling at the 20th tool and the 3rd agent
- What has to change in your code when a vendor changes their API
- What a protocol would have to provide to make that problem go away

## Before You Start

- Exercises 2.1–2.3 complete

## Architecture Overview

What you have right now, drawn honestly:

```text
            your agent code
          /       |        \
   vManage     ThousandEyes   ServiceNow
   client       client         client
  (you wrote)  (you wrote)    (you wrote)
```

Every line is glue **you** wrote and **you** maintain: auth, request shape, response parsing, error handling, retries — per tool, per agent. Now picture the real target:

```text
   agent A        agent B        agent C
      \  \  \       |  |  |       /  /  /
       (every agent re-wires every tool it needs)
   vManage  ThousandEyes  ServiceNow  Splunk  Meraki  ...20 more
```

That is **M agents × N tools** of integration code. Add one agent, re-wire N tools. Add one tool, touch M agents.

## Setup

### Step 1 — none

Open a notebook or a scratch file. That is the whole setup.

## Exercises

### Part 1 — count the cost of growth

Using the three tools you wired in 2.1–2.3, answer on paper:

1. You add a **4th** specialist agent that needs the same three tools. How many new tool-wiring integrations do you write? Now generalise: M agents, N tools — how many integrations in the worst case?
2. **vManage ships a breaking API change** (a field renames, an auth header changes). Walk through your 2.1 code: which files change? Now multiply by every agent that talks to vManage. Who finds out it broke — you, or your user at runtime?
3. A teammate wants to add a **Meraki** tool. What do they need from you before they can even start? Where is the "list of tools and how to call them" written down today? (Trick question — it's scattered across your code.)

### Part 2 — design the thing that fixes it

Without naming MCP, write one sentence: *"To make this stop hurting, there would have to be a standard way to ___."* Then list the specific things that "standard way" would need to carry across the wire so an agent could use a tool it had never seen.

**Reflection Questions**

1. Which of your three pains is worst *at scale* — the N×M wiring, the breakage on vendor change, or the discovery problem? Defend your answer.
2. If a **vendor** published their own tool server that you just connected to, which of the three pains would disappear and which would remain yours?

> Answer to check yourself: if the vendor ships the server, the *wiring* and the *breakage-on-change* move to them — when their API changes, they update their server, not you. What remains yours is *choosing* which servers to trust and connect. That hand-off is the entire value proposition you'll see in Category 3 and again in Lab 3.

## Verify

**Success Criteria**

- A written answer naming at least three things that break as tools and agents multiply
- You can state, in one sentence, what MCP would have to standardise to fix it

**Done when:** you have the three pains written down and a one-sentence description of the protocol that would remove them — in your own words, before anyone shows you MCP.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "I can't think of three pains" | thinking about 3 tools, not 30 | re-read Part 1 Q1 and scale M and N up to 20+ |
| "Isn't the answer just 'write a library'?" | a shared library still ships *in* every agent and breaks on vendor change | ask: what if the *vendor* ran it, not you? |

## Quick Reference

- The wall: **M agents × N tools** of hand-written, separately-maintained glue.
- The three pains: **N×M wiring**, **breakage on vendor API change**, **no shared discovery**.
- The fix (next category): a **protocol** — a standard way to describe tools, call them, and discover them, so an agent can use a server it never shipped with.

---

**Source material:** No code. This is the hinge into Category 3.
