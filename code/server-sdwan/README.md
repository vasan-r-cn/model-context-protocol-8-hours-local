# code/server-sdwan — an SD-WAN MCP server (Module 5, exercise 5.1)

A **read-only** MCP server over the Cisco vManage dataservice API: ~20 tools
(inventory, WAN edges, control connections, BFD/tunnels, health, alarms,
events, templates, policies, running-config, audit). FastMCP 2.x, Streamable
HTTP on `:7004`.

Vendored from `agentic-ai-workshop/mcp/sdwan/sdwan_mcp_server.py` with two
pod adaptations: host from `VMANAGE_HOST` (fallback `FQDN`), and `fix_url()`
respects an explicit `:port` (the pod exposes vManage on a NAT port, not :443).

```bash
cd code/server-sdwan
cp .env.example .env         # set VMANAGE_HOST=<pod FQDN>:<port>, creds
./run.sh                     # serves Streamable HTTP on :7004/mcp
```

Connect with fast-agent:

```bash
cd ../client-fastagent
fast-agent go -c lab-sdwan.yaml --servers sdwan --model openrouter.anthropic/claude-sonnet-4
# in session: /tools  ->  sdwan__get_inventory, sdwan__get_device_tunnels, ...
```

Every tool is a GET after a `j_security_check` login — read-only. TLS verify is
off (lab self-signed cert). Each tool accepts an optional `fqdn`; it defaults to
`VMANAGE_HOST`.
