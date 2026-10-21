#!/usr/bin/env python3
"""Build the consolidated 8-hour intermediate workshop syllabus (.docx).

Consolidates two sources:
  - docs/MCP_in_Practice-8HR_Intermediate-v2_2.docx (teammate syllabus; formatting template)
  - docs/workshop-flow-8h.md (run-of-show: timings, lab environment, client build, capstone)

Formatting is cloned paragraph-by-paragraph from the template so the output matches
the teammate document exactly (fonts, colours, spacing, bullets, header logo, footer).
The template's body is replaced; header/footer/styles/numbering are kept as-is.

Usage:  python3 scripts/build_8h_syllabus.py            (needs python-docx)
Output: docs/MCP_in_Practice-8HR_Intermediate-v3_consolidated.docx
"""

from __future__ import annotations

import copy
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "docs" / "MCP_in_Practice-8HR_Intermediate-v2_2.docx"
OUTPUT = ROOT / "docs" / "MCP_in_Practice-8HR_Intermediate-v3_consolidated.docx"

# Exemplar paragraph indices in the template body (see inspection notes in
# docs/workshop-flow-8h.md history): each role maps to a paragraph whose XML we clone.
EXEMPLARS = {
    "kicker": 0,        # "Instructor-Led Classroom Training" — centred, underlined, 11pt
    "gap": 1,           # empty centred paragraph
    "title": 2,         # bold 14pt centred
    "title2": 3,        # "(Full-Day — 8 Hours)"
    "subtitle": 4,      # bold 11pt navy centred
    "rule": 5,          # empty paragraph with bottom border (section end)
    "h1": 6,            # section heading — bold 16pt
    "body": 7,          # justified body text
    "lead": 11,         # short lead-in line ("Upon completing…")
    "bullet_lead": 12,  # bullet with bold lead run + normal run
    "h2": 22,           # module heading — bold 14pt navy
    "hands_on": 32,     # "Hands-on:" — bold italic navy, indented
    "bullet": 73,       # plain bullet
}


class Builder:
    def __init__(self, template: Path):
        self.doc = Document(str(template))
        body = self.doc.element.body
        paras = [c for c in body.iterchildren() if c.tag == qn("w:p")]
        self.ex = {k: copy.deepcopy(paras[i]) for k, i in EXEMPLARS.items()}
        # wipe body, keep sectPr
        for child in list(body.iterchildren()):
            if child.tag != qn("w:sectPr"):
                body.remove(child)
        self._body = body
        self.sect = body.find(qn("w:sectPr"))

    def _append(self, el):
        self.sect.addprevious(el)
        return Paragraph(el, self.doc)

    def _clone(self, role: str, *texts: str, justify: bool = True, keep_next: bool = False):
        """Clone exemplar; fill its runs with texts (extra runs removed, missing ignored)."""
        el = copy.deepcopy(self.ex[role])
        ppr = el.find(qn("w:pPr"))
        if not justify and ppr is not None:
            for jc in ppr.findall(qn("w:jc")):
                ppr.remove(jc)
        if keep_next and ppr is not None:
            ppr.insert(0, ppr.makeelement(qn("w:keepNext"), {}))
        runs = el.findall(qn("w:r"))
        for i, r in enumerate(runs):
            if i < len(texts):
                t = r.find(qn("w:t"))
                t.text = texts[i]
                t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            else:
                el.remove(r)
        return self._append(el)

    # roles -------------------------------------------------------------
    def kicker(self, t): self._clone("kicker", t)
    def gap(self): self._clone("gap")
    def title(self, t): self._clone("title", t)
    def title2(self, t): self._clone("title2", t)
    def subtitle(self, t): self._clone("subtitle", t)
    def rule(self): self._clone("rule")
    def h1(self, t): self._clone("h1", t, keep_next=True)
    def h2(self, t): self._clone("h2", t, keep_next=True)
    def body(self, t): self._clone("body", t)
    def lead(self, t): self._clone("lead", t)
    def hands_on(self, t="Hands-on:"): self._clone("hands_on", t, keep_next=True)
    def bullet(self, t): self._clone("bullet", t)
    def bullet_lead(self, lead, rest, justify=True): self._clone("bullet_lead", lead, rest, justify=justify)
    def bullets(self, items, justify=True):
        for it in items:
            if isinstance(it, tuple):
                self.bullet_lead(*it, justify=justify)
            else:
                self._clone("bullet", it, justify=justify)

    def module(self, heading, points, labs):
        self.h2(heading)
        self.bullets(points)
        if labs:
            self.hands_on()
            self.bullets(labs)

    def save(self, path: Path):
        self.doc.save(str(path))


def build() -> Path:
    b = Builder(TEMPLATE)

    # ---- masthead ----------------------------------------------------------
    b.kicker("Instructor-Led Classroom Training")
    b.gap()
    b.title("MCP in Practice: Agentic Network Operations Workshop")
    b.title2("(Full-Day — 8 Hours)")
    b.subtitle("Skill Level: Intermediate")
    b.rule()

    # ---- course description ------------------------------------------------
    b.h1("Course Description")
    b.body(
        "This full-day, lab-intensive workshop is about building MCP infrastructure rather than "
        "explaining it. Participants implement, secure, test, and promote a production-grade MCP "
        "server that exposes Cisco network operations capability to AI agents, and build the "
        "client-side contract that makes its safety controls enforceable."
    )
    b.body(
        "The morning establishes the protocol baseline quickly — lifecycle, Streamable HTTP "
        "sessions, capability negotiation, and the six primitives, observed on the wire rather than "
        "described — then moves directly into server engineering: transports and authentication, "
        "tool and schema design, error semantics, resource modelling, and audit. The afternoon "
        "covers write-path control, MCP-specific security risk, the client side of the contract "
        "(approval and sampling only exist when a client implements them), and the test and "
        "promotion discipline required before an agent is permitted to change network state. "
        "Agent orchestration frameworks are out of scope; the workshop assumes an agent exists and "
        "makes the tools and the host behind it correct, safe, and operable."
    )
    b.body(
        "All exercises run in Criterion's production-representative lab estate — two live Cisco IOS "
        "routers and an MCP server host — never against customer or "
        "production infrastructure. Within the lab, Router1 plays the live-operations role and "
        "Router2 the production-representative role: every write moves through pre-flight "
        "validation on Router2, policy checks, explicit human approval, verification, and rollback "
        "before it is promoted to Router1 — the same validation gate and formal promotion model "
        "Criterion applies to customer production estates. Participants finish with a working, "
        "audited MCP server, a minimal MCP client they wrote themselves, and a repeatable scenario "
        "suite they can carry into their own environment."
    )
    b.rule()

    # ---- objectives --------------------------------------------------------
    b.h1("Course Objectives")
    b.lead("Upon completing this course, the learner will be able to:")
    b.bullets([
        ("Explain and observe the protocol: ",
         "Trace the MCP lifecycle, Streamable HTTP session mechanics, capability negotiation, and "
         "the six primitives on the wire, and state which primitive each production client actually "
         "consumes."),
        ("Implement a production-grade MCP server: ",
         "Build an MCP server for network operations using the official Python SDK, with a "
         "maintainable structure, session handling, connection management against network devices, "
         "and a structured per-invocation audit record."),
        ("Select and secure transports: ",
         "Choose between stdio and Streamable HTTP for a given deployment; implement bearer-token "
         "authentication and role mapping, and understand the OAuth 2.1 path for remote access."),
        ("Engineer tools and schemas for reliable selection: ",
         "Design intent-shaped tools with constrained input schemas, structured output schemas, and "
         "tool annotations that make agent tool selection deterministic rather than probabilistic."),
        ("Define correct error and validation semantics: ",
         "Return actionable errors for rejected input, unreachable devices, partial results, "
         "timeouts, and authorization failures, so an agent can reason about failure instead of "
         "retrying blindly."),
        ("Model reference context as resources and prompts: ",
         "Expose topology, baselines, and configuration as MCP resources and resource templates; "
         "author server-side prompts; decide correctly between a resource and a tool; assemble "
         "cross-device evidence at the server."),
        ("Enforce write-path control at the server: ",
         "Implement read/write separation, role-based tool visibility and enforcement, pre-flight "
         "dry runs, policy validation, server-side human approval, verification, audit records, and "
         "rollback — enforced in code, not in the prompt."),
        ("Assess and contain MCP-specific security risk: ",
         "Identify tool poisoning, version drift, excessive scope, confused-deputy conditions, and "
         "prompt injection through ingested device data; distinguish visibility from authorization; "
         "apply MCP security scanning to a running server."),
        ("Build the client side of the contract: ",
         "Implement a minimal MCP client with an LLM loop, capability declaration, elicitation "
         "(approval) handling, progress and notification handling, and sampling — and fill in the "
         "capability matrix for a client they wrote."),
        ("Test and promote an MCP server: ",
         "Build contract tests over the SDK's in-memory transport and a scenario suite against known "
         "network conditions, and move a change from the production-representative device through a "
         "validation gate to a controlled, reversible rollout."),
    ])
    b.rule()

    # ---- agenda ------------------------------------------------------------
    b.h1("Agenda at a Glance")
    b.lead("Approximately 75% hands-on. Times are elapsed from session start; two 10-minute breaks and a 45-minute lunch are included.")
    b.bullets([
        ("0:00–0:35 — ", "Orientation — baseline checkpoint, protocol internals, trust boundaries, pre-flight on each participant's own server instance"),
        ("0:35–1:25 — ", "Module 1 — Protocol on the wire and production-grade servers · Lab 1"),
        ("1:25–1:35 — ", "Break"),
        ("1:35–2:35 — ", "Module 2 — Tool and schema engineering · Lab 2"),
        ("2:35–3:25 — ", "Module 3 — Multi-source context and correlation · Lab 3"),
        ("3:25–4:10 — ", "Lunch"),
        ("4:10–5:40 — ", "Module 4 — Safety, identity and write-path control · Labs 4 and 5"),
        ("5:40–5:50 — ", "Break"),
        ("5:50–6:35 — ", "Module 5 — The client side of the contract · Lab 6"),
        ("6:35–7:40 — ", "Module 6 and Capstone — testing, promotion, and the validated change · Lab 7"),
        ("7:40–8:00 — ", "Wrap-up — capability matrix, hardening roadmap, take-home assignments"),
    ], justify=False)
    b.rule()

    # ---- modules -----------------------------------------------------------
    b.h1("Modules")

    b.module("Orientation: Scope, Baseline & the Engineering Problem", [
        "Protocol baseline, taught fast — host, client, and server roles; JSON-RPC framing; the "
        "lifecycle from initialize through capability negotiation to close; Streamable HTTP session "
        "mechanics; the six primitives and who controls each (model, application, user)",
        "What breaks in real deployments — tools an agent cannot choose between, errors an agent "
        "cannot act on, write paths with no gate, and clients that silently ignore half the protocol",
        "Three trust boundaries that organise the day — model ↔ tool result, client ↔ server, "
        "server ↔ device — and the lab that exercises each",
        "Scope boundary — where MCP responsibility ends and agent orchestration begins, and why the "
        "tool layer is the harder engineering problem",
        "Design targets for the day — determinism, auditability, repeatability, and rollback awareness",
    ], [
        "Pre-flight — start a personal MCP server instance against the shared lab routers, connect "
        "MCP Inspector, verify the client development environment",
    ])

    b.module("Module 1: Protocol on the Wire & Production-Grade Servers", [
        "Server implementation patterns — project structure, decorator-based tool registration, "
        "configuration, and blocking device I/O isolated in worker threads for a server more than "
        "one team will maintain",
        "Transports in practice — stdio for local and single-operator use versus Streamable HTTP for "
        "shared and remote servers; session identifiers, server-to-client streams, and resumption",
        "Authentication and identity — bearer tokens at the transport layer today, OAuth 2.1 for "
        "remote access in production; service versus per-operator identity; credential storage; "
        "propagating operator identity into device sessions",
        "Sessions, concurrency, and audit — connection lifecycle, safe concurrent access to shared "
        "devices, and the structured record every invocation must leave to be defensible after the fact",
        "Reading a production client — where a real MCP client handles 401, server instructions, "
        "progress-driven timeouts, and declares its capabilities",
    ], [
        "Lab 1 — trace the protocol on the wire in MCP Inspector, then drive a Streamable HTTP "
        "session by hand; connect a chat client end to end through an authentication failure; add "
        "structured per-invocation audit logging to the server",
    ])

    b.module("Module 2: Tool and Schema Engineering", [
        "Tool granularity — one tool per operator intent versus one tool per command or API "
        "endpoint, and how granularity drives selection accuracy",
        "Input schema design — types, enums, constraints, defaults, and rejecting ambiguous or unsafe "
        "input at the boundary; exact-match allowlists versus prefix matching",
        "Output schema design — returning structured evidence rather than raw device text, and "
        "shaping results so conclusions are supportable",
        "Descriptions and annotations — writing tool metadata, including read-only, destructive, and "
        "idempotent hints, so selection is deterministic",
        "Error semantics — distinguishing invalid input, unauthorized, unreachable, partial, and "
        "timed-out; errors as tool results the agent can read and act on",
        "Contract testing — exercising the tool surface over the SDK's in-memory transport with the "
        "device layer mocked, so a server gains a CI gate without a router",
    ], [
        "Lab 2 — build a read-only device tool, refactor endpoint-shaped tools into intent-shaped "
        "tools with strict schemas, structured output, and annotations, then measure agent selection "
        "accuracy before and after; write contract tests that run green with no device attached",
    ])

    b.module("Module 3: Multi-Source Context and Correlation", [
        "Resources versus tools — interface tables, running configuration, baselines, and golden "
        "configuration as resources; resource templates for parameterised context; why running "
        "configuration is served as a resource but refused as a command",
        "Prompts as server-authored runbooks — user-invoked templates that reference the server's "
        "own tools and resources; the naming collision with client-local prompt libraries",
        "Server-side correlation — assembling cross-device evidence at the server, because a device "
        "cannot be assessed in isolation and the agent should not be stitching raw payloads together",
        "Context budget — summarisation, field selection, and payload limits; what to return and "
        "what to withhold",
        "Caching, idempotency, and rate limits — protecting production devices from agent-driven "
        "query volume",
        "Worked Cisco endpoints (discussion) — mapping the same patterns to Nexus and ACI, SD-WAN, "
        "Intersight, and ServiceNow as tool and resource sources",
    ], [
        "Lab 3 — expose resources, a resource template, and prompts; add a second device to the "
        "server inventory and implement a correlation tool that returns assembled cross-device evidence",
    ])

    b.module("Module 4: Safety, Identity and Write-Path Control", [
        "Read/write separation — enforcing the boundary in server code and authorization, never in "
        "the prompt; role-based tool visibility versus role-based enforcement (hiding is UX, "
        "authorization is enforcement)",
        "The controlled write path — pre-flight dry run, schema validation, policy check, explicit "
        "approval, apply, verify, and rollback; pre-change snapshots as the rollback anchor",
        "Human approval as a server-side gate — elicitation, structuring the approval request so the "
        "approver sees the actual intended change and its blast radius, and graceful degradation "
        "when a client cannot approve",
        "Dynamic servers — tool-list change notifications and resource subscriptions as the "
        "mechanism behind runtime capability control",
        "Prompt injection through ingested data — instructions hidden in interface descriptions, "
        "syslog, ticket text, or telemetry the agent reads",
        "MCP-specific threats — tool poisoning, rug-pull and version drift, confused deputy, "
        "excessive scope, and over-broad credentials; scanning a server's tool surface",
    ], [
        "Lab 4 — gate a state-changing tool behind role checks, pre-flight validation, policy check, "
        "explicit human approval, verification, and demonstrated rollback; observe the same tool "
        "degrade safely in a client without approval support",
        "Lab 5 — prove that a hidden tool is still refused when called by name; deliver a live "
        "injection attempt through a device interface description and contain it; scan the running "
        "server with MCP security scanners such as MCP-Scan and Cisco AI Defense MCP Scanner (DefenseClaw)",
    ])

    b.module("Module 5: The Client Side of the Contract", [
        "Why the host matters — approval gates, sampling, and live tool-list refresh exist only when "
        "the client implements them; the capability matrix as a readable fact, not an opinion",
        "The agent loop — MCP tool schemas to LLM function calls, tool results back into the "
        "conversation, termination",
        "Capability declaration — what changes on the wire when a client advertises elicitation, and "
        "how the server detects it",
        "Handlers — elicitation (terminal approval), progress, logging, notifications with automatic "
        "tool re-listing, and sampling (the server borrowing the client's model)",
    ], [
        "Lab 6 — build a minimal Python MCP client in stages: connect and list, agent loop, "
        "elicitation handler, progress and notification handlers, sampling; complete the capability "
        "matrix row for the client you wrote",
    ])

    b.module("Module 6: Testing, Promotion and Operations", [
        "Testing tool behaviour — contract tests, golden fixtures, and device simulators for "
        "repeatable results",
        "Scenario suites — exercising the server against known network conditions and asserting on "
        "returned evidence",
        "Environment separation and the validation gate — production-representative versus live "
        "operations, why they never share a wire, and the evidence required before a change is "
        "permitted in live operations",
        "Rollout and runtime operations — staged deployment, secret handling, rollback, and ongoing "
        "review of tool error rates, latency, scope, and audit records",
    ], [])

    b.module("Capstone: The Validated Change", [
        "Scenario — a broken end-to-end condition in the production-representative device with no "
        "stated root cause",
        "Diagnosis — correlated evidence, probable root cause, and a specific remediation, produced "
        "through the participant's own MCP server driven by the participant's own client",
        "Execution — propose the change, validate it on the production-representative device with "
        "recorded evidence, run the scenario suite, promote through the approval gate to the "
        "live-operations device, verify, and demonstrate rollback",
        "Debrief — reviewing the audit trail and identifying the remaining gaps between the workshop "
        "server and a production deployment",
    ], [
        "Lab 7 — diagnose, fix through the controlled write path with approval, verification, and "
        "demonstrated rollback; reconstruct what happened to the live-operations device from the "
        "audit record alone",
    ])

    b.module("Wrap-Up: Capability Matrix and Hardening Roadmap", [
        "Capability matrix, three columns — MCP Inspector, the participant's client, and a "
        "production coding agent (take-home): which primitive each consumes and who controls it",
        "Hardening roadmap — OAuth 2.1, containerised deployment with secret handling, publishing a "
        "server entry to the MCP Registry, structured observability, per-operator identity",
        "Take-home assignments — prompts and resources with a production client, OAuth 2.1 "
        "conversion, containerise and publish, capstone stretch goals",
    ], [])
    b.rule()

    # ---- labs outline ------------------------------------------------------
    b.h1("Labs Outline")
    b.bullets([
        "Trace the protocol on the wire, drive a Streamable HTTP session by hand, connect a chat client "
        "through an authentication failure, and add per-invocation audit logging",
        "Build and refactor tools into intent-shaped tools with strict schemas, structured output, "
        "and annotations; measure selection accuracy; write contract tests",
        "Expose resources, templates, and prompts; add a second device and implement server-side "
        "cross-device correlation",
        "Gate a state-changing tool behind roles, validation, policy check, human approval, "
        "verification, and rollback",
        "Prove hidden ≠ authorized, contain a prompt-injection attempt delivered through device "
        "data, and run an MCP security scan",
        "Build a minimal MCP client with approval, notification, and sampling handlers, and complete "
        "its capability matrix row",
        "Capstone: diagnose a broken end-to-end condition and apply an approved, validated, verified, "
        "reversible fix through the promotion gate",
    ])
    b.rule()

    # ---- takeaways ---------------------------------------------------------
    b.h1("What Participants Take Away")
    b.bullets([
        "A working MCP server for network operations: authenticated, role-aware, audited, and running "
        "over Streamable HTTP against the lab estate",
        "An intent-shaped tool, resource, and prompt set with strict schemas, annotations, and "
        "structured error semantics",
        "A controlled write path with pre-flight validation, policy check, human approval, "
        "verification, and rollback — and a client that can actually approve",
        "A minimal MCP client, a contract and scenario test suite, and the promotion evidence pattern, "
        "ready to adapt to their own environment",
        "A completed capability matrix explaining what \"MCP support\" means, client by client",
    ])
    b.rule()

    # ---- audience ----------------------------------------------------------
    b.h1("Target Audience")
    b.bullets([
        "Network Automation Engineers and NetDevOps teams building agent-facing tooling",
        "Platform, DevOps, and SRE engineers responsible for internal tool and API surfaces",
        "Software Developers integrating AI agents with infrastructure systems",
        "AI Systems Engineers and solution teams delivering agentic operations capability",
        "Network Architects and Operations Leads accountable for change safety and auditability",
        "Security Engineers assessing agent and tool exposure in operational environments",
    ])
    b.rule()

    # ---- skill level -------------------------------------------------------
    b.h1("Skill Level & Assumed Knowledge")
    b.lead(
        "This is a hands-on engineering course. Participants write and debug server-side and "
        "client-side Python throughout the day and should be comfortable with the following:"
    )
    b.bullets([
        ("Python — ", "functions, modules, type hints, exception handling, and basic asynchronous "
         "programming; prior use of a schema or validation library is an advantage"),
        ("APIs and data formats — ", "REST, JSON, and JSON Schema; reading and writing structured "
         "request and response payloads"),
        ("Networking — ", "working knowledge of interfaces, IP addressing, and routing on Cisco IOS, "
         "and familiarity with operational troubleshooting"),
        ("Tooling — ", "confident use of a development environment, CLI, SSH, and version control"),
        ("MCP — ", "not assumed. The Orientation block establishes the protocol baseline at pace; "
         "participants who have completed the 4-hour MCP Essentials workshop will find it a rapid "
         "checkpoint rather than a re-teach"),
    ])
    b.body(
        "No experience with agent orchestration frameworks is required. This course covers the "
        "server, tool, and client-contract layers; agent reasoning, orchestration frameworks, and "
        "multi-agent design are out of scope."
    )
    b.rule()

    # ---- prerequisites -----------------------------------------------------
    b.h1("Prerequisites")
    b.bullets([
        "Internet access and a working local development environment with Python 3.11+ and Git",
        "Ability to install packages and run a local HTTP service on the workshop machine",
        "Node.js 22+ for MCP Inspector",
        "Access to the Criterion-provided production-representative lab environment (server host, "
        "two Cisco IOS routers, and the LLM API key issued for the session)",
    ])

    b.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    print(build())
