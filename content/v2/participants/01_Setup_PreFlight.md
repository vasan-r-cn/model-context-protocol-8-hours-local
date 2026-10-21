# Initial Setup & Pre-Flight Checklist

**Module M0 — first 10 minutes.** Goal: every seat green before the lecture starts. Work top to bottom; each step ends with a check. If any check fails, raise your hand — do not debug past step 3 on your own during the session.

## What you were given

| Item | Value |
|---|---|
| Lab desktops | MCP-Client (`linuxdesktop3`), MCP-Server (`linuxdesktop4`) — SSH or console access per your lab sheet |
| LibreChat login | `student@email.local` / `password` |
| MCP bearer token | `cisco-mcp-workshop` |
| Router1 | `172.18.2.6` (admin / admin, enable: admin) |

Full topology: Student Guide, section 2.

---

## Step 1 — LibreChat is up (MCP-Client desktop)

Open Chrome on the client desktop → `http://127.0.0.1:3080` → log in.

> [SCREENSHOT 1: LibreChat login page at 127.0.0.1:3080]

**Check:** you see the chat screen with the model pill showing `anthropic/claude-haiku-4.5`. Send `hi` — you get a reply.

If the page doesn't load, on `linuxdesktop3`:

```bash
cd ~/LibreChat
sudo docker compose ps          # five containers Up: LibreChat, chat-mongodb, chat-meilisearch, rag_api, vectordb
sudo docker compose up -d       # if any are missing
```

## Step 2 — Start the MCP server (MCP-Server desktop)

SSH to `linuxdesktop4`:

```bash
cd ~/cisco_mcp
./run.sh
```

First run creates a Python virtualenv and installs dependencies (about a minute); afterwards it starts instantly. Expected output ends with:

```
Starting Cisco MCP Server on http://0.0.0.0:8000 (MCP endpoint: /mcp)...
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**LEAVE THIS TERMINAL OPEN AND VISIBLE.** The server log is a teaching instrument — you will read it all day (tool calls, auth failures with reasons, SSH activity).

**Check:** from a second terminal on the same machine:

```bash
curl http://127.0.0.1:8000/
```

returns JSON containing `"status": "Cisco Router MCP Server Running"`.

## Step 3 — Smoke test (same machine)

```bash
cd ~/cisco_mcp
./smoke_test.sh
```

**Check:** last line reads `13 passed, 0 failed`. This proves: health endpoint, auth rejection, the MCP `initialize` handshake, and all 7 tools listed — without any client involved.

## Step 4 — MCP Inspector connects

In a new terminal on `linuxdesktop4` (Node 22 is preinstalled on the lab image):

```bash
npx @modelcontextprotocol/inspector@2.0.0
```

Open the URL it prints (it includes a session token — use the full printed URL, not just the port).

> [SCREENSHOT 2: Inspector terminal output showing the tokenized http://localhost:6274 URL]

In the Inspector connect pane (left side):

| Field | Value |
|---|---|
| Transport Type | `Streamable HTTP` |
| URL | `http://127.0.0.1:8000/mcp` |
| Authentication → Bearer Token | `cisco-mcp-workshop` — the token only, no "Bearer " prefix |

Click **Connect**.

> [SCREENSHOT 3: Inspector connect pane filled in with URL, transport and bearer token field]

**Check:** status shows Connected; the Tools tab lists 7 tools.

Common mistake: typing `Bearer cisco-mcp-workshop` into the token field. The server terminal will tell you exactly that: `401 on /mcp: token was entered WITH the 'Bearer ' prefix`.

## Step 5 — You are green when…

- [ ] LibreChat chat answers `hi` (Step 1)
- [ ] Server terminal open and running (Step 2)
- [ ] `./smoke_test.sh` → 13 passed (Step 3)
- [ ] Inspector connected, 7 tools visible (Step 4)

All four boxes ticked → you're ready for Lab 1. Sit back; help your neighbor.
