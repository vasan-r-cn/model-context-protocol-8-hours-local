# AI Agents Deployment - SD-WAN as Case study

## Deploy the SD-WAN Agent with FastAPI + LangSmith

---

## What You Will Do

Deploy the SD-WAN agent with both a REST API and an interactive chat UI running side by side. Trace every agent run in LangSmith, and confirm that both interfaces produce traces from the same agent.

---

## What You Will Learn

- How to serve an AI agent over REST and a chat UI simultaneously
- How Gradio creates a chat interface with minimal code
- How one Docker image runs multiple services through a single environment variable

---

## How It Works

```
FastAPI  (8000) --+
                      |
                      +--> SD-WAN Agent (shared) --> SD-WAN Tools --> vManage
                      |             |
Gradio UI (7862) -----+             v
                          LangSmith (traces everything)
```

Both the chat UI and the REST API call the same `run_agent()` function. LangSmith records every run regardless of which interface triggered it.

**One detail worth understanding before you start.** The agent decides where its tools come from at runtime, in `agent.py`:

```python
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL")

if MCP_SERVER_URL:
    tools = await client.get_tools()      # tools from the MCP server
else:
    tools = DIRECT_TOOLS                  # 19 tool functions imported locally
```

The same agent code runs as a single process or as a distributed service depending on one environment variable. In this deployment, Compose sets `MCP_SERVER_URL`, so the tools run in their own container.

---

## Setup

### PATH

```bash
cd ~/agentic-ai-workshop/deployment/sdwan_agent/
```

### 1. Create a `.env` file in this folder

```bash
cp ~/agentic-ai-workshop/.env ~/agentic-ai-workshop/deployment/sdwan_agent/
```

Confirm it contains all of the following, with real values on every line:

```
OPENROUTER_API_KEY=your_openrouter_api_key
FQDN=your.vmanage.hostname
VMANAGE_USERNAME=your_vmanage_username
VMANAGE_PASSWORD=your_vmanage_password
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=sdwan-workshop
```

---

## Running with Docker

### 1. Read the Compose file before running it

```bash
cat docker-compose.yml
```

### 2. Read the Dockerfile

```bash
cat Dockerfile
```

### 3. Start the stack

```bash
docker compose up --build -d
```

![](https://sdcloud-imgs.s3.amazonaws.com/sandboxes/Screenshot%202026-05-07%20170351.png)
View logs:
![](https://sdcloud-imgs.s3.amazonaws.com/sandboxes/Screenshot%202026-05-07%20170337.png)

### 4. Check both services came up

```bash
docker compose ps
docker logs sdwan-mcp
docker logs sdwan-gradio
```

**Checkpoint before continuing:**

- `docker compose ps` shows `sdwan-mcp` and `sdwan-gradio` running
- `sdwan-mcp` logs show `Uvicorn running on http://0.0.0.0:9000`


### 5. Open the chat UI 
Verify the Gradio /chat endpoint is responding before moving on(Human Interface)

```
sdwan-gradio
   ↓
Gradio :7862
   ↓
run_agent()
   ↓
MCP Client
   ↓
MCP Server :9000
   ↓
SD-WAN tools
   ↓
vManage
```

```
docker compose exec sdwan-gradio python -c "
from gradio_client import Client
c = Client('http://localhost:7862', verbose=False)
print(c.predict('Are there any devices currently down?', api_name='/chat'))
"
```
FastAPI — test this next ( Programmable API)


```
External Application
       |
       | HTTP POST :8000
       v
    FastAPI
       |
       v
  run_agent()
       |
       v
  SD-WAN Agent
       |
       v
   MCP Client
       |
       v
 MCP Server :9000
       |
       v
   SD-WAN Tool
       |
       v
    vManage
```

```
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Are there any devices currently down?"}'
```

Test MCP Server directly (tools)


```
                    ┌──────────────┐
                    │   Gradio     │
                    │    :7862     │
                    └──────┬───────┘
                           │
                           │
                    ┌──────▼───────┐
                    │ SD-WAN Agent │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ MCP Client   │
                    └──────┬───────┘
                           │
                           │ MCP :9000
                           ▼
                    ┌──────────────┐
                    │ MCP Server   │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ SD-WAN Tools │
                    └──────┬───────┘
                           │
                           ▼
                        vManage
```

### open the cloud flare tunnel URL in your browser to access the chat UI.

```
                         INTERNET
                            │
                            ▼
                     ┌────────────┐
                     │ Cloudflare │
                     └─────┬──────┘
                           Tunnel
                            │
                            ▼
                    ┌───────────────┐
                    │ Gradio :7862  │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  SD-WAN Agent │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ MCP Client    │
                    └───────┬───────┘
                            │
                       Docker network
                            │
                            ▼
                    ┌───────────────┐
                    │ MCP Server    │
                    │    :9000      │
                    └───────┬───────┘
                            │
                            ▼
                         vManage                         INTERNET
                            │
                            ▼
                     ┌────────────┐
                     │ Cloudflare │
                     └─────┬──────┘
                           Tunnel
                            │
                            ▼
                    ┌───────────────┐
                    │ Gradio :7862  │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  SD-WAN Agent │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ MCP Client    │
                    └───────┬───────┘
                            │
                       Docker network
                            │
                            ▼
                    ┌───────────────┐
                    │ MCP Server    │
                    │    :9000      │
                    └───────┬───────┘
                            │
                            ▼
                         vManage
```


```bash
docker logs sdwan-tunnel
```

![Screenshot 2026-05-07 170253](https://sdcloud-imgs.s3.amazonaws.com/sandboxes/Screenshot%202026-05-07%20170253.png)
---

## Test the Agent


![Screenshot 2026-05-07 171956](https://sdcloud-imgs.s3.amazonaws.com/sandboxes/Screenshot%202026-05-07%20171956.png)
open the gradio UI and ask questions about the SD-WAN environment. The agent will use the tools to fetch real-time data from vManage and respond.

Try these questions:
- `"Are there any devices currently down?"`
- `"Show me all active critical alarms"`
- `"Get tunnel status for device 10.1.1.1"`
- `"Generate a full audit report"`

---


### 6. Verify LangSmith is receiving traces

Tracing failing is silent — the agent answers normally whether or not runs are
being recorded. Confirm the settings reached the container:

```bash
docker compose exec sdwan-gradio env | grep LANGSMITH
```

Then open your `LANGSMITH_PROJECT` in LangSmith. A run named
`single_agent_gradio_run` should appear within a few seconds of the question you
just asked.

**Checkpoint:**

- `LANGSMITH_TRACING=true` and a non-empty `LANGSMITH_API_KEY` are set in the container
- A run appears in the expected project
- Opening the run shows the tool call you saw in the `sdwan-mcp` logs

---

## Understanding the Project Files

Nine files, three of which do the real work. Read them in this order — each one
depends on the one before it.

### `tools.py` — the single source of truth (607 lines)

Nineteen LangChain tools, each a decorated async function that talks to vManage:

```python
@tool()
async def get_inventory(fqdn: str | None = None) -> Dict[str, Any]:
    """Fetch full SD-WAN device inventory."""
    fqdn = fqdn or DEFAULT_FQDN
    logger.info(f"Tool called: get_inventory with {fqdn}")
    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)
    client = await vmanage_login(base_url, VMANAGE_USERNAME, VMANAGE_PASSWORD)
    try:
        devices = await vmanage_get(client, base_url, "/dataservice/device")
        return {"inventory": devices}
    finally:
        await client.aclose()
```

Every tool follows that shape: resolve the target, log the call, validate,
authenticate, fetch, close the session in `finally`. Shared helpers at the top
handle URL normalisation, login, and resolving a device name to an internal ID.

**This file is why the deployment can run two ways.** These are ordinary
LangChain tools, so an agent can import and use them directly — and they can also
be wrapped and served over MCP. One definition, two topologies.

> The `logger.info(f"Tool called: ...")` line is what you grep for in step 7. It
> lives here, in the tool itself, which is why it appears in the tool server's
> logs rather than the agent's.

### `mcp_server.py` — the same tools, over the network (158 lines)

A thin wrapper. It imports each tool from `tools.py` under an underscore alias,
then re-exposes it as an MCP tool:

```python
from tools import get_inventory as _get_inventory

async def _call(tool, **kwargs):
    return await tool.ainvoke({k: v for k, v in kwargs.items() if v is not None})

@mcp.tool()
async def get_inventory(fqdn: str | None = None) -> dict[str, Any]:
    """Retrieves SD-WAN inventory from vManage."""
    return await _call(_get_inventory, fqdn=fqdn)
```

The `_call` helper strips `None` values so optional arguments are omitted rather
than passed as null.

Note the server construction:

```python
mcp = FastMCP(
    "SD-WAN MCP Server",
    host=os.getenv("MCP_HOST", "0.0.0.0"),
    port=int(os.getenv("MCP_PORT", "9000")),
    stateless_http=True,
    json_response=True,
)
```

**`stateless_http=True` explains something you saw in step 7.** Because no session
state is retained between requests, the client re-runs `ListToolsRequest` on every
call, and the log shows `Terminating session: None` each time. That is the
configured behaviour, not a fault — it trades a little repeated discovery for a
server that holds nothing between requests and can be restarted or scaled freely.

### `agent.py` — the reasoning layer (196 lines)

Three responsibilities.

**1. Choose the tool source.** The switch that makes both topologies possible:

```python
if MCP_SERVER_URL:
    client = MultiServerMCPClient({"sdwan": {"transport": "http", "url": MCP_SERVER_URL}})
    tools = await client.get_tools()
else:
    tools = DIRECT_TOOLS      # imported straight from tools.py
```

**2. Build the agent once.** The agent is cached in a module global behind an
`asyncio.Lock`, so tool discovery happens on first use rather than per request,
and two simultaneous first requests cannot both build one.

**3. Define the system prompt.** A long, explicit prompt telling the agent it
*must* use tools for operational questions and must not guess. Worth reading in
full — it is the reason this agent reliably reaches for tools instead of
answering from general knowledge.

It also enforces its dependencies at import:

```python
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set")
if not os.getenv("LANGSMITH_API_KEY"):
    raise RuntimeError("LANGSMITH_API_KEY not set")
```

Tracing is therefore a hard startup requirement. Defensible — an agent you cannot
trace arguably should not run — but it does mean LangSmith being unreachable takes
your agent down with it.

### The two front doors

| File | Serves | Port |
|---|---|---|
| `app.py` (48 lines) | Gradio chat UI, for humans | 7862 |
| `api.py` (15 lines) | FastAPI `POST /ask`, for other systems | 8000 |

Both call the same `run_agent()`. `app.py` reads every setting from the
environment — including `share`, which defaults to `false`. `api.py` is fifteen
lines: a Pydantic model for the request body, one endpoint, one call.

### `start.sh` — the role switch

Chooses which service this container becomes, from one variable:

```bash
if [ "$SERVICE_MODE" = "mcp" ]; then
    exec python -u mcp_server.py
fi
exec python -u app.py
```

Two branches. There is no `api` branch, which is why the REST API has to be
started by hand in step 6 and why adding one is Exercise 4.

### `Dockerfile` — one image, line by line

```dockerfile
FROM python:3.12-slim
```
Slim rather than full: no compilers or docs, a much smaller image. Fine here
because nothing in `requirements.txt` needs to build from source.

```dockerfile
WORKDIR /app
```
Every later `COPY` and the final `CMD` are relative to this. It is why `start.sh`
can be run as `./start.sh`.

```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SERVICE_MODE=app \
    GRADIO_PORT=7862 \
    GRADIO_SHARE=false \
    MCP_PORT=9000
```

| Variable | Why it matters here |
|---|---|
| `PYTHONDONTWRITEBYTECODE` | No `.pyc` files — pointless in a container that is rebuilt, not edited |
| `PYTHONUNBUFFERED` | **The important one.** Without it Python buffers stdout and `docker logs` shows nothing until the buffer flushes. Every log line you relied on in step 7 depends on this |
| `PIP_NO_CACHE_DIR` | Do not keep the pip download cache in the image layer |
| `SERVICE_MODE=app` | The default role. Compose overrides it per service |
| `GRADIO_SHARE=false` | Gradio's public sharing is off unless explicitly enabled |

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
```
`--no-install-recommends` skips optional extras. Deleting the apt lists in the
*same* `RUN` matters: a separate `RUN rm` would leave them in the earlier layer,
so the image would still carry them. `curl` is what makes a container healthcheck
possible.

```dockerfile
RUN groupadd --system app && useradd --system --gid app app
```
Creates a system user with no login shell and no home directory by default.
Nothing runs as this user yet — that comes later.

```dockerfile
COPY requirements.txt .
RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt
```
**Copy requirements before the source, not with it.** Docker caches layers, and a
layer is invalidated when its inputs change. Because only `requirements.txt` was
copied at this point, editing `agent.py` does not invalidate the install layer —
you saw this working in your build output as `CACHED [6/9] ... pip install`. Copy
everything first and every code change reinstalls every dependency.

```dockerfile
COPY --chown=app:app . .
```
Now the source. `--chown` sets ownership during the copy rather than needing a
separate `RUN chown` layer afterwards.

```dockerfile
RUN chmod +x start.sh
```
Belt and braces — the file may lose its execute bit depending on how it reached
the build context.

```dockerfile
RUN mkdir -p /home/app/.cache/huggingface/gradio/frpc && \
    curl -fsSL https://cdn-media.huggingface.co/frpc-gradio-0.3/frpc_linux_amd64 \
         -o /home/app/.cache/huggingface/gradio/frpc/frpc_linux_amd64_v0.3 && \
    chmod +x ... && chown -R app:app /home/app/.cache
```
`frpc` is the helper Gradio uses for `share=True` public links. This deployment
sets `GRADIO_SHARE=false`, so it is never used. It costs a build-time dependency
on a third-party CDN, an unaudited binary in the image, and a build that fails if
that CDN is down — all for a feature this deployment does not use.

```dockerfile
USER app
CMD ["./start.sh"]
```
Everything above ran as root; everything from here runs unprivileged. That
ordering is deliberate — you cannot `apt-get install` as `app`. If the process is
ever compromised, it is not root inside the container.

`CMD` rather than `ENTRYPOINT` means it can be overridden on the command line,
which is exactly what you did when you ran `uvicorn` directly in step 6.

---

### `docker-compose.yml` — how the services find each other

Two services, both from the same image, differing only in environment.

```yaml
  sdwan-mcp:
    build: .
    image: sdwan-agent:latest
```
`build` and `image` together: build from this directory, and tag the result
`sdwan-agent:latest`. The second service then reuses that tag rather than
building again — which is why your build output showed most steps `CACHED`.

```yaml
    env_file:
      - .env
    environment:
      FQDN: ${FQDN:-}
      VMANAGE_USERNAME: ${VMANAGE_USERNAME:-admin}
      VMANAGE_PASSWORD: ${VMANAGE_PASSWORD:-admin123}
      SERVICE_MODE: mcp
      MCP_HOST: 0.0.0.0
      MCP_PORT: 9000
      MCP_TRANSPORT: streamable-http
```

`SERVICE_MODE: mcp` is the whole difference in role — `start.sh` branches on it and
runs `mcp_server.py` instead of `app.py`.

`MCP_HOST: 0.0.0.0` binds all interfaces inside the container. Binding `127.0.0.1`
would make the server unreachable from the other container, since each has its own
loopback.

**Note which secrets live here:** this service gets the vManage credentials and
never sees the LLM key. That is the split worth keeping — the tool server talks to
your infrastructure, the agent talks to the model, and neither holds the other's
credentials.

```yaml
    ports:
      - "9000:9000"
    restart: unless-stopped
```
`host:container`. This is the line the Notes suggest removing: the agent reaches
the tool server by service name over the internal network, so publishing 9000 to
the host only widens exposure of the credential-holding service.

`restart: unless-stopped` brings the container back after a crash or a host reboot,
but respects a deliberate `docker compose stop`.

```yaml
  sdwan-gradio:
    environment:
      SERVICE_MODE: app
      MCP_SERVER_URL: http://sdwan-mcp:9000/mcp
      GRADIO_PORT: 7862
      GRADIO_SHARE: "false"
```

**`http://sdwan-mcp:9000/mcp` is the most important line in the file.** `sdwan-mcp`
is not a hostname you configured anywhere — Compose creates a network for the
project and registers each service name on its DNS. The `9000` here is the
*container* port, not the published one, so this keeps working even after you
remove the `ports:` block.

Setting `MCP_SERVER_URL` at all is what puts `agent.py` into distributed mode.
Delete this one line and the same image runs the agent with tools bundled locally.

Note `GRADIO_SHARE: "false"` is quoted. In YAML, bare `false` is a boolean; the
code reads this as a string and lowercases it, so quoting keeps the types honest.

```yaml
    depends_on:
      - sdwan-mcp
```
Controls **start order only** — it waits for the container to be created, not for
the MCP server to be ready to serve. There is no healthcheck, so on a slow start
the agent could come up first. It does not break anything here because tool
discovery happens lazily on the first question, by which point the server is up.
If you added a healthcheck, `depends_on` could wait for `condition: service_healthy`
instead.

**One subtlety that catches people, and it is what makes Exercise 3 work.** Each
service both loads `.env` wholesale and sets specific variables explicitly:

```yaml
env_file:
  - .env
environment:
  VMANAGE_PASSWORD: ${VMANAGE_PASSWORD:-admin123}
```

The `environment:` block takes precedence over `env_file:`. And `${VMANAGE_PASSWORD}`
is substituted by Compose *before* the container starts, reading from your shell or
from the `.env` sitting beside the Compose file. So `.env` is doing two different
jobs here: supplying variables to the container, and supplying values for
substitution.

The consequence: commenting out `VMANAGE_PASSWORD` in `.env` does not leave it
unset — the `:-admin123` default fills it in, the container starts normally, and
nothing logs that a fallback was used.

**`requirements.txt`** — pins `langchain`, `fastapi` and `uvicorn` exactly, but
leaves `langgraph` and `langchain_openrouter` loose. Worth knowing when a rebuild
behaves differently from the image you tested.


### How the tracing works, and how it differs from Langfuse

Both tools record the same thing — every model call, tool call and the reasoning
between them — but they attach to your code in fundamentally different ways.

**LangSmith here uses a decorator.** In `agent.py`:

```python
from langsmith import Client, traceable

@traceable(
    name="single_agent_gradio_run",
    metadata={
        "ui": "gradio",
        "agent_type": "single-agent",
    },
)
async def run_agent(user_prompt: str) -> str:
    ...
```

The decorator wraps the whole function. Anything that happens inside it — including
the agent's tool calls and model calls — is captured as a nested run tree, without
those inner calls knowing tracing exists. Configuration comes entirely from the
environment:

| Variable | Effect |
|---|---|
| `LANGSMITH_TRACING` | `true` turns tracing on. Set it to `false` and the decorator becomes a no-op |
| `LANGSMITH_API_KEY` | Authenticates to LangSmith. `agent.py` raises at import if it is missing |
| `LANGSMITH_PROJECT` | Which project the runs appear under |
| `LANGSMITH_ENDPOINT` | Which LangSmith instance to send to |

**Langfuse uses a callback instead.** From the observability section:

```python
from langfuse.langchain import CallbackHandler

langfuse_handler = CallbackHandler()

result = await agent.ainvoke(
    {"messages": messages},
    config={"callbacks": [langfuse_handler]}
)
```

The handler is passed *into the call* as configuration, and Langfuse also needs an
explicit `langfuse.flush()` to push buffered events.

**The practical differences:**

| | LangSmith decorator | Langfuse callback |
|---|---|---|
| Attaches at | The function boundary | Each individual agent call |
| Code change needed | One decorator above the function | Pass `config=` at every call site |
| Turning it off | An environment variable | Remove the handler from each call |
| Sending data | Automatic | Often an explicit `flush()` |
| Names the run | `name=` on the decorator | Derived, or set via a span |

Neither is better in the abstract. The decorator is less invasive and gives you one
place to control tracing. The callback is more explicit about which calls are being
traced, and lets you trace some calls and not others.

### Confirm your traces are actually arriving

Tracing failing is silent — the agent answers normally either way — so check
rather than assume:

```bash
docker compose exec sdwan-gradio env | grep LANGSMITH
```

Expect `LANGSMITH_TRACING=true`, a non-empty `LANGSMITH_API_KEY`, and the project
name you intend to use.

Then ask one question and open that project in LangSmith. A run named
`single_agent_gradio_run` should appear within a few seconds.

If nothing appears:

| Symptom | Likely cause |
|---|---|
| Agent will not start at all | `LANGSMITH_API_KEY` missing — `agent.py` raises at import by design |
| Agent answers, no runs appear | `LANGSMITH_TRACING` is not `true`, or the key is invalid |
| Runs appear under the wrong project | `LANGSMITH_PROJECT` differs from the project you are viewing |


### How a single question flows through all of it

```
You ask "Are any devices down?"
        |
   api.py  or  app.py                 <- whichever front door
        |
   agent.py :: run_agent()            <- @traceable sends the run to LangSmith
        |
   agent.py :: get_agent()            <- builds once, cached
        |
   MCP_SERVER_URL set?
        |
        +-- yes -> MultiServerMCPClient --HTTP--> mcp_server.py --> tools.py
        |                                        (other container)
        +-- no  -> DIRECT_TOOLS -------------------------------->  tools.py
                                                                    |
                                                          httpx -> vManage
```

Everything below `agent.py` is identical in both paths. The only difference is
whether the tool call crosses a network boundary — which is exactly what you
verified in step 7.

---





## Notes

- Ensure `.env` is updated before execution
- Verify all APIs are reachable
- The tool server publishes port 9000 to the host, though the agent reaches it over Compose's internal network by service name. Removing that `ports:` block makes the credential-holding service unreachable from outside the stack without affecting the agent — worth doing before this pattern goes anywhere real.
- The client and server name their transport differently and still interoperate: `agent.py` connects with `"transport": "http"` while Compose runs the server with `MCP_TRANSPORT: streamable-http`. `langchain-mcp-adapters` maps `http` onto streamable HTTP, so both are correct.
- The `Dockerfile` downloads the `frpc` binary from an external CDN. That helper exists only for Gradio's `share=True` public links, which this deployment sets to `false`. If you adapt this Dockerfile, dropping those lines removes a build-time dependency on a third-party CDN that the deployment never uses.

### Clean up

```bash
docker compose down
```

---

## What You Built

One agent, reachable two ways, with every run traced. Plus a working answer to the question Exercise 1 asks: both interfaces appear in LangSmith, but are not distinguishable from each other until you make them so.