"""Cisco Router MCP Server — workshop edition.

FastMCP (official MCP Python SDK) served over Streamable HTTP at /mcp,
mounted inside a FastAPI app that keeps the unauthenticated GET / health
check. Demonstrates all workshop primitives: tools (with annotations,
progress, structured output), resources (incl. a template), prompts,
tool-list-changed notifications, resource subscriptions, and an
elicitation confirmation gate with graceful degradation.

Lab defaults (router IP, credentials, auth token) are intentional for the
workshop environment and can be overridden via environment variables —
see .env.example.
"""

from __future__ import annotations

import logging
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Literal

import anyio
from fastapi import FastAPI
from netmiko import ConnectHandler
from pydantic import AnyUrl, BaseModel, Field

from mcp import types
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.lowlevel import NotificationOptions

from app import inventory as inv

# ---------------------------------------------------------------------------
# Configuration (env-overridable; defaults match the lab topology)
# ---------------------------------------------------------------------------

# Devices come from inventory.yaml via app/inventory.py. Every device-touching
# tool takes a `device` argument whose default is a production-representative
# device, so a call that omits it cannot reach production.
DeviceName = Literal[inv.DEVICE_NAMES]  # type: ignore[valid-type]
DEFAULT_DEVICE = inv.DEFAULT_DEVICE

MCP_AUTH_TOKEN = os.environ.get("MCP_AUTH_TOKEN", "cisco-mcp-workshop")

SNAPSHOT_DIR = Path(os.environ.get("MCP_SNAPSHOT_DIR", Path(__file__).resolve().parent.parent / "snapshots"))

# Exact-match allowlist for dynamic_show. Deliberately NOT prefix matching:
# `startswith("show")` would allow `show running-config` (credential
# exposure) and IOS pipe/redirect abuse (`show run | redirect tftp://...`).
ALLOWED_SHOW_COMMANDS = {
    "show ip interface brief",
    "show interfaces description",
    "show ip route",
    "show ip protocols",
    "show ip ospf neighbor",
    "show version",
    "show clock",
    "show inventory",
    "show arp",
    "show cdp neighbors",
}

RUNNING_CONFIG_URI = f"device://{inv.DEFAULT_DEVICE}/running-config"

# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "cisco-router-mcp",
    instructions=(
        "Operates a live Cisco lab network: a DC site (production), a DR site "
        "(production-representative), two branches, and a legacy site. Every "
        "device-touching tool takes a `device` argument — call list_devices "
        "first if you are unsure which device to use. Tools marked read-only "
        "are safe on any device. configure_interface and create_loopback "
        "modify live configuration and are accepted only on "
        "production-representative devices; always confirm with the user "
        "before calling them, and state exactly what will change. To change "
        "production, validate on a production-representative device first, "
        "then promote."
    ),
    streamable_http_path="/mcp",
)


# ---------------------------------------------------------------------------
# SSH helpers — Netmiko is blocking, so every call runs in a worker thread
# ---------------------------------------------------------------------------

def _run_show(command: str, device: str) -> str:
    connection = ConnectHandler(**inv.get(device).netmiko_args())
    try:
        return connection.send_command(command)
    finally:
        connection.disconnect()


def _run_config(commands: list[str], device: str) -> str:
    connection = ConnectHandler(**inv.get(device).netmiko_args())
    try:
        connection.enable()
        return connection.send_config_set(commands)
    finally:
        connection.disconnect()


async def run_show(command: str, device: str = inv.DEFAULT_DEVICE) -> str:
    """Run a show command on `device`. Blocking SSH, so it goes to a thread."""
    if not inv.get(device).reachable:
        raise RuntimeError(
            f"device {device!r} has no management address configured in "
            f"{inv.INVENTORY_PATH.name}"
        )
    return await anyio.to_thread.run_sync(_run_show, command, device)


async def run_config(commands: list[str], device: str = inv.DEFAULT_DEVICE) -> str:
    """Apply config to `device`. Callers MUST have cleared inv.may_write_to()."""
    return await anyio.to_thread.run_sync(_run_config, commands, device)


def _save_snapshot(config_text: str, device: str) -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = SNAPSHOT_DIR / f"{device}-running-config-{stamp}.txt"
    path.write_text(config_text)
    return path


def _latest_snapshot(device: str) -> Path | None:
    if not SNAPSHOT_DIR.is_dir():
        return None
    snapshots = sorted(SNAPSHOT_DIR.glob(f"{device}-running-config-*.txt"))
    return snapshots[-1] if snapshots else None


# ---------------------------------------------------------------------------
# Resource subscriptions
#
# FastMCP has no subscription API, so the handlers register on the wrapped
# low-level server. Subscribers are remembered per session; config-writing
# tools call _notify_config_changed() to push notifications/resources/updated.
# ---------------------------------------------------------------------------

_low_level = mcp._mcp_server
_subscriptions: list[tuple[object, str]] = []  # (ServerSession, uri)


@_low_level.subscribe_resource()
async def _on_subscribe(uri: AnyUrl) -> None:
    session = _low_level.request_context.session
    entry = (session, str(uri))
    if entry not in _subscriptions:
        _subscriptions.append(entry)


@_low_level.unsubscribe_resource()
async def _on_unsubscribe(uri: AnyUrl) -> None:
    session = _low_level.request_context.session
    entry = (session, str(uri))
    if entry in _subscriptions:
        _subscriptions.remove(entry)


async def _notify_config_changed() -> None:
    for session, uri in list(_subscriptions):
        if uri != RUNNING_CONFIG_URI:
            continue
        try:
            await session.send_resource_updated(AnyUrl(uri))
        except Exception:
            _subscriptions.remove((session, uri))  # session is gone


# ---------------------------------------------------------------------------
# Elicitation confirmation gate (graceful degradation)
#
# Inspector supports elicitation and shows a confirmation dialog. LibreChat
# advertises no client capabilities, so eliciting against it would fail —
# capability negotiation decides which path runs. That split is the lesson.
#
# Spec rule: elicitation must NEVER be used to collect secrets/credentials.
# ---------------------------------------------------------------------------

class ConfirmChange(BaseModel):
    confirm: bool = Field(description="Apply this configuration change to the live router?")


async def _confirm_change(ctx: Context, description: str) -> tuple[bool, str]:
    """Returns (proceed, warning). Empty warning when the client confirmed."""
    supports_elicitation = ctx.session.check_client_capability(
        types.ClientCapabilities(elicitation=types.ElicitationCapability())
    )
    if not supports_elicitation:
        return True, (
            "WARNING: client does not support elicitation — change applied "
            "without interactive confirmation.\n\n"
        )
    result = await ctx.elicit(
        message=f"{description} This modifies a live lab router. Proceed?",
        schema=ConfirmChange,
    )
    if result.action == "accept" and result.data and result.data.confirm:
        return True, ""
    return False, ""


# ---------------------------------------------------------------------------
# Read-only tools
# ---------------------------------------------------------------------------

@mcp.tool(annotations=types.ToolAnnotations(readOnlyHint=True))
async def get_interfaces(ctx: Context, device: DeviceName = DEFAULT_DEVICE) -> str:
    """Get a device's interfaces and their status (show ip interface brief)."""
    await ctx.report_progress(0, 1, f"Connecting to {device} over SSH...")
    try:
        output = await run_show("show ip interface brief", device)
    except Exception as exc:
        return f"Error talking to {device}: {exc}"
    await ctx.report_progress(1, 1, "Done")
    return f"{device} interfaces:\n\n{output}"


@mcp.tool(annotations=types.ToolAnnotations(readOnlyHint=True))
async def list_devices() -> str:
    """List every lab device with its site, role, and whether it is writable.

    Call this first when a request names a site ("DC", "DR", "the branch")
    rather than a device, or when you need to know which device a change may
    be applied to.
    """
    return inv.describe()


class RouterInfo(BaseModel):
    """Structured output — clients see this as the tool's outputSchema."""

    hostname: str
    version: str
    uptime: str


@mcp.tool(annotations=types.ToolAnnotations(readOnlyHint=True))
async def get_router_info(ctx: Context, device: DeviceName = DEFAULT_DEVICE) -> RouterInfo:
    """Get a device's hostname, software version, and uptime."""
    await ctx.report_progress(0, 1, f"Collecting show version from {device}...")
    output = await run_show("show version", device)
    await ctx.report_progress(1, 1, "Done")

    hostname, version, uptime = "unknown", "unknown", "unknown"
    for line in output.splitlines():
        line = line.strip()
        if " uptime is " in line:
            hostname, _, uptime = line.partition(" uptime is ")
        elif line.startswith("Cisco IOS") and "Version" in line:
            version = line.split("Version", 1)[1].strip().split(",")[0]
    return RouterInfo(hostname=hostname.strip(), version=version, uptime=uptime.strip())


@mcp.tool(annotations=types.ToolAnnotations(readOnlyHint=True))
async def dynamic_show(command: str, ctx: Context, device: DeviceName = DEFAULT_DEVICE) -> str:
    """Run a read-only Cisco show command on a device.

    Only an exact allowlist of show commands is accepted. If the command is
    rejected, pick the closest allowed command from the error message and
    retry.
    """
    normalized = " ".join(command.lower().split())
    if normalized not in ALLOWED_SHOW_COMMANDS:
        allowed = "\n".join(sorted(ALLOWED_SHOW_COMMANDS))
        return (
            f"Command rejected: {command!r} is not on the allowlist.\n"
            f"Allowed commands:\n{allowed}"
        )
    await ctx.report_progress(0, 1, f"Running {normalized!r} on {device}...")
    try:
        output = await run_show(normalized, device)
    except Exception as exc:
        return f"Error talking to {device}: {exc}"
    await ctx.report_progress(1, 1, "Done")
    return f"{device}# {normalized}\n\n{output}"


@mcp.tool(annotations=types.ToolAnnotations(readOnlyHint=True))
async def snapshot_config(ctx: Context, device: DeviceName = DEFAULT_DEVICE) -> str:
    """Capture a device's running config to a timestamped snapshot file.

    Snapshots are the rollback/reset anchor: take one before config changes.
    """
    await ctx.report_progress(0, 1, f"Capturing running-config from {device}...")
    try:
        output = await run_show("show running-config", device)
    except Exception as exc:
        return f"Error talking to {device}: {exc}"
    path = _save_snapshot(output, device)
    await ctx.report_progress(1, 1, "Done")
    return f"Snapshot saved to {path} ({len(output.splitlines())} lines)."


# ---------------------------------------------------------------------------
# Config-writing tools
#
# Defined as plain functions and registered/unregistered at runtime by
# enable_config_tools, which fires notifications/tools/list_changed.
# Operational pattern being modeled: destructive capability is an explicit
# toggle, not an always-on default.
# ---------------------------------------------------------------------------

_CONFIG_TOOL_ANNOTATIONS = types.ToolAnnotations(readOnlyHint=False, destructiveHint=True)


async def configure_interface(
    interface: str, ip_address: str, ctx: Context, device: DeviceName = DEFAULT_DEVICE
) -> str:
    """Configure an interface with an IP address (/24) and bring it up.

    Modifies live configuration. Accepted only on production-representative
    devices. A pre-change snapshot is taken automatically.
    """
    allowed, reason = inv.may_write_to(device)
    if not allowed:
        return reason
    proceed, warning = await _confirm_change(
        ctx, f"About to configure {interface} with {ip_address}/24 on {device}."
    )
    if not proceed:
        return "Change cancelled by user."
    try:
        pre_change = await run_show("show running-config", device)
        snapshot = _save_snapshot(pre_change, device)
        commands = [
            f"interface {interface}",
            f"ip address {ip_address} 255.255.255.0",
            "no shutdown",
        ]
        output = await run_config(commands, device)
    except Exception as exc:
        return f"Error talking to {device}: {exc}"
    await _notify_config_changed()
    return (
        f"{warning}Configured {interface} with {ip_address}/24 on {device} "
        f"(pre-change snapshot: {snapshot}).\n\n{output}"
    )


async def create_loopback(
    loopback_id: int, ctx: Context, device: DeviceName = DEFAULT_DEVICE
) -> str:
    """Create a loopback interface on a device.

    Accepted only on production-representative devices. The description
    MCP_CREATED marks it for the lab reset script.
    """
    allowed, reason = inv.may_write_to(device)
    if not allowed:
        return reason
    proceed, warning = await _confirm_change(
        ctx, f"About to create interface Loopback{loopback_id} on {device}."
    )
    if not proceed:
        return "Change cancelled by user."
    try:
        commands = [f"interface Loopback{loopback_id}", "description MCP_CREATED"]
        output = await run_config(commands, device)
    except Exception as exc:
        return f"Error talking to {device}: {exc}"
    await _notify_config_changed()
    return f"{warning}Loopback{loopback_id} created on {device}.\n\n{output}"


_CONFIG_TOOLS = {"configure_interface": configure_interface, "create_loopback": create_loopback}


def _register_config_tools() -> None:
    for name, fn in _CONFIG_TOOLS.items():
        if mcp._tool_manager.get_tool(name) is None:
            mcp.add_tool(fn, name=name, annotations=_CONFIG_TOOL_ANNOTATIONS)


def _unregister_config_tools() -> None:
    for name in _CONFIG_TOOLS:
        # The SDK's ToolManager has no remove_tool; lab-grade reach-in.
        mcp._tool_manager._tools.pop(name, None)


@mcp.tool()
async def enable_config_tools(enabled: bool, ctx: Context) -> str:
    """Enable or disable the config-writing tools (configure_interface, create_loopback).

    Fires notifications/tools/list_changed so subscribed clients refresh
    their tool list live.
    """
    if enabled:
        _register_config_tools()
    else:
        _unregister_config_tools()
    await ctx.session.send_tool_list_changed()
    state = "enabled" if enabled else "disabled"
    return f"Config-writing tools {state}. Clients were notified via tools/list_changed."


# Enabled at startup so the LibreChat lab works out of the box (LibreChat only
# discovers tools at startup — it ignores list_changed). Set
# MCP_CONFIG_TOOLS_DEFAULT=disabled to start in the locked-down state.
if os.environ.get("MCP_CONFIG_TOOLS_DEFAULT", "enabled").lower() != "disabled":
    _register_config_tools()


# ---------------------------------------------------------------------------
# Resources — application-controlled context (the client decides to read
# them), in contrast to tools, which the model decides to call.
# LibreChat does not consume resources; these are for the Inspector labs.
# ---------------------------------------------------------------------------

@mcp.resource(
    f"device://{inv.DEFAULT_DEVICE}/interfaces",
    description=f"Live interface table for {inv.DEFAULT_DEVICE} (show ip interface brief)",
)
async def interfaces_resource() -> str:
    return await run_show("show ip interface brief")


@mcp.resource(
    RUNNING_CONFIG_URI,
    description=f"Live running configuration of {inv.DEFAULT_DEVICE}",
)
async def running_config_resource() -> str:
    return await run_show("show running-config")


# Resource template: one URI shape covers every device in the inventory.
@mcp.resource(
    "device://{device}/running-config",
    description="Live running configuration of any device in the inventory",
)
async def device_running_config_resource(device: str) -> str:
    if device not in inv.DEVICES:
        return f"Unknown device {device!r}. Known devices: {', '.join(inv.DEVICE_NAMES)}."
    try:
        return await run_show("show running-config", device)
    except Exception as exc:
        return f"Error talking to {device}: {exc}"


@mcp.resource(
    "device://{device}/interfaces/{name}",
    description="Detail for one interface on one device (show interfaces <name>)",
)
async def interface_detail_resource(device: str, name: str) -> str:
    if device not in inv.DEVICES:
        return f"Unknown device {device!r}. Known devices: {', '.join(inv.DEVICE_NAMES)}."
    try:
        return await run_show(f"show interfaces {name}", device)
    except Exception as exc:
        return f"Error talking to {device}: {exc}"


@mcp.resource(
    f"device://{inv.DEFAULT_DEVICE}/baseline",
    description="Most recent running-config snapshot (rollback anchor)",
)
def baseline_resource() -> str:
    snapshot = _latest_snapshot(inv.DEFAULT_DEVICE)
    if snapshot is None:
        return "No snapshot captured yet. Run the snapshot_config tool first."
    return snapshot.read_text()


# ---------------------------------------------------------------------------
# Prompts — user-controlled templates surfaced by the client.
# (LibreChat's own "Prompts" feature is an unrelated local library.)
# ---------------------------------------------------------------------------

@mcp.prompt(title="Troubleshoot an interface")
def troubleshoot_interface(interface: str, device: str = inv.DEFAULT_DEVICE) -> str:
    """Guided interface triage. Given an interface name (and optionally a
    device), produce a step-by-step plan: check status, read the interface
    detail resource, list likely causes, confirm with allowed show commands,
    and propose a fix that flags whether it touches live config."""
    return (
        f"Troubleshoot {interface} on {device} step by step:\n"
        f"1. Check its status with get_interfaces (device={device}) — is it "
        f"up/up, down/down, or administratively down?\n"
        f"2. Read device://{device}/interfaces/{interface} for errors, drops, "
        f"and line-protocol detail.\n"
        f"3. List the most likely causes for the state you found "
        f"(shutdown, no IP, cable/far end, duplex/speed).\n"
        f"4. Recommend the exact show commands to confirm the root cause, "
        f"using only commands dynamic_show allows.\n"
        f"5. Propose a fix, and state clearly whether it changes live config."
    )


@mcp.prompt(title="Audit a device configuration")
def audit_router_config(device: str = inv.DEFAULT_DEVICE) -> str:
    """Read-only config audit. Given a device, review its running-config
    resource against a safety checklist (undescribed up interfaces, admin-down
    interfaces holding an IP, MCP_CREATED workshop loopbacks, weak SNMP
    communities, other production-unsafe settings) and report findings as a
    table. Does not propose changes unless asked."""
    return (
        f"Audit {device}'s running configuration (resource "
        f"device://{device}/running-config) against this checklist and report "
        f"findings as a table:\n"
        "- Interfaces that are up but have no description\n"
        "- Interfaces administratively down that carry an IP address\n"
        "- Loopbacks tagged MCP_CREATED (workshop leftovers to clean up)\n"
        "- Weak or default SNMP community strings\n"
        "- Anything else that looks unsafe for a production device\n"
        "Do not propose config changes unless asked."
    )


# ---------------------------------------------------------------------------
# Capability advertisement
#
# The SDK's default initialization options hardcode resources.subscribe=False
# and omit listChanged. Wrap create_initialization_options so the initialize
# response tells the truth about what this server does (visible in Lab 1).
# ---------------------------------------------------------------------------

_original_create_init_options = _low_level.create_initialization_options


def _create_init_options(notification_options=None, experimental_capabilities=None):
    options = _original_create_init_options(
        notification_options or NotificationOptions(tools_changed=True, resources_changed=True),
        experimental_capabilities,
    )
    if options.capabilities.resources is not None:
        options.capabilities.resources.subscribe = True
    return options


_low_level.create_initialization_options = _create_init_options


# ---------------------------------------------------------------------------
# Bearer-token auth — plain HTTP auth at the transport layer, guarding /mcp
# only. GET / stays open so students can health-check before touching auth.
# ---------------------------------------------------------------------------

class BearerAuthMiddleware:
    """Pure ASGI middleware (BaseHTTPMiddleware buffers streaming responses)."""

    def __init__(self, app, token: str, protected_path: str = "/mcp"):
        self.app = app
        self.expected = f"Bearer {token}"
        self.protected_path = protected_path

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].startswith(self.protected_path):
            headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
            provided = headers.get("authorization", "")
            if not secrets.compare_digest(provided, self.expected):
                # Say WHY it failed (without ever logging the token) so
                # students can self-diagnose 401s from the server terminal.
                if not provided:
                    reason = "no Authorization header sent"
                elif not provided.startswith("Bearer "):
                    reason = f"header does not start with 'Bearer ' (starts with {provided[:10]!r})"
                elif provided.startswith("Bearer Bearer"):
                    reason = "token was entered WITH the 'Bearer ' prefix — enter the token only"
                else:
                    reason = (
                        f"token mismatch (received {len(provided) - 7} chars, "
                        f"expected {len(self.expected) - 7} — check MCP_AUTH_TOKEN/.env and stray spaces)"
                    )
                logging.getLogger("cisco-mcp.auth").warning("401 on %s: %s", scope["path"], reason)
                await send({
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"www-authenticate", b"Bearer"),
                    ],
                })
                await send({
                    "type": "http.response.body",
                    "body": (
                        b'{"error": "unauthorized", "hint": "Send header '
                        b'Authorization: Bearer <MCP_AUTH_TOKEN> (see .env.example)"}'
                    ),
                })
                return
        await self.app(scope, receive, send)


# ---------------------------------------------------------------------------
# FastAPI wrapper: health check + mounted Streamable HTTP endpoint
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="Cisco Network MCP Server", lifespan=lifespan)


@app.get("/")
def root():
    unconfigured = [n for n, d in inv.DEVICES.items() if not d.reachable]
    return {
        "status": "Cisco Network MCP Server Running",
        "devices": len(inv.DEVICES),
        "default_device": inv.DEFAULT_DEVICE,
        "writable_devices": list(inv.writable_names()),
        "devices_without_management_address": unconfigured,
        "mcp_endpoint": "/mcp",
        "transport": "streamable-http",
        "auth": "Authorization: Bearer <MCP_AUTH_TOKEN>",
    }


# Mounted last: the exact GET / route above wins; everything else (i.e. /mcp)
# is handled by the FastMCP Streamable HTTP app.
app.mount("/", mcp.streamable_http_app())
app.add_middleware(BearerAuthMiddleware, token=MCP_AUTH_TOKEN)
