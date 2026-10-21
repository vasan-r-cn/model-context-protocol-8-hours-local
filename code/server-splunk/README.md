# code/server-splunk — a vendor MCP server you did not write

Module 5 point: you don't write every server. This is a real, **unofficial**,
community Splunk MCP server — [`splunk/splunk-mcp-server2`](https://github.com/splunk/splunk-mcp-server2)
(MIT) — that you install and consume on its own terms.

## Shape

- It runs **locally on your desktop** and talks to your pod's Splunk over the
  Splunk REST API (`:8089` on `cclorchestrator78`).
- It speaks **SSE** (not Streamable HTTP), serving `http://localhost:8050/sse`.
- It exposes **7 tools**: `validate_spl`, `search_oneshot`, `search_export`,
  `get_indexes`, `get_saved_searches`, `run_saved_search`, `get_config`.
- Auth to Splunk is the server's business (`SPLUNK_USERNAME`/`PASSWORD` or
  `SPLUNK_TOKEN` in its `.env`). The MCP client→server hop is local, no bearer.

## Install & run

```bash
cd code/server-splunk
./setup.sh                                  # clones upstream/, builds venv
cp .env.example upstream/python/.env        # then edit: pod Splunk host + creds
./run.sh                                    # serves SSE on :8050
```

## Connect fast-agent

```bash
cd ../client-fastagent
fast-agent go -c lab-splunk.yaml --servers splunk --model openrouter.anthropic/claude-sonnet-4
# in session: /tools   ->  splunk__get_indexes, splunk__search_oneshot, ...
```

> **Third-party code.** `upstream/` is cloned from an unofficial community repo.
> Pin `SPLUNK_MCP_REF` to a reviewed commit SHA before class, read what you run,
> and keep the Splunk account least-privilege (read-only).
