# Participant Q&A Prep — Anticipated Questions & Answers

Instructor reference. Grouped by theme; each answer is deliverable verbally in under a minute, with a lab pointer where the answer can be *shown* instead of told. Showing beats telling every time — most answers here have a 30-second live demo.

---

## 1. Tool discovery & updates

**Q: I added 2 new tools to the server — how does the client discover them?**
Two mechanisms. (1) Discovery at connect: every client calls `tools/list` after `initialize` — restart/reconnect and the new tools are there. (2) Live update: the server sends `notifications/tools/list_changed`, and clients that handle it re-fetch the list without reconnecting. Inspector handles it (demo: `enable_config_tools` toggle, Lab 5); LibreChat does not — it discovers at startup only, so you reinitialize the server from the MCP menu or restart the api container. That difference is the client-capability lesson again.

**Q: Does the server need a restart when I edit a tool?**
Yes in our lab — Python is loaded at process start; `Ctrl+C` + `./run.sh`. (uvicorn `--reload` exists but is a dev convenience, not part of MCP.) The *protocol* doesn't require reconnecting clients after a tool change if the server emits `list_changed`.

**Q: What happens if the model calls a tool that was just removed?**
The server returns a JSON-RPC error ("unknown tool"). Clients surface it to the model as a failed call; a good model retries with `tools/list`-refreshed knowledge if the client refreshed. Stale tool lists are exactly why `list_changed` exists.

**Q: Are tool descriptions cached by the model?**
No — tools are sent with *every* model request (that's how function calling works). The client caches the list between MCP fetches; the model sees whatever the client sends per turn. Consequence: description edits take effect as soon as the client refreshes the list.

## 2. Multiple servers & composition

**Q: How do I connect multiple MCP servers to one client?**
Just add more entries — `mcpServers:` in librechat.yaml takes any number; Claude Code takes repeated `claude mcp add`. Each server gets its own client connection, session, and auth. The host merges all tools into one list for the model, typically namespaced (`c