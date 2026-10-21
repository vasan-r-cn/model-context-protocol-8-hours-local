# Lab 3 — Build Your Own Tool

**45 minutes · clients: Inspector first, then LibreChat · file: `~/cisco_mcp/app/main.py` on linuxdesktop4**

You will extend the MCP server with tools you write yourself. The point is not typing Python — it is experiencing the full loop: *docstring → schema → model decides → validation → SSH → result → model reads it*.

Before starting, read Server Code Walkthrough §4–5 (ten minutes, seriously — everything below assumes it).

Plan: one warm-up, two builds, then advanced exercises. Build 1 is deliberately simple — a complete tool in ~20 lines. Build 2 adds the security lesson.

---

## Warm-up: extend the allowlist (5 min)

`dynamic_show` accepts only exact commands from `ALLOWED_SHOW_COMMANDS`. Add one:

```python
ALLOWED_SHOW_COMMANDS = {
    ...
    "show users",
}
```

Restart the server (`Ctrl+C`, `./run.sh`). Verify in Inspector: `dynamic_show` with `show users` now runs; `show run` is still rejected.

**Checkpoint 1:** new command accepted, off-list command still rejected. You changed server behavior without touching any schema — the allowlist is data, not protocol.

## Build 1: `check_internet` — does the router have internet? (15 min)

A question every network engineer asks daily: *can this device reach the internet?* Expose it as a one-click MCP tool. No parameters, no validation — the smallest complete tool you can write.

### Step 1 — the code

Add to `main.py`, next to the other read-only tools (after `dynamic_show` is a good spot):

```python
@mcp.tool(annotations=types.ToolAnnotations(readOnlyHint=True))
async def check_internet(ctx: Context) -> str:
    """Check whether Router1 has internet connectivity by pinging google.com.

    Reports OK or FAILED with the raw ping output. A failure can mean no
    internet route OR no DNS on the router — try 8.8.8.8 to tell them apart.
    """
    await ctx.report_progress(0, 1, "Pinging google.com from Router1...")
    try:
        output = await run_show("ping google.com repeat 3 timeout 2")
    except Exception as exc:
        return f"Error talking to Router1: {exc}"
    await ctx.report_progress(1, 1, "Done")
    if "!" in output:
        verdict = "Internet connectivity: OK"
    elif "Unrecognized host" in output:
        verdict = "Internet connectivity: FAILED (DNS — router cannot resolve google.com)"
    else:
        verdict = "Internet connectivity: FAILED (no echo replies)"
    return f"{verdict}\n\nRouter1# ping google.com repeat 3 timeout 2\n\n{output}"
```

Read your own code before running it — every line is doing a named job:

- **The decorator + docstring** generate the tool's schema and the description the LLM reads. Note the docstring tells the model what a failure *means* — that sentence will visibly improve the model's answers.
- **`repeat 3 timeout 2`** keeps the worst case around 6 seconds — a plain `ping google.com` on IOS can run past Netmiko's read timeout when every echo times out.
- **`"!" in output`** — IOS prints one `!` per successful echo, `.` per timeout. The tool *interprets* the output and returns a verdict line first, raw evidence after.
- **Both outcomes are success.** "No internet" is a correct, useful answer — the tool only *fails* if it can't ask the router at all.

### Step 2 — verify in Inspector (always Inspector before chat)

Restart the server. In Inspector:

1. Tools tab → `check_internet` present, `readOnlyHint: true`, empty input schema (`{}` — no arguments).
2. Call it. Watch the progress notification, then read the verdict line.

**Checkpoint 2:** tool listed and returns a verdict (either OK or FAILED — both count; note which one *your* lab gives, and why).

### Step 3 — now with the model

In LibreChat: refresh the server's tools (MCP menu → reinitialize, or ask the instructor), new chat, then:

- *"Does the router have internet access?"* — watch the model pick your tool, and notice how its answer uses your verdict line.
- *"Why might the ping have failed?"* — the docstring's DNS-vs-route hint tends to show up here. You wrote that hint.

**Checkpoint 3:** the model called `check_internet` (visible in the server terminal) and gave a correct plain-language answer.

## Build 2: `ping_from_router` — now with untrusted input (15 min)

`check_internet` had no parameters. The moment a tool takes an argument, the model *invents its value* — and LLM-supplied arguments are **untrusted input, always**. Build the general version of your ping tool and defend it.

### Step 1 — think first

The model will supply `target`. Write down two ways a raw f-string `f"ping {target}"` could go wrong before reading on.

> Examples: `"172.18.2.10 repeat 100000"` (resource burn), or any trailing IOS options you never intended. Same lesson as the `dynamic_show` allowlist: prefix/presence checks are not guardrails.

### Step 2 — the code

```python
import re   # with the other imports at the top of main.py

IPV4_RE = re.compile(
    r"^(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
    r"(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}$"
)


@mcp.tool(annotations=types.ToolAnnotations(readOnlyHint=True))
async def ping_from_router(target: str, ctx: Context) -> str:
    """Ping an IPv4 address FROM Router1 to test reachability across the lab.

    target must be a plain IPv4 address (e.g. 172.18.2.10).
    """
    candidate = target.strip()
    if not IPV4_RE.match(candidate):
        return (
            f"Rejected: {target!r} is not a plain IPv4 address. "
            "Provide dotted-quad only, e.g. 172.18.2.10."
        )
    await ctx.report_progress(0, 1, f"Pinging {candidate} from Router1...")
    try:
        output = await run_show(f"ping {candidate} repeat 3 timeout 2")
    except Exception as exc:
        return f"Error talking to Router1: {exc}"
    await ctx.report_progress(1, 1, "Done")
    return f"Router1# ping {candidate}\n\n{output}"
```

The rejection text is written *for the model*: it explains what valid input looks like, so the model can retry correctly — the same errors-as-text pattern from Lab 1 (C3).

### Step 3 — verify, then attack, then chat

In Inspector:
1. `ping_from_router` with `172.18.2.10` → ping output (`!!!` = success).
2. `ping_from_router` with `172.18.2.10 repeat 1000` → your rejection text. The regex just ate your injection.

In LibreChat:
- *"From the router, can we reach Router2 at 172.18.2.10?"*
- *"Ping every device in the lab from the router"* — observe sequential tool calls.
- Watch a failed target: `.` output is a *successful tool call* reporting unreachability — does the model interpret it right?

**Checkpoint 4:** accept + reject behaviors confirmed in Inspector; at least one chat prompt produced a correct reachability answer via your tool.

## Understanding: what actually happened (5 min)

Trace one exchange end to end and match it to Lab 1's message taxonomy: your prompt → OpenRouter (model chooses the tool, invents arguments) → LibreChat sends `tools/call` → bearer check → **your validation** → worker thread → SSH → text result → model reads and phrases the answer. The model never held credentials, never saw SSH, and could only do what your validation allowed. **The server is the security boundary; the model is a user.**

## Advanced (pick any; take-home friendly)

**A. Command history (10 min).** Log every executed command to a file: one `logging.getLogger("cisco-mcp.audit")` call inside `run_show`/`run_config`. Verify entries appear for all tools. Auditability is a one-liner when all I/O flows through two helpers — that's *why* it flows through two helpers.

**B. Multi-router (15 min).** Give `ping_from_router` a `router: str = "router1"` parameter backed by `ROUTERS = {"router1": {...172.18.2.6...}, "router2": {...172.18.2.10...}}`. A `Literal["router1", "router2"]` type hint becomes an enum in the generated schema. Ask LibreChat to *"check internet connectivity from both routers."*

**C. Break the naive version (5 min, discussion).** Replace the regex with `if not target: return ...` and think through what `"172.18.2.10 repeat 100000"` now does. Put the regex back.

## Troubleshooting this lab

| Symptom | Cause | Fix |
|---|---|---|
| Tool missing from Inspector after restart | syntax error — server didn't start | read the server terminal traceback |
| Tool in Inspector but not LibreChat | LibreChat discovered tools at startup | reinitialize the server from the MCP menu (or restart api) |
| `check_internet`: "Unrecognized host" | router has no DNS configured | expected in some lab builds — the verdict line says so; try `ping_from_router` with `8.8.8.8` to test the route alone |
| ping output empty / Netmiko read timeout | ping ran past the read window | keep `repeat 3 timeout 2` in the command |
| Model refuses to guess Router2's IP | it genuinely may not know | give the IP in your prompt — or add it to the tool docstring; notice which fix is better and why |
| Model calls the wrong tool | descriptions too similar | sharpen the docstrings — say *when* to use each tool |
