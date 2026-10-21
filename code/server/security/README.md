# security/ — DefenseClaw lab target (Module 6, exercise 6.4)

`vulnerable_server.py` is an **intentionally vulnerable** MCP server used only as
a scan target for the DefenseClaw exercise. It is never started by `run.sh` and
must never be used as a pattern for a real server.

It plants five issues, one per analyzer finding:

| # | Issue | Caught by |
|---|---|---|
| 1 | Tool poisoning — hidden instruction in a docstring | `llm` |
| 2 | Over-broad capability — arbitrary shell command tool | `llm` / `behavioral` |
| 3 | Hardcoded secret in a tool description | `yara` |
| 4 | Missing timeout / error handling | `readiness` |
| 5 | Prompt injection in a prompt template | `llm` (`--scan-prompts`) |

## Run (DefenseClaw host — `linuxdesktop65`)

```bash
# needs the standalone fastmcp package (not the SDK's mcp.server.fastmcp)
pip install fastmcp
FASTMCP_STATELESS_HTTP=true python3 vulnerable_server.py   # serves :8766/mcp
```

## Scan

See `expansion/mcp-server-security.md` for the full DefenseClaw install and the
four scan sections. Quick version once DefenseClaw is installed:

```bash
~/.defenseclaw/.venv/bin/mcp-scanner --analyzers yara,readiness,llm \
  --format detailed remote --server-url http://localhost:8766/mcp | tee stage2-llm-report.txt
```

Authoritative, verified end-to-end instructions live in
`expansion/mcp-server-security.md` (DefenseClaw 0.8.10, incl. the Python 3.10→3.12 fix).
