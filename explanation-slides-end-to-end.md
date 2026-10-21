# Explanation Slides — End-to-End Mermaid Diagrams

Diagram source for the 4-hour MCP workshop deck (`Training Process.pptx`, 48 slides).

**How to use this file**
- Each entry maps to a slide (or a suggested *new* insert) and contains: what participant confusion it fixes, the diagram type, a ready-to-render **mermaid** block, and a one-line caption.
- Render each block at [mermaid.live](https://mermaid.live) → export PNG/SVG → enhance with the image model → paste into the slide.
- Only `flowchart` and `sequenceDiagram` are used so everything renders cleanly and shares one visual language.

**Single running thread (kept consistent across all diagrams)**
- **Concept slides:** "Why is Branch-12 / Webex slow?" network-troubleshooting story (Webex · ThousandEyes · Splunk), matching the deck's existing slides 9/11/16/19/21.
- **Protocol + lab slides:** the *real* workshop server — LibreChat → MCP server (`:8000/mcp`, bearer) → Netmiko SSH → **Router1 `172.18.2.6`**, tools `get_interfaces` / `dynamic_show` / `configure_interface` / `create_loopback`, resources `router://interfaces|running-config|baseline`, prompts `/troubleshoot_interface` · `/audit_router_config`, plus the elicitation confirm-gate.

**Legend (reuse these role labels everywhere for a coherent look)**
- **Host** = the AI app the user talks to (LibreChat, Claude Desktop, Cursor)
- **Client** = the MCP connector inside the host (1 client ↔ 1 server)
- **Server** = the program exposing Tools / Resources / Prompts (our router server)
- **LLM** = the model doing the reasoning
- **Router1** = the lab device the server drives over SSH

---

## A. Concept glue

### Slide 14 — How APIs Work (request/response cycle)
**Fixes:** the current slide is overlapping text with no picture; participants don't see the request→process→response loop.
**Type:** sequenceDiagram

```mermaid
sequenceDiagram
    autonumber
    participant App as Client app
    participant API as Server (API)
    participant DB as Data / device

    App->>API: HTTP request — GET /interfaces<br/>headers: Authorization: Bearer …
    Note over App,API: Method + endpoint + params + body
    API->>DB: Look up / act
    DB-->>API: Raw data
    API-->>App: HTTP response — 200 OK<br/>JSON payload
    Note over App,API: Each call is independent (stateless).<br/>Auth travels in every request.
```
*Caption: An API call is one round trip — the client asks with a verb + endpoint, the server does the work and answers with a status code and JSON. Every call stands alone.*

---

### Slide 17 / 18 — The M×N Integration Problem
**Fixes:** text-only "N×M problem"; participants can't see why custom integrations explode.
**Type:** flowchart (bipartite)

```mermaid
flowchart LR
    subgraph Agents["M AI agents"]
        A1[Chatbot]
        A2[Troubleshooting agent]
        A3[Ops copilot]
    end
    subgraph Tools["N tools / systems"]
        T1[Webex API]
        T2[ThousandEyes API]
        T3[Splunk API]
    end

    A1 --> T1
    A1 --> T2
    A1 --> T3
    A2 --> T1
    A2 --> T2
    A2 --> T3
    A3 --> T1
    A3 --> T2
    A3 --> T3

    note["3 agents × 3 tools = 9 custom integrations<br/>Each has its own API, auth, data format<br/>M × N — every line built, tested, maintained"]
    Tools -.-> note
```
*Caption: Without a standard, every agent needs bespoke glue for every system. 3×3 already = 9 brittle integrations; it grows as M×N.*

---

### Slide 18 / 19 — The MCP Solution: M + N
**Fixes:** broken side-by-side text; the "linear scaling" payoff isn't visual.
**Type:** flowchart (hub)

```mermaid
flowchart LR
    subgraph Agents["M AI agents — speak MCP once"]
        A1[Chatbot]
        A2[Troubleshooting agent]
        A3[Ops copilot]
    end
    MCP{{"MCP<br/>one standard protocol<br/>tools/list · tools/call"}}
    subgraph Servers["N MCP servers — built once, reused"]
        S1[Webex MCP server]
        S2[ThousandEyes MCP server]
        S3[Splunk MCP server]
    end

    A1 --> MCP
    A2 --> MCP
    A3 --> MCP
    MCP --> S1
    MCP --> S2
    MCP --> S3

    note["3 agents + 3 servers = 6 connections<br/>Any agent can use any server<br/>M + N instead of M × N"]
    Servers -.-> note
```
*Caption: Each agent implements MCP once; each system is wrapped once as an MCP server. 5×10 = 50 custom integrations becomes 5+10 = 15.*

---

### NEW 18a — MCP Value Proposition (who maintains the integration?)
**Fixes:** meet-notes ask — show how *vendor-provided* MCP servers remove the API-churn burden. Kept on-thread with a network vendor (Splunk) instead of booking.com.
**Type:** flowchart (before / after)

```mermaid
flowchart TB
    subgraph Before["Before MCP — you own the glue"]
        direction LR
        yb[Your agent] --> gb["Splunk API client<br/>(you write & maintain<br/>~150 lines)"]
        gb --> sb[Splunk]
        chg1["Splunk changes its API →<br/>your client breaks →<br/>you patch it"]:::warn
        sb -.-> chg1
    end

    subgraph After["With MCP — the vendor owns the glue"]
        direction LR
        ya[Your agent] -->|speaks MCP| sa["Splunk MCP server<br/>(shipped & maintained<br/>by Splunk)"]
        sa --> spa[Splunk]
        chg2["Splunk changes internally →<br/>they update their MCP server →<br/>your agent is untouched"]:::ok
        spa -.-> chg2
    end

    classDef warn fill:#fde2e1,stroke:#c0392b,color:#7b241c;
    classDef ok fill:#e8f6ef,stroke:#1e8449,color:#145a32;
```
*Caption: When a provider ships its own MCP server, API changes are their problem, not yours. Your agent speaks one protocol and stops chasing breaking integrations.*

---

### Slide 20 — What is MCP? ("USB-C for AI")
**Fixes:** broken/overlapping text; the analogy never lands visually.
**Type:** flowchart (analogy, two parallel rows)

```mermaid
flowchart LR
    subgraph Physical["Physical world"]
        direction LR
        d1[Monitor]
        d2[Keyboard]
        d3[Drive]
        usbc{{USB-C<br/>one connector}}
        laptop[Laptop]
        d1 --> usbc
        d2 --> usbc
        d3 --> usbc
        usbc --> laptop
    end

    subgraph AI["AI world"]
        direction LR
        t1[Router tools]
        t2[Files / logs]
        t3[Ticketing]
        mcp{{MCP<br/>one protocol}}
        host[AI app / LLM]
        t1 --> mcp
        t2 --> mcp
        t3 --> mcp
        mcp --> host
    end

    Physical -.->|same idea| AI
    note["MCP is a standard connector, NOT an AI, an agent, or a model.<br/>It is the port everything plugs into."]
    AI -.-> note
```
*Caption: USB-C let any device use one port. MCP lets any tool plug into any AI the same way — it's the connector, not the brain.*

---

## B. Architecture / protocol

### Slide 23 — MCP Protocol Architecture (Host / Client / Server + layers)
**Fixes:** the core meet-notes request — participants can't picture host vs client vs server, or the data/transport split.
**Type:** flowchart (component diagram with subgraphs)

```mermaid
flowchart TB
    user([User]) --> Host

    subgraph Host["HOST — AI application (LibreChat · Claude Desktop · Cursor)"]
        direction LR
        ca["MCP Client A<br/>1:1 connector"]
        llm["LLM<br/>reasons · picks tools"]
        cb["MCP Client B<br/>1:1 connector"]
        ca --- llm
        llm --- cb
    end

    subgraph Srv1["SERVER 1 — Router MCP server (ours)"]
        direction TB
        t1["Tools<br/>get_interfaces · configure_interface<br/>controlled by the MODEL"]
        r1["Resources<br/>router://running-config<br/>controlled by the APP / USER"]
        p1["Prompts<br/>/troubleshoot_interface<br/>controlled by the USER"]
    end

    subgraph Srv2["SERVER 2 — another MCP server"]
        s2["Tools · Resources · Prompts"]
    end

    ca <==>|"MCP · 1:1"| Srv1
    cb <==>|"MCP · 1:1"| Srv2

    subgraph Stack["Every Client ↔ Server link runs on two layers"]
        direction TB
        d["DATA LAYER — JSON-RPC 2.0<br/>lifecycle · tools/resources/prompts · notifications"]
        tr["TRANSPORT LAYER<br/>stdio (local subprocess)  ·  Streamable HTTP (remote: POST + SSE)"]
        d --> tr
    end

    ca -.->|runs on| Stack
    cb -.->|runs on| Stack

    lab["In the lab: LibreChat → Streamable HTTP → :8000/mcp (Bearer) → server → SSH → Router1"]:::muted
    Stack -.-> lab
    classDef muted fill:#f4f6f8,stroke:#b0b8c0,color:#5a6673;
```
*Caption: The Host runs the LLM plus one Client per Server (1:1). Each Server exposes Tools (model-controlled), Resources & Prompts (app/user-controlled). Every link rides the same two layers — JSON-RPC (data) over stdio or Streamable HTTP (transport); our lab uses HTTP.*

> **Deck build note:** in `Training Process.pptx` this slide is drawn as **native PowerPoint shapes** (deck theme: navy/cyan slate, Noto Sans), not the mermaid image above. Regenerate with `python3 scripts/redraw_arch_diagram.py`. The mermaid above is kept as the editable spec.

---

### Slide 26 — JSON-RPC 2.0 Message Types
**Fixes:** slide shows a notification blob only; participants don't see how request/response/notification differ (the `id` correlation).
**Type:** sequenceDiagram

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant S as Server

    rect rgb(232,242,253)
    Note over C,S: 1. Request + 2. Response — correlated by "id"
    C->>S: {"jsonrpc":"2.0","id":1,"method":"tools/call","params":{…}}
    S-->>C: {"jsonrpc":"2.0","id":1,"result":{…}}
    end

    rect rgb(232,246,239)
    Note over C,S: 3. Notification — one-way, NO "id", no reply expected
    S->>C: {"jsonrpc":"2.0","method":"notifications/tools/list_changed"}
    end
```
*Caption: Requests carry an `id`; the matching response echoes it. Notifications drop the `id` entirely — fire-and-forget, used for live updates.*

---

### Slide 27 — Transport Mechanisms (stdio vs Streamable HTTP)
**Fixes:** overlapping text; participants don't see local vs remote, or which one the lab uses.
**Type:** flowchart (two variants)

```mermaid
flowchart TB
    subgraph Stdio["stdio transport — LOCAL"]
        direction LR
        h1[Host] -->|launches as subprocess| s1[Server]
        h1 -->|writes stdin| s1
        s1 -->|writes stdout| h1
        n1[No network config · low latency]:::muted
    end

    subgraph Http["Streamable HTTP transport — REMOTE  ⟵ the lab uses this"]
        direction LR
        h2[Host / Client] -->|HTTP POST /mcp<br/>Authorization: Bearer| s2[Server]
        s2 -->|Server-Sent Events stream| h2
        n2[Different machines · bearer token / API key / OAuth]:::muted
    end

    classDef muted fill:#f4f6f8,stroke:#b0b8c0,color:#5a6673;
```
*Caption: stdio = server runs as a local subprocess (I/O over pipes). Streamable HTTP = client and server on different machines, POST + SSE, authenticated. Our workshop server runs HTTP at `:8000/mcp` with a bearer token.*

---

### Slide 28 / 29 — MCP Protocol Lifecycle (all 4 phases)
**Fixes:** the four phases are separate cards; participants don't see them as one ordered conversation.
**Type:** sequenceDiagram

```mermaid
sequenceDiagram
    autonumber
    participant C as Client (Host)
    participant S as Server

    rect rgb(232,242,253)
    Note over C,S: Phase 1 — Initialization (version + capability handshake)
    C->>S: initialize {protocolVersion, capabilities}
    S-->>C: result {serverInfo, capabilities}
    C->>S: notifications/initialized
    end

    rect rgb(232,246,239)
    Note over C,S: Phase 2 — Discovery (what can this server do?)
    C->>S: tools/list
    S-->>C: [get_interfaces, dynamic_show, …]
    C->>S: resources/list · prompts/list
    S-->>C: [router://running-config, …] · [/troubleshoot_interface, …]
    end

    rect rgb(255,247,232)
    Note over C,S: Phase 3 — Execution (do the work, repeatable)
    C->>S: tools/call {name:"get_interfaces"}
    S-->>C: result {interface table}
    end

    rect rgb(244,246,248)
    Note over C,S: Phase 4 — Termination (graceful close)
    C->>S: shutdown
    S-->>C: result {}
    C->>S: exit (notification)
    end
```
*Caption: One session, four phases — shake hands, discover capabilities, call them as needed, then close cleanly.*

---

## C. The six primitives

### NEW 30a / Slide 30–31 — Six primitives, three control points
**Fixes:** the "overall picture" for primitives — who is actually in control of each, mapped to the lab.
**Type:** flowchart (grouped by controller)

```mermaid
flowchart TB
    subgraph Model["Controlled by the MODEL"]
        tools["Tools<br/>get_interfaces, configure_interface<br/>→ the LLM decides to call these"]
    end
    subgraph AppUser["Controlled by the APP / USER"]
        res["Resources<br/>router://running-config<br/>→ the host/user attaches these as context"]
        prm["Prompts<br/>/troubleshoot_interface<br/>→ the user picks these templates"]
    end
    subgraph Server["Controlled by the SERVER"]
        notif["Notifications<br/>tools/list_changed, resources/updated<br/>→ the server pushes these"]
        elic["Elicitation<br/>confirm-before-config-change<br/>→ the server asks, the USER answers"]
        samp["Sampling<br/>(lecture only)<br/>→ the server asks, the MODEL answers"]
    end

    note["Same 6 words, 3 owners.<br/>Ask 'who is in control?' and each primitive falls into place."]:::muted
    Server -.-> note
    classDef muted fill:#f4f6f8,stroke:#b0b8c0,color:#5a6673;
```
*Caption: Six primitives sort into three control points — the model calls Tools; the app/user supplies Resources & Prompts; the server drives Notifications, Elicitation, and Sampling.*

---

### Slide 32 / 33 — Tools (discovery → invocation → validation → result)
**Fixes:** slide shows JSON only; the call flow (who validates, when) isn't drawn.
**Type:** sequenceDiagram

```mermaid
sequenceDiagram
    autonumber
    participant LLM
    participant C as Client
    participant S as Server
    participant R as Router1

    C->>S: tools/list
    S-->>C: get_interfaces {inputSchema}
    Note over LLM,C: LLM sees the schema, decides to call
    LLM->>C: call get_interfaces
    C->>S: tools/call {name:"get_interfaces"}
    S->>S: Validate args against JSON Schema
    S->>R: SSH — show ip interface brief
    R-->>S: interface table
    S-->>C: result {content:[{type:"text", …}]}
    C-->>LLM: tool result → final answer
```
*Caption: The model discovers a tool's schema, calls it, the server validates the inputs, runs the action, and returns a structured result the model reads.*

---

### Slide 34 — Tools: FastMCP mapping (the docstring IS the prompt)
**Fixes:** participants miss that the Python function *becomes* the tool contract.
**Type:** flowchart (mapping)

```mermaid
flowchart LR
    subgraph Py["Python function (server code)"]
        direction TB
        fn["def get_interfaces(ctx) -> str"]
        doc["&quot;&quot;&quot;Get all router interfaces<br/>and their status<br/>(show ip interface brief).&quot;&quot;&quot;"]
        hint["type hints: ctx: Context -> str"]
        ann["@mcp.tool(readOnlyHint=True)"]
    end
    subgraph Wire["What the LLM receives (tools/list)"]
        direction TB
        nm["name: get_interfaces"]
        de["description: (the docstring)"]
        sc["inputSchema: (generated from hints)"]
        rh["annotations: readOnlyHint"]
    end

    fn --> nm
    doc --> de
    hint --> sc
    ann --> rh
    warn["So: write the docstring deliberately —<br/>it is the prompt the model reads."]:::muted
    Wire -.-> warn
    classDef muted fill:#f4f6f8,stroke:#b0b8c0,color:#5a6673;
```
*Caption: FastMCP turns the function name into the tool name, the docstring into the description the LLM reads, and the type hints into the JSON Schema. The docstring is prompt engineering.*

---

### Slide 35 / 36 — Resources (app-controlled context + subscriptions)
**Fixes:** slide shows read JSON only; the list/read/subscribe/update lifecycle isn't drawn.
**Type:** sequenceDiagram

```mermaid
sequenceDiagram
    autonumber
    participant U as User / Host
    participant C as Client
    participant S as Server
    participant R as Router1

    C->>S: resources/list
    S-->>C: router://interfaces · router://running-config · router://baseline
    U->>C: attach router://running-config as context
    C->>S: resources/read {uri:"router://running-config"}
    S->>R: SSH — show running-config
    R-->>S: config text
    S-->>C: contents [{uri, mimeType, text}]

    rect rgb(232,246,239)
    Note over C,S: Live updates via subscription
    C->>S: resources/subscribe {uri:"router://running-config"}
    Note over S: config changes later …
    S->>C: notifications/resources/updated {uri}
    C->>S: resources/read (re-fetch)
    end
```
*Caption: Resources are read-only context the app/user chooses to attach. Subscribe once and the server notifies the client whenever that resource changes.*

---

### Slide 37 / 38 — Prompts (user-controlled templates)
**Fixes:** slide shows JSON; participants don't see prompts as user-triggered, parameterized templates.
**Type:** sequenceDiagram

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant C as Client (Host)
    participant S as Server
    participant LLM

    C->>S: prompts/list
    S-->>C: /troubleshoot_interface · /audit_router_config
    U->>C: pick /troubleshoot_interface, interface = Gig0/1
    C->>S: prompts/get {name, arguments:{interface:"Gig0/1"}}
    S-->>C: messages [ …step-by-step troubleshooting plan… ]
    C->>LLM: seed the conversation with those messages
    Note over U,LLM: The user chose the workflow — the template expands with their argument.
```
*Caption: Prompts are reusable, parameterized templates the user invokes (like a slash command). The server fills in the arguments and returns ready-to-run messages.*

---

### Slide 39 — Elicitation (server asks, user answers) + graceful degrade
**Fixes:** participants confuse elicitation with prompts; and don't know what happens on clients (LibreChat) that lack the capability.
**Type:** sequenceDiagram

```mermaid
sequenceDiagram
    autonumber
    participant LLM
    participant C as Client (Host)
    participant U as User
    participant S as Server
    participant R as Router1

    LLM->>C: call create_loopback {id: 99}
    C->>S: tools/call {name:"create_loopback"}
    S->>S: destructive change → confirm gate

    alt Client supports elicitation (e.g. Inspector)
        S->>C: elicitation/request {prompt:"Apply Loopback99 to Router1?"}
        C->>U: show confirm dialog
        U-->>C: yes
        C-->>S: result {input: "yes"}
        S->>R: SSH — configure loopback
        R-->>S: applied
        S-->>C: result "Loopback99 created"
    else Client has NO elicitation capability (LibreChat)
        Note over S: degrade gracefully — do not hang —<br/>follow server policy (proceed / refuse per config)
        S-->>C: result (per configured default)
    end
```
*Caption: Elicitation lets the server pause mid-tool to ask the user a question. Clients without the capability don't break — the server degrades gracefully instead of hanging.*

---

### Slide 40 — Notifications (server-controlled, one-way)
**Fixes:** participants don't see what triggers each notification in the real server.
**Type:** sequenceDiagram

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant S as Server

    rect rgb(255,247,232)
    Note over C,S: Capability changed — e.g. enable_config_tools(true)
    S->>C: notifications/tools/list_changed
    C->>S: tools/list (re-discover)
    S-->>C: now includes configure_interface, create_loopback
    end

    rect rgb(232,246,239)
    Note over C,S: Subscribed resource changed
    S->>C: notifications/resources/updated {uri:"router://running-config"}
    end

    rect rgb(232,242,253)
    Note over C,S: Long-running op progress
    S->>C: notifications/progress {progressToken, progress:50, total:100}
    end
```
*Caption: Notifications are one-way pushes from server to client — new tools appeared, a resource changed, or work is progressing. No `id`, no reply.*

---

### NEW 40a — Sampling (lecture only: server asks, model answers)
**Fixes:** rounds out the six primitives; sampling is easy to confuse with tools.
**Type:** sequenceDiagram

```mermaid
sequenceDiagram
    autonumber
    participant S as Server
    participant C as Client (Host)
    participant LLM

    Note over S,LLM: Server needs a bit of reasoning mid-task
    S->>C: sampling/createMessage {messages}
    C->>LLM: run completion (host controls model & cost)
    LLM-->>C: generated text
    C-->>S: result {content}
    Note over S,C: The host stays in control — it can approve, edit, or deny.
```
*Caption: Sampling flips the direction — the server asks the client's model to think. The host mediates, so it keeps control of cost and safety. (Lecture only; not consumed by the lab client.)*

---

## D. The lab + end-to-end flow (the biggest gap)

### NEW Big-Picture — one Client, one Server, one Router (high-level overview)
**Fixes:** participants need the simplest possible mental model first — before the detailed topology. One client desktop, one server desktop, one router, two hops.
**Type:** native pptx shapes (deck theme), grounded in `mcp-workshop-topo.png`.

> **Deck build note:** this slide is drawn as **native PowerPoint shapes** (no mermaid), placed just before the detailed Lab-Topo slide. Regenerate with `python3 scripts/draw_bigpicture_slide.py`.

Flow it shows:
`MCP-Client desktop (172.18.0.2) — Host app: LibreChat → MCP Client`  →  **MCP · Streamable HTTP · :8000/mcp · Bearer** (across the lab network: public-internet2 → switch)  →  `MCP-Server desktop (172.18.1.2) — MCP server script (FastMCP) → Tools`  →  **Netmiko SSH · show/config**  →  `Router1 (172.18.2.6) — Cisco IOS`.

One-liner (footnote on the slide): *you ask LibreChat → its MCP client calls the server over MCP → the server's tools SSH into Router1 → the answer comes back to you.*

---

### NEW Lab-Topo — Workshop lab topology
**Fixes:** meet-notes core ask — participants need to see the sandbox: what runs where, ports, auth, and the SSH boundary to the router.
**Type:** flowchart (topology with subgraphs)

```mermaid
flowchart LR
    user([Participant<br/>browser])

    subgraph Sandbox["Criterion SDCloud sandbox"]
        direction TB
        subgraph HostBox["Host machine"]
            lc["LibreChat<br/>UI :3080  ·  API"]
            llmp[LLM provider]
            lc --- llmp
        end
        subgraph SrvBox["MCP server machine"]
            srv["Router MCP server<br/>uvicorn :8000<br/>/mcp (Streamable HTTP)"]
        end
        rtr["Router1<br/>172.18.2.6<br/>admin/admin"]

        lc -->|"HTTP POST /mcp<br/>Authorization: Bearer cisco-mcp-workshop"| srv
        srv -->|"Netmiko SSH<br/>show / config commands"| rtr
    end

    user -->|https| lc

    note["Health check: GET / on :8000<br/>Verify: ./smoke_test.sh  ·  MCP Inspector"]:::muted
    SrvBox -.-> note
    classDef muted fill:#f4f6f8,stroke:#b0b8c0,color:#5a6673;
```
*Caption: The whole lab in one picture — your browser → LibreChat (:3080) → MCP server (:8000/mcp, bearer token) → SSH → Router1. LibreChat is the MCP host/client; the server drives the real device.*

---

### NEW Lab-E2E — End-to-end query flow ("show me the interfaces")
**Fixes:** THE money diagram — participants finally see how one typed question becomes a tool call, an SSH command, and an answer. Ties every component together.
**Type:** sequenceDiagram

```mermaid
sequenceDiagram
    autonumber
    actor U as Participant
    participant LC as LibreChat (Host + Client)
    participant LLM
    participant S as MCP Server
    participant R as Router1

    U->>LC: "Show me the interfaces on Router1"
    Note over LC,S: On connect, LibreChat already ran tools/list
    LC->>LLM: user message + available tools (get_interfaces, …)
    LLM-->>LC: tool_call: get_interfaces
    LC->>S: tools/call {name:"get_interfaces"} (HTTP POST /mcp, bearer)
    S->>S: run in worker thread (Netmiko is blocking)
    S->>R: SSH — show ip interface brief
    R-->>S: interface table (text)
    S-->>LC: result {content:[{type:"text", text:"…"}]}
    LC->>LLM: tool result
    LLM-->>LC: natural-language summary
    LC-->>U: rendered answer
    Note over U,R: One question → discovery → tool call → SSH → result → answer.
```
*Caption: A single question travels: LibreChat gives the LLM the tool list, the LLM picks `get_interfaces`, LibreChat calls the server, the server SSHes to Router1, and the result flows back as a plain-English answer.*

---

### NEW Lab-Config — Config change with the safety gate (rollback-aware)
**Fixes:** shows the production-safe pattern — confirm before change, snapshot for rollback, notify after. This is the destructive-tool story.
**Type:** sequenceDiagram

```mermaid
sequenceDiagram
    autonumber
    actor U as Participant
    participant LC as LibreChat (Host)
    participant LLM
    participant S as MCP Server
    participant R as Router1

    U->>LC: "Create Loopback99 on Router1"
    LC->>LLM: message + tools (config tools enabled)
    LLM-->>LC: tool_call: create_loopback {id:99}
    LC->>S: tools/call {name:"create_loopback"} (destructiveHint)

    S->>S: _confirm_change() — elicitation gate
    alt confirmed (or graceful default)
        S->>R: snapshot running-config → baseline (rollback anchor)
        S->>R: SSH config — interface Loopback99 …
        R-->>S: applied
        S-->>LC: result "Loopback99 created (MCP_CREATED)"
        S->>LC: notifications/tools/list_changed
        S->>LC: notifications/resources/updated {router://running-config}
    else declined
        S-->>LC: result "change cancelled — no config applied"
    end
    LC-->>U: outcome + what changed
    Note over S,R: reset_lab.py --apply removes MCP_CREATED loopbacks between cohorts.
```
*Caption: Config-writing tools are gated: confirm first, snapshot a rollback baseline, apply, then push notifications so the client re-discovers state. Safe-by-default, auditable, reversible.*

---

### NEW Inspector — What the MCP Inspector shows (end-of-session debugger)
**Fixes:** the Inspector is demoed last; a simple map of its tabs orients participants to what they're seeing.
**Type:** flowchart

```mermaid
flowchart LR
    insp["MCP Inspector<br/>(npx @modelcontextprotocol/inspector)"]
    insp -->|"Streamable HTTP<br/>http://server:8000/mcp<br/>Bearer token"| srv["Router MCP server"]

    subgraph Tabs["What you can inspect"]
        t1["Tools — list & call<br/>get_interfaces, dynamic_show, …"]
        t2["Resources — browse & read<br/>router://running-config"]
        t3["Prompts — expand templates<br/>/troubleshoot_interface"]
        t4["Notifications — watch live<br/>list_changed, updated"]
    end

    srv --- Tabs
    note["Same protocol as LibreChat, but raw —<br/>you see the actual JSON-RPC on the wire."]:::muted
    Tabs -.-> note
    classDef muted fill:#f4f6f8,stroke:#b0b8c0,color:#5a6673;
```
*Caption: The Inspector connects to the same `/mcp` endpoint and exposes each primitive on its own tab — the clearest way to watch the raw JSON-RPC once you understand the flow.*

---

## Placement summary (where the new inserts go)

| New diagram | Suggested placement |
|---|---|
| **18a** Value proposition | after slide 19 (MCP M+N solution) |
| **30a** Six primitives / three control points | at slide 30–31 (replaces/augments the primitives intro) |
| **40a** Sampling | after slide 40 (notifications), before SDK section |
| **Lab-Topo** | start of the lab section (after slide 44/45 SDK, before hands-on) |
| **Lab-E2E** | immediately after Lab-Topo — the anchor diagram for the whole workshop |
| **Lab-Config** | after Lab-E2E, when introducing config tools / Lab 5 |
| **Inspector** | end of session, with the Inspector demo |

## Existing slides intentionally left as-is (already have a good diagram)
7, 8, 9, 11, 16, 19, 21, 24, 44, 45 — these render clearly today; only fix layout/text overflow, no new mermaid needed.
