# Setup & Pre-Flight

<!-- STUB: generated skeleton, not yet authored -->

**Duration:** 12 min · **Runs on:** your participant desktop

Do this before anything else. It is the same work as
[Exercise 1.1](exercises/01-llm-foundations/01-environment-setup.md) — that file
is the participant-facing version with reflection; this one is the checklist.

## Your seat

| | |
|---|---|
| Desktop | _assigned on the day_ |
| Seat number | _assigned on the day — your loopbacks are `Loopback<seat>x`, `10.<seat>.x.x`_ |
| MCP server URL | _to be written_ |
| MCP auth token | _to be written_ |

## Checklist

- [ ] Desktop reachable, you are logged in
- [ ] `python3.12` and `uv` present
- [ ] Server venv builds
- [ ] `OPENROUTER_API_KEY` exported
- [ ] Devices reachable over SSH
- [ ] MCP server starts; health endpoint answers
- [ ] `./smoke_test.sh` passes
- [ ] `pytest -q` green
- [ ] fast-agent connects and calls a tool
- [ ] Splunk bearer token issued and the endpoint answers
- [ ] Orchestrator venv built (needed from Category 7)

## Running the ladder

```bash
cd ~/mcp-8-hours
./scripts/sanity_check.sh            # full
./scripts/sanity_check.sh --quick    # skip device/network checks
```

_Reading the output, and what each rung means — to be written. Source:
`docs/where-things-run.md`._
