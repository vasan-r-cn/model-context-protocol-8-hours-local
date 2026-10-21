# Spike D1 — fast-agent as the workshop harness

**Date:** 30 Sep 2026 · **Result: GREEN.** fast-agent replaces LibreChat with no change to the MCP server.

Run against the existing 4h server (`code/server`, 7 tools) on `:8099`. The lab
routers are unreachable from the build host, so device calls fail at SSH — that
is expected and is itself useful: it proves errors travel back as tool results.

## Reproduce from a clean shell

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python fast-agent-mcp        # installed 0.10.41

# terminal 1 — the MCP server
cd code/server && PORT=8099 ./run.sh

# terminal 2 — no config file, no API key
.venv/bin/fast-agent go \
  --url http://127.0.0.1:8099/mcp \
  --auth cisco-mcp-workshop \
  --model passthrough --no-home \
  -m '***CALL_TOOL get_router_info {}'
```

## Findings that change how the labs are written

| # | Finding | Consequence |
|---|---|---|
| 1 | **Pin `fast-agent-mcp==0.10.41`.** `pip` on the host's default Python 3.10 resolves to 0.2.36 — a different CLI and a different config schema. | Pre-flight installs with `uv` + Python 3.12. Do not let `pip3 install fast-agent-mcp` be the instruction. |
| 2 | `fast-agent go --url … --auth …` works with **no config file at all**. | Lab 1 opens with one command. Config files arrive in Lab 3, when there are two servers to name. |
| 3 | **`--model passthrough` + `***CALL_TOOL <name> <json>`** invokes a tool deterministically with no LLM and no API key. | Pre-flight check, per-lab smoke test and CI gate all become scriptable. Removes OpenRouter from the critical path of "is my server wired up". |
| 4 | With `-c <config>`, servers must **also** be named with `--servers <name>`. Without it the agent starts with zero tools and a misleading "No tools are currently available". | Every lab guide shows `-c` and `--servers` together. This is a guaranteed support call otherwise. |
| 5 | Tool namespace separator is **`__`** (double underscore): `my_server__create_loopback`. | Worksheets and answer keys use `__`. |
| 6 | `elicitation.mode` accepts `forms` \| `auto-cancel` \| `none`, and **defaults to `none`** — hyphen, not underscore. | Elicitation is OFF unless the config says so. See below. |
| 7 | `${ENV_VAR}` substitution works in the config, including inside the `Authorization` header. | One config file ships to every seat; only `MCP_SERVER_URL` / `MCP_AUTH_TOKEN` differ. |

## The Lab 4 beat, proven on the wire

Same tool, same server, one config line different:

```bash
# elicitation: mode: auto-cancel   → the gate fires
{'result': 'Change cancelled by user.'}          # 11ms, no SSH attempted

# elicitation: mode: none          → no gate, straight to the device
{'result': 'Error talking to Router1: TCP connection to device failed. …'}
```

With `mode: none` the client does not advertise the capability, the server's
`_confirm_change` takes its degradation path, and the change proceeds — the
LibreChat behaviour the workshop has been explaining all along. One line of
client config is the whole difference between a confirm gate and no gate.

**This is a regression test, not just a demo.** Both runs are one-shot and
scriptable, so the gate can be asserted in CI.

## Not yet verified

- OpenRouter provider end to end (needs a funded key) — config key `openrouter` exists at top level.
- `forms` mode interactively (needs a TTY; `auto-cancel` proves the capability negotiation).
- Two servers in one config with namespacing — Lab 3, blocked on the pyATS spike.
