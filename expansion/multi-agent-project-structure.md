# Multi-Agent Orchestration — Code Walkthrough

## Project Structure

The workshop documentation describes the multi-agent project approximately as:

```text
multi_agent_langgraph/
├── agents
│   ├── base.py
│   └── guardrails.py
├── app.py
├── edges.py
├── graph.py
├── main.py
├── nodes.py
├── prompts
│   ├── root_prompt.py
│   ├── sdwan_prompt.py
│   ├── servicenow_prompt.py
│   └── thousandeyes_prompt.py
├── README.md
├── requirements.txt
├── server.py
├── state.py
├── tools
│   ├── escalation_tools.py
│   ├── research_tools.py
│   ├── sdwan_tools.py
│   ├── servicenow_tools.py
│   └── thousandeyes_tools.py
└── toolsets.py
```

> An earlier guide uses `service_now.py`; the v3 workshop material uses `servicenow.py`. Use the filename in the supplied `multi_agent_v2` code base.

## 1. `app.py` — Entry Point

`app.py` exposes the workflow through the Gradio UI.

Conceptually:

```text
Browser → Gradio → Graph / Orchestrator
```

**Instructor question:** Where does the user's natural-language request enter the multi-agent system?

---

## 2. `state.py` — Shared Context

The LangGraph state carries information between workflow nodes.

Conceptually:

```python
state = {
    "question": "...",
    "intent": "...",
    "agent_result": "...",
    "response": "..."
}
```

Use the **actual fields from `multi_agent_v2`** when teaching the code.

Key message:

> State is the shared context that allows different workflow nodes to exchange information.

---

## 3. `router.py` — Intent Routing

The router determines which workflow path should execute.

Example:

```text
"Show SD-WAN tunnel status"
          |
          v
     SD-WAN Agent
```

```text
"Show ThousandEyes path"
          |
          v
   ThousandEyes Agent
```

```text
"Get incident INC0017997"
          |
          v
   ServiceNow Agent
```

The workshop material describes keyword and/or LLM-based intent classification.

---

## 4. `sdwan_graph.py` — Main Workflow

This is the main LangGraph workflow.

Conceptually:

```text
START
 |
 v
Router
 |
 +---- SD-WAN Node --------+
 |                         |
 +---- ThousandEyes Node --+--> Response
 |                         |
 +---- ServiceNow Node ----+
```

Show the actual graph construction from the repository and point out:

- nodes
- edges
- routing
- state
- final response

---

## 5. Agent Nodes

A node connects LangGraph to a specialist agent.

Conceptually:

```python
def agent_node(state):
    result = specialist_agent.run(state)
    return {"agent_result": result}
```

The exact implementation must come from the supplied source.

Teaching rule:

> **The graph controls orchestration; the agent performs domain-specific work.**

---

## 6. SD-WAN Agent

The SD-WAN specialist handles network-domain operations.

Possible workshop use cases include:

- tunnel health
- BFD status
- application-aware routing
- WAN SLA checks
- policy validation
- TLOC/path analysis

Focus on the flow:

```text
User Intent
 → SD-WAN Agent
 → SD-WAN API/tool
 → Result
 → Shared State
```

Do not spend the orchestration section on every SD-WAN API.

---

## 7. ThousandEyes Agent

The ThousandEyes specialist handles end-to-end path/experience information.

Documented example:

```text
Get path visualization details for test_id 2637213.
```

Another example:

```text
Give the available test list of dns-server of ThousandEyes agent.
```

Teaching point:

> SD-WAN provides managed-network visibility; ThousandEyes provides end-to-end path and experience visibility.

---

## 8. ServiceNow Agent

The ServiceNow specialist handles ITSM operations.

Example:

```text
Get details for ServiceNow incident INC0017997.
```

For the instructor-assisted exercise, demonstrate the same extension pattern:

```text
Agent implementation
      ↓
Graph node
      ↓
Graph registration
      ↓
Router / intent handling
      ↓
UI validation
```

---

## 9. `planner.py` — Orchestrator

The planner/master-agent role coordinates the workflow.

Important distinction:

```text
Planner ≠ Domain Tool Executor
```

The planner decides/coordinates; specialist agents perform domain-specific work.

---

## 10. `base.py`

The base agent provides common functionality/configuration for specialist agents.

Use the supplied implementation to explain:

- common LLM configuration
- shared agent behavior
- common setup
- error/logging behavior

---

## 11. `logger.py`

Centralized logging provides:

- execution visibility
- debugging
- error tracing
- orchestration troubleshooting

Keep terminal logs visible during the demo.

---

## Complete Request Lifecycle

```text
1. User enters prompt
2. app.py receives request
3. Planner / Router determines intent
4. LangGraph selects node
5. Specialist agent executes
6. Agent calls tool/API
7. Result updates state
8. Graph completes
9. Gradio displays response
```

## Instructor Focus

Do not teach every line.

Teach the relationship:

```text
app.py
  ↓
router.py / planner.py
  ↓
sdwan_graph.py
  ↓
agent node
  ↓
specialist agent
  ↓
tool/API
  ↓
state.py
  ↓
response
```