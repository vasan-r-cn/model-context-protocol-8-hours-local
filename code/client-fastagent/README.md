# fast-agent — the workshop harness

Replaces LibreChat. It is the only client we found that consumes tools,
resources, prompts **and** elicitation, so the protocol no longer has to be
demonstrated in MCP Inspector alone.

## Install (pre-flight — already done on the lab image)

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

Python 3.12 via `uv` is required. `pip3 install fast-agent-mcp` on the system
Python 3.10 installs a much older release with a different CLI.

## Environment — load it from `.env`

The lab yaml files read `${OPENROUTER_MODEL}`, `${MCP_SERVER_URL}` and
`${MCP_AUTH_TOKEN}` by substitution, and the `--model openrouter.$OPENROUTER_MODEL`
flag reads the same var. Keep them in `.env` (not in the yaml), and load them
into your shell before running:

```bash
cp .env.example .env         # then edit: OpenRouter key + model, server url/token
set -a; . ./.env; set +a     # export everything in .env into the shell
```

`OPENROUTER_API_KEY` stays out of the yaml. `OPENROUTER_MODEL` (e.g.
`anthropic/claude-sonnet-4`) is the one place the model is set for every lab.

## Lab 1 — no config file needed

```bash
fast-agent go --url $MCP_SERVER_URL --auth $MCP_AUTH_TOKEN --model passthrough
```

## Lab 3 onward — config file, because there are two servers

```bash
export MCP_SERVER_URL=http://<server-host>:80<seat>/mcp
export MCP_AUTH_TOKEN=cisco-mcp-workshop
fast-agent go -c lab1.yaml --servers my_server
```

Always pass `--servers`. Tools are namespaced `<server>__<tool>`, e.g.
`my_server__get_interfaces`.

## Checking your wiring without spending tokens

`--model passthrough` runs no LLM. `***CALL_TOOL` invokes a tool directly:

```bash
fast-agent go -c lab1.yaml --servers my_server --model passthrough \
  -m '***CALL_TOOL my_server__get_router_info {}'
```

Use this whenever you are unsure whether a problem is your server or the model.

## In-session commands

`/mcp` servers · `/tools` · `/prompts` · `/resources` · `/help`
