"""Builds the corrected workshop lecture deck (M1, ~40 min).

Regenerates content/v2/MCP_Essentials_Deck_v2.pptx from the slide data below.
This is the v2 replacement for content/PDFModel_Context_Protocol_WaterMarked.pdf,
with every correction from content/v2/instructor/06_Deck_Corrections_Memo applied.

Usage: python3 scripts/build_deck.py
"""

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

NAVY = RGBColor(0x0B, 0x2A, 0x4A)
CYAN = RGBColor(0x00, 0xB4, 0xD8)
DARK = RGBColor(0x20, 0x20, 0x20)
GREY = RGBColor(0x6A, 0x6A, 0x6A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT = RGBColor(0xF0, 0xF4, 0xF8)
MONO = "Consolas"

SLIDE_W, SLIDE_H = Inches(13.333), Inches(7.5)


def _fill(shape, color):
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()


def _text(frame, runs_lines, size=18, color=DARK, bold=False, mono=False, space_after=6):
    frame.word_wrap = True
    first = True
    for line in runs_lines:
        p = frame.paragraphs[0] if first else frame.add_paragraph()
        first = False
        level = 0
        text = line
        while text.startswith("  "):
            level += 1
            text = text[2:]
        p.level = min(level, 4)
        p.space_after = Pt(space_after)
        run = p.add_run()
        run.text = text
        f = run.font
        f.size = Pt(size - 2 * level)
        f.bold = bold or text.startswith("★")
        f.color.rgb = color
        if mono or text.lstrip().startswith(("{", "}", "@", "def ", "async ", '"', "curl", "npx", "claude ")):
            f.name = MONO
            f.size = Pt(size - 3)


class Deck:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width = SLIDE_W
        self.prs.slide_height = SLIDE_H
        self.blank = self.prs.slide_layouts[6]
        self.n = 0

    def _base(self, title, section=""):
        self.n += 1
        slide = self.prs.slides.add_slide(self.blank)
        bar = slide.shapes.add_shape(1, 0, 0, SLIDE_W, Inches(1.0))
        _fill(bar, NAVY)
        tf = bar.text_frame
        tf.margin_left = Inches(0.4)
        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = title
        r.font.size = Pt(28)
        r.font.bold = True
        r.font.color.rgb = WHITE
        accent = slide.shapes.add_shape(1, 0, Inches(1.0), SLIDE_W, Emu(45720))
        _fill(accent, CYAN)
        foot = slide.shapes.add_textbox(Inches(0.4), Inches(7.05), Inches(12.5), Inches(0.4))
        fp = foot.text_frame.paragraphs[0]
        fr = fp.add_run()
        fr.text = f"Criterion Networks · MCP Workshop · {section}".rstrip(" ·")
        fr.font.size = Pt(10)
        fr.font.color.rgb = GREY
        num = slide.shapes.add_textbox(Inches(12.6), Inches(7.05), Inches(0.6), Inches(0.4))
        np_ = num.text_frame.paragraphs[0]
        nr = np_.add_run()
        nr.text = str(self.n)
        nr.font.size = Pt(10)
        nr.font.color.rgb = GREY
        return slide

    def title_slide(self, title, subtitle, lines):
        self.n += 1
        slide = self.prs.slides.add_slide(self.blank)
        bg = slide.shapes.add_shape(1, 0, 0, SLIDE_W, SLIDE_H)
        _fill(bg, NAVY)
        box = slide.shapes.add_textbox(Inches(0.8), Inches(2.2), Inches(11.7), Inches(3.5))
        tf = box.text_frame
        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = title
        r.font.size = Pt(40)
        r.font.bold = True
        r.font.color.rgb = WHITE
        p2 = tf.add_paragraph()
        r2 = p2.add_run()
        r2.text = subtitle
        r2.font.size = Pt(22)
        r2.font.color.rgb = CYAN
        for line in lines:
            p3 = tf.add_paragraph()
            r3 = p3.add_run()
            r3.text = line
            r3.font.size = Pt(14)
            r3.font.color.rgb = LIGHT

    def section_slide(self, kicker, title):
        self.n += 1
        slide = self.prs.slides.add_slide(self.blank)
        bg = slide.shapes.add_shape(1, 0, 0, SLIDE_W, SLIDE_H)
        _fill(bg, NAVY)
        box = slide.shapes.add_textbox(Inches(0.8), Inches(2.8), Inches(11.7), Inches(2.0))
        tf = box.text_frame
        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = kicker
        r.font.size = Pt(16)
        r.font.color.rgb = CYAN
        p2 = tf.add_paragraph()
        r2 = p2.add_run()
        r2.text = title
        r2.font.size = Pt(36)
        r2.font.bold = True
        r2.font.color.rgb = WHITE

    def bullets(self, title, lines, section="", size=18):
        slide = self._base(title, section)
        box = slide.shapes.add_textbox(Inches(0.5), Inches(1.3), Inches(12.3), Inches(5.6))
        _text(box.text_frame, lines, size=size)
        return slide

    def code(self, title, intro, code_lines, outro=(), section=""):
        slide = self._base(title, section)
        y = Inches(1.25)
        if intro:
            box = slide.shapes.add_textbox(Inches(0.5), y, Inches(12.3), Inches(0.9))
            _text(box.text_frame, intro, size=16)
            y = Inches(2.15)
        h = Inches(0.32 * len(code_lines) + 0.3)
        block = slide.shapes.add_shape(1, Inches(0.5), y, Inches(12.3), h)
        _fill(block, RGBColor(0x1E, 0x1E, 0x1E))
        tf = block.text_frame
        tf.margin_left = Inches(0.25)
        tf.margin_top = Inches(0.12)
        first = True
        for line in code_lines:
            p = tf.paragraphs[0] if first else tf.add_paragraph()
            first = False
            p.alignment = PP_ALIGN.LEFT
            r = p.add_run()
            r.text = line if line else " "
            r.font.name = MONO
            r.font.size = Pt(14)
            r.font.color.rgb = RGBColor(0xD8, 0xF0, 0xD8)
        if outro:
            box2 = slide.shapes.add_textbox(Inches(0.5), Emu(int(y) + int(h) + 91440), Inches(12.3), Inches(1.4))
            _text(box2.text_frame, outro, size=15)

    def table(self, title, headers, rows, section="", col_widths=None, size=13):
        slide = self._base(title, section)
        n_rows, n_cols = len(rows) + 1, len(headers)
        shape = slide.shapes.add_table(
            n_rows, n_cols, Inches(0.5), Inches(1.4), Inches(12.3), Inches(0.4 * n_rows)
        )
        table = shape.table
        if col_widths:
            for i, w in enumerate(col_widths):
                table.columns[i].width = Inches(w)
        for c, head in enumerate(headers):
            cell = table.cell(0, c)
            cell.text = head
            for p in cell.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(size)
                    r.font.bold = True
                    r.font.color.rgb = WHITE
            _fill_cell(cell, NAVY)
        for i, row in enumerate(rows, start=1):
            for c, val in enumerate(row):
                cell = table.cell(i, c)
                cell.text = val
                for p in cell.text_frame.paragraphs:
                    for r in p.runs:
                        r.font.size = Pt(size)
                        r.font.color.rgb = DARK
        return slide


def _fill_cell(cell, color):
    cell.fill.solid()
    cell.fill.fore_color.rgb = color


d = Deck()

# ---- Title & agenda -------------------------------------------------------
d.title_slide(
    "Model Context Protocol (MCP) Essentials",
    "for AI-Driven Network Operations — Workshop Edition v2",
    ["Aligned to MCP specification revision 2025-11-25",
     "Lecture module M1 (40 min) · pairs with hands-on Labs 1–5",
     "Criterion Networks"],
)

d.bullets("Agenda (40 minutes)", [
    "1. LLMs, agents, and why integration is the bottleneck  (8 min)",
    "2. The MxN problem and MCP's answer  (7 min)",
    "3. Protocol architecture: messages, transports, lifecycle  (10 min)",
    "4. The six primitives — with the code you will run today  (12 min)",
    "5. Client reality, security, and your lab map  (3 min)",
    "",
    "Everything in sections 3–4 is observable on the wire in Lab 1 — this lecture has a lab behind every claim.",
], section="Agenda")

# ---- Section 1 ------------------------------------------------------------
d.section_slide("Section 1 of 5", "LLMs, agents, and the integration bottleneck")

d.bullets("LLMs in two minutes", [
    "A large language model predicts text from context — everything it 'does' is emitting tokens.",
    "★ Tool use changed the game: models can emit a STRUCTURED REQUEST to run a function, then read the result.",
    "The model never executes anything. It asks; your systems act; it interprets.",
    "  That separation — model asks, server decides — is the entire security story of today's lab.",
    "Context window = working memory: what you place there (tool results, configs, docs) is what it reasons over.",
], section="1 · LLMs & Agents")

d.bullets("AI agent vs. agentic workflow", [
    "AI agent: a model in a loop — decide → act (tool call) → observe result → decide again.",
    "Agentic workflow: multiple steps/roles orchestrated around models, with checkpoints and human gates.",
    "Both are only as capable as the ACTIONS they can take and the CONTEXT they can reach.",
    "★ Capability and context arrive through integrations — which is exactly where teams stall.",
], section="1 · LLMs & Agents")

d.bullets("Why network operations should care", [
    "Everything in ops has an API or a CLI — routers, controllers, monitoring, ticketing.",
    "An assistant that can query interface state, check routing, and draft config touches real revenue-hours.",
    "★ But network gear is where 'the model did something unexpected' is unacceptable.",
    "Today you build the guardrail stack, not just the demo:",
    "  read-only vs destructive tool annotations · command allowlists · confirmation gates · pre-change snapshots",
], section="1 · LLMs & Agents")

# ---- Section 2 ------------------------------------------------------------
d.section_slide("Section 2 of 5", "The MxN problem — and MCP's answer")

d.bullets("How AI applications integrated before MCP", [
    "Every AI application hand-wires every system it talks to: bespoke schemas, auth, retries, prompts.",
    "M applications × N systems = M×N custom integrations — each one built, tested, and maintained separately.",
    "Change a backend API → revisit every AI app that touches it.",
    "Integration effort dominates AI feature development. (Ask your own platform team.)",
], section="2 · MxN → M+N")

d.bullets("MCP: one protocol between AI apps and systems", [
    "Model Context Protocol — open standard, open spec: modelcontextprotocol.io",
    "Each system exposes ONE MCP server; each AI application implements ONE MCP client.",
    "★ M×N bespoke integrations become M+N standard endpoints.",
    "The 'USB-C for AI' analogy: one connector shape, any device combination.",
    "What MCP is NOT: not an agent framework, not a model, not an orchestrator — just the connection standard.",
], section="2 · MxN → M+N")

d.bullets("What that means for this lab", [
    "You will write ONE Python file exposing Cisco router operations as an MCP server.",
    "It will be consumed — unchanged — by three different clients this week:",
    "  LibreChat (a chat product) · MCP Inspector (a protocol tool) · Claude Code (a coding agent)",
    "★ Same server, three clients, zero client-specific code. That is M+N working.",
], section="2 · MxN → M+N")

# ---- Section 3 ------------------------------------------------------------
d.section_slide("Section 3 of 5", "Protocol architecture")

d.bullets("Host, client, server", [
    "HOST — the AI application the user sees (LibreChat, an IDE, your custom agent).",
    "CLIENT — the protocol connector inside the host; one client per server connection.",
    "SERVER — the program exposing capabilities (your Python file).",
    "Two layers:",
    "  Data layer: JSON-RPC 2.0 messages — what is said",
    "  Transport layer: how bytes move — stdio (local) or Streamable HTTP (remote)",
], section="3 · Architecture")

d.code("JSON-RPC 2.0 — the whole message taxonomy", [
    "Three message kinds. You will label all three yourself in Lab 1:",
], [
    '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{...}}   ← request (has id)',
    '{"jsonrpc":"2.0","id":1,"result":{...}}                          ← response (matches id)',
    '{"jsonrpc":"2.0","method":"notifications/progress","params":{...}} ← notification (NO id, no reply)',
], [
    "Requests expect exactly one response. Notifications are fire-and-forget, both directions.",
], section="3 · Architecture")

d.table("Transports", ["Transport", "Status", "Use", "In this lab"], [
    ["stdio", "current", "local process, client launches server", "bridge trick (mcp-remote) in the take-home"],
    ["Streamable HTTP", "current", "remote server, one endpoint, sessions + streaming", "★ /mcp on the workshop server"],
    ["HTTP+SSE (two endpoints)", "DEPRECATED (2025-03-26)", "legacy only", "what v1 of this workshop used — retired"],
], section="3 · Architecture", col_widths=[3.0, 2.6, 4.2, 2.5])

d.bullets("Protocol lifecycle", [
    "1. initialize — client sends protocolVersion + its capabilities; server replies with ITS capabilities + instructions.",
    "2. notifications/initialized — sent by the CLIENT to confirm readiness. (One-way; no id.)",
    "★ Capability negotiation happens here: each side may only use what the other declared.",
    "3. Operation — discovery (tools/list, resources/list, prompts/list) and execution (tools/call, resources/read, ...).",
    "4. Termination — transport-level: close the connection, or HTTP DELETE of the Streamable HTTP session.",
    "  (There are no 'shutdown'/'exit' methods in MCP — that's a different protocol.)",
], section="3 · Architecture")

# ---- Section 4 ------------------------------------------------------------
d.section_slide("Section 4 of 5", "The six primitives — with today's code")

d.table("Six primitives, three control points", ["Primitive", "Controlled by", "Today's example", "Lab"], [
    ["Tools", "the model", "get_interfaces, configure_interface", "1–3"],
    ["Resources", "the application / user", "router://running-config", "4"],
    ["Prompts", "the user", "/troubleshoot_interface", "4"],
    ["Notifications", "the server", "tools/list_changed, resources/updated", "5"],
    ["Elicitation", "server asks, user answers", "confirm-before-config-change", "5"],
    ["Sampling", "server asks, model answers", "(lecture only — see client matrix)", "—"],
], section="4 · Primitives", col_widths=[2.4, 3.0, 4.9, 2.0])

d.code("Tools — model-controlled actions", [
    "A FastMCP tool from the server you run today. The docstring IS the prompt engineering:",
], [
    "@mcp.tool(annotations=types.ToolAnnotations(readOnlyHint=True))",
    "async def get_interfaces(ctx: Context) -> str:",
    '    """Get all router interfaces and their status (show ip interface brief)."""',
    "    await ctx.report_progress(0, 1, \"Connecting to Router1 over SSH...\")",
    "    ...",
], [
    "Function name → tool name · docstring → description the LLM reads · type hints → JSON Schema (generated).",
    "Annotations declare intent: readOnlyHint / destructiveHint — on network gear, this distinction is everything.",
    "Errors return as text results, never exceptions — so the model can read them and retry (Lab 1, C3).",
], section="4 · Primitives")

d.bullets("Tools — the 2025 spec additions you'll use", [
    "Structured output: a tool can declare an outputSchema and return validated JSON, not just prose.",
    "  (get_router_info returns {hostname, version, uptime} — see it in Inspector.)",
    "Tool annotations are machine-readable safety hints — clients can gate destructive tools differently.",
    "Progress notifications stream during long calls; clients use them to extend timeouts (slow SSH ≠ dead call).",
], section="4 · Primitives")

d.bullets("Resources — context on demand", [
    "URI-addressed data the CLIENT chooses to read: router://interfaces, router://running-config.",
    "Templates parameterize: router://interfaces/{name}.",
    "★ Tools = the model decides to act. Resources = the application/user decides to load context.",
    "Today's sharp edge: 'show running-config' is REJECTED as a tool command but SERVED as a resource —",
    "  the model can't pull full config on its own initiative; a human deliberately loading it is a different trust decision.",
], section="4 · Primitives")

d.bullets("Prompts — reusable expertise", [
    "Named, parameterized templates the USER invokes from the client UI.",
    "Today: troubleshoot_interface(interface), audit_router_config() — your team runbooks, encoded once, versioned with the server.",
    "In Claude Code they appear as slash commands: /mcp__cisco-router__troubleshoot_interface",
    "Naming trap: LibreChat's built-in 'Prompts' feature is its own local library — NOT MCP prompts.",
], section="4 · Primitives")

d.bullets("Notifications & subscriptions — the push half", [
    "notifications/tools/list_changed — the server's toolset changed at runtime.",
    "  Today: enable_config_tools toggles the destructive tools; watch the list shrink live in Inspector.",
    "resources/subscribe + notifications/resources/updated — 'tell me when this changes.'",
    "  Today: subscribe to router://running-config, run create_loopback, watch the update arrive.",
    "notifications/progress — long-running call heartbeat.",
    "Everything else you've seen is request/response; this is how servers speak first.",
], section="4 · Primitives")

d.code("Elicitation — the server asks the user", [
    "Method: elicitation/create. Server sends a message + a flat JSON Schema (requestedSchema);",
    "the client renders a dialog; result is {action: accept | decline | cancel, content: {...}}.",
], [
    "result = await ctx.elicit(",
    "    message=f\"About to configure {interface} with {ip}/24 on Router1. Proceed?\",",
    "    schema=ConfirmChange,",
    ")",
    "if result.action != \"accept\":",
    "    return \"Change cancelled by user.\"",
], [
    "★ Servers MUST NOT elicit secrets or credentials — confirmations and parameters only.",
    "Lab 5: Inspector pops this exact dialog. LibreChat declares no elicitation capability →",
    "the server degrades gracefully (applies with a warning). Capability negotiation, visible.",
], section="4 · Primitives")

d.bullets("Sampling — the server asks the model", [
    "sampling/createMessage: a server requests an LLM completion THROUGH the client — server needs no API key.",
    "modelPreferences: hints plus costPriority / speedPriority / intelligencePriority (client maps to an actual model).",
    "Human-in-the-loop review is a SHOULD (strong design principle) — clients typically show the user what's asked.",
    "Rare in the wild today (see client matrix) — lecture-only in this lab.",
], section="4 · Primitives")

d.bullets("Security — where each guardrail lives", [
    "Transport auth: MCP uses plain HTTP auth for remote servers — today a bearer token; OAuth 2.1 for products.",
    "Input validation: LLM-supplied arguments are untrusted input. Always.",
    "  Today: exact-command allowlist (not prefix match — 'show run | redirect tftp://…' is why), IPv4 regex in Lab 3.",
    "Intent classification: readOnlyHint / destructiveHint annotations.",
    "Human gates: elicitation confirm-before-change.",
    "Recovery: pre-change snapshots (snapshot_config) + reset-to-baseline procedure.",
    "★ The server is the security boundary. The model is a user.",
], section="4 · Primitives")

# ---- Section 5 ------------------------------------------------------------
d.section_slide("Section 5 of 5", "Client reality & your lab map")

d.table("What clients actually consume (verified)", ["Capability", "LibreChat", "Inspector", "Claude Code", "VS Code"], [
    ["Tools + auth", "✓", "✓", "✓", "✓"],
    ["Server instructions", "✓", "✓", "✓", "✓"],
    ["Resources", "—", "✓", "✓ @-mention", "✓"],
    ["Prompts", "—", "✓", "✓ slash cmd", "✓"],
    ["list_changed / subscribe", "—", "✓", "—", "partial"],
    ["Elicitation", "—", "✓", "—", "✓"],
    ["Sampling", "—", "mock", "—", "✓"],
], section="5 · Reality & Labs", col_widths=[3.6, 2.2, 2.1, 2.5, 1.9], size=14)

d.bullets("Design consequence (memorize this one)", [
    "★ 'Supports MCP' is a spectrum, not a checkbox.",
    "Build tools-first — the universal baseline every client consumes.",
    "Layer resources, prompts, notifications, elicitation as progressive enhancement.",
    "Degrade gracefully when a capability is missing (you'll watch our server do exactly that in Lab 5).",
    "Check the client's declared capabilities — they're in the initialize exchange, and you know how to read it now.",
], section="5 · Reality & Labs")

d.bullets("The ecosystem, current view", [
    "Spec revision 2025-11-25 — brought structured output, tool annotations, tasks; HTTP+SSE long deprecated.",
    "First-party SDKs: Python, TypeScript, Java, Kotlin, C#, Go, Swift, Ruby, PHP, Rust.",
    "MCP Registry: public discovery of published servers.",
    "Deep-primitive clients today are IDE-class (Claude Code, VS Code, Cursor) and custom agents built on the SDKs;",
    "chat products mostly consume tools — precisely the two-client story of this workshop.",
], section="5 · Reality & Labs")

d.bullets("What you build today", [
    "Lab 1 (25m) — Protocol on the wire: label initialize / tools/list / tools/call in Inspector.",
    "Lab 2 (30m) — LibreChat end-to-end: bearer auth (you'll fix a broken token), chat drives the router.",
    "Lab 3 (45m) — Build your own tool: ping_from_router with input validation and annotations.",
    "Lab 4 (35m) — Resources & prompts in Inspector.",
    "Lab 5 (30m) — Notifications, subscriptions, and the elicitation gate.",
    "Take-home — consume prompts & resources from Claude Code, a production client.",
], section="5 · Reality & Labs")

d.bullets("Key takeaways", [
    "MCP turns M×N integrations into M+N standard endpoints — you'll prove it with one server, three clients.",
    "The protocol is small: three message kinds, one handshake, six primitives.",
    "Control points differ by primitive: model → tools, application → resources, user → prompts.",
    "Capability negotiation is the load-bearing feature — servers must degrade gracefully.",
    "On network infrastructure, the guardrail stack is not optional: validate, annotate, confirm, snapshot, reset.",
    "",
    "Spec & docs: modelcontextprotocol.io · SDKs: github.com/modelcontextprotocol",
], section="Wrap")

d.prs.save("content/v2/MCP_Essentials_Deck_v2.pptx")
print(f"Wrote content/v2/MCP_Essentials_Deck_v2.pptx ({d.n} slides)")
