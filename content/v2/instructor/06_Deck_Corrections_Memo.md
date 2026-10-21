# Deck Corrections Memo — "MCP Essentials for AI-Driven Network Operations"

**To:** deck owner · **Re:** `content/PDFModel_Context_Protocol_WaterMarked.pdf` (dated 22 Oct 2025)
**Status update:** a rebuilt deck implementing every item below already exists — `content/v2/MCP_Essentials_Deck_v2.pptx` (regenerate via `scripts/build_deck.py`). This memo remains the record of what changed and why, and applies if the original deck is updated independently. The rebuilt deck is text-first; original diagrams/visuals were image-only in the PDF and could not be carried over — re-add any wanted visuals to the pptx by hand.
**Context:** the deck remains the lecture backbone for the updated 4-hour workshop (module M1, trimmed to ~40 min). The lab stack has been rebuilt (FastMCP server, Streamable HTTP, bearer auth, all six primitives live) — several slides now contradict either the MCP spec or what students see minutes later in the lab. Items below are ordered by severity; 1–3 are factual errors that must not be taught.

---

## A. Must-fix (factual errors)

**1. Termination slide shows Language Server Protocol, not MCP.**
`{"method": "shutdown"}` → `{"method": "exit"}` does not exist in MCP. Termination is transport-level: close the connection, or HTTP `DELETE` of the Streamable HTTP session. Replace the JSON with a one-liner on session close.

**2. Elicitation slide — wrong method, wrong shape, forbidden example.**
- Method is `elicitation/create`, not `elicitation/request`; the payload carries a flat `requestedSchema` (JSON Schema with primitive properties), not `inputType`.
- Result shape: `{action: "accept" | "decline" | "cancel", content: {...}}`.
- The example elicits an **API key** — the spec explicitly forbids using elicitation for secrets/credentials. Replace with the lab's real example: confirm-before-router-config-change (students see this exact dialog in Lab 5).

**3. `notifications/initialized` direction reversed.**
Slide says the *server* sends it ("server ready"). It is sent by the **client** after receiving the `initialize` response. Students verify this on the wire in Lab 1 — the slide must match.

**4. Transport slide inconsistency.**
One slide lists "HTTP+SSE" as a current transport; another correctly says Streamable HTTP. HTTP+SSE was deprecated in the 2025-03-26 revision — label it *legacy*. The lab runs Streamable HTTP.

**5. Fabricated Python SDK code.**
`from mcp import Client; client = Client("server-name"); await client.connect()` is not the SDK API. Real client: `ClientSession` + a transport context manager (`streamablehttp_client`). Better: swap this slide for the *server-side* FastMCP decorator snippet — it's what students write in Lab 3:

```python
@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_interfaces(ctx: Context) -> str:
    """Get all router interfaces and their status."""
```

## B. Should-fix (stale/overstated)

**6. Protocol version** `2025-06-18` → `2025-11-25`. Mention what the revision added where relevant (structured tool output / `outputSchema`, tool annotations, tasks). Annotations and structured output are live in the lab server.

**7. Sampling slide:** `hints: ["claude-3-5-sonnet"]` is an outdated model name; `modelPreferences` also has `costPriority` / `speedPriority` / `intelligencePriority`. Also: human-in-the-loop for sampling is **SHOULD** (design principle), not MUST.

**8. Uncited numbers.** "60–70% of development time on integration", "150+ lines per tool", "90% less maintenance", "67% reduction (50 → 15)" — cite a source on-slide or cut. Same for the "— Anthropic, 2024" quote (link the actual post).

**9. Ecosystem slide is 2024-vintage** (Zed/Replit/Sourcegraph; Drive/Slack/GitHub connectors). Refresh with the current landscape and mention the MCP Registry. Suggested current framing: IDE-class clients (Claude Code, VS Code/Copilot, Cursor) consume the deep primitives; chat products consume tools — which is precisely the workshop's two-client story.

**10. Section 5 over-promises.** Agenda says "Implementation guide, resources" but no such slides exist — the deck jumps to Future/Thank You. Either add 1–2 slides handing off to the labs ("now you build exactly this") or fix the agenda.

## C. New content request (the audience-fit gap)

**11. Zero network-operations content despite the title.** Add 2–3 slides bridging concepts → this lab:
- The Cisco tool example (slide-sized `get_interfaces` / `configure_interface` pair) with read-only vs destructive annotations on network gear.
- Where guardrails live when an AI agent touches network config: transport auth → command allowlist → confirmation gate (elicitation) → pre-change snapshot → reset. (Matches the shipped server one-for-one; instructors can point at the running code.)
- Client capability reality: the matrix of what LibreChat / Inspector / IDE clients actually consume — sets up Labs 4–5.

## D. Mechanical

**12.** Ligature corruption from the source font ("Solu-on", "condiAons", "noQﬁcaQons"), typos ("Expertize", "AreLarge", "TheFuture"), duplicated MxN slide with reversed labels and out-of-order footer numbers, image-only slides lacking a text layer (search/accessibility), copyright footer year, and the two conflicting confidentiality footers — one editorial pass.

---

**Timing note for the trimmed lecture (40 min):** Section 1 (LLM fundamentals) compresses to ~8 min for this audience; Sections 2–4 carry the weight; Section 5 hands off to the labs. Slides supporting Labs 4–5 (resources/prompts/notifications/elicitation) matter more than launch-era ecosystem history.
