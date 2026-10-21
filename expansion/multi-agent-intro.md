# Multi-Agent Orchestration — Introduction

## Purpose

This lab introduces a multi-agent architecture for network operations. Instead of one agent handling every domain, an **orchestrator** coordinates specialist agents.

Workshop focus:

- **SD-WAN Agent** — network/SD-WAN operations
- **ThousandEyes Agent** — path and experience visibility
- **ServiceNow Agent** — ITSM/incident operations
- **Orchestrator / Planner** — intent classification and workflow coordination
- **LangGraph** — graph execution and shared state
- **Gradio** — user interface

## Architecture

```text
User
 |
 v
Gradio UI / app.py
 |
 v
Planner / Router
 |
 +----> SD-WAN Agent
 |
 +----> ThousandEyes Agent
 |
 +----> ServiceNow Agent
 |
 v
Shared State / Graph
 |
 v
Final Response
```

The workshop material describes this as a **hub-and-spoke** pattern: a master/orchestrator delegates work to specialist agents.

## Why Multi-Agent?

Each agent has a clear responsibility:

| Component | Responsibility |
|---|---|
| Orchestrator | Understand intent and select/coordinate agents |
| SD-WAN Agent | SD-WAN/network operational analysis |
| ThousandEyes Agent | End-to-end path and experience visibility |
| ServiceNow Agent | Incident/ITSM operations |
| Shared State | Carry context and intermediate results |
| LangGraph | Routing, nodes, edges and workflow control |
| Gradio | User interaction |

The key teaching point is:

> **The goal is not three separate chatbots. The goal is coordinated specialist agents working as one operational system.**

## Example

```text
"Investigate this network performance issue.
Check SD-WAN, investigate the ThousandEyes path,
and check for a related ServiceNow incident."
```

A multi-agent workflow can use different specialists to contribute evidence to the same operational question.

## Key Concepts

1. **Specialization** — each agent owns a domain.
2. **Orchestration** — the planner/router determines the workflow.
3. **Shared state** — information can move between graph nodes.
4. **Graph execution** — LangGraph supports routing and conditional workflows.
5. **Extensibility** — another specialist can be added using the same agent → node → graph → router pattern.

## Learning Objectives

Participants should be able to:

- Explain single-agent vs multi-agent architecture.
- Identify the role of the orchestrator.
- Explain shared state.
- Follow a request through LangGraph.
- Understand where SD-WAN, ThousandEyes and ServiceNow fit.
- Validate individual agents and the overall workflow.
- Understand how to add another specialist agent.

## Workflow

```text
Prompt → Route → Specialist Agent → Tool/API → State → Response
```