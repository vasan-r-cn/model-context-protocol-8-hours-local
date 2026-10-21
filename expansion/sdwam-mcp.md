# SD-WAN MCP Server and Gradio App

A FastMCP 2.x-based Model Context Protocol (MCP) server for Cisco SD-WAN (vManage), with an optional Gradio UI for interactive testing.

This project allows a single LLM agent to query SD-WAN state, inventory, health, tunnels, templates, and policies using natural language, via multiple MCP tools.

Architecture: Single-Agent plus Multi-Tool (MCP). This is not a multi-agent system by default.

---

## 1. Objectives

By the end of this section, you will be able to:

- Explain what MCP, the Model Context Protocol, actually buys you over the `@tool`-decorated functions from the previous three sections.
- Trace the split between the two files, client and server, and say which process does what, and in which order they need to be started.
- Explain why the MCP client and its discovered tools are cached, while the LLM and agent are recreated on every single request.
- State precisely why this chat app has no memory between turns, despite looking like a normal conversational UI.

## 2. Note on Scope

- This section is a bigger architectural jump than the last three. There is no checkpointer, no `thread_id`, and no hand-written system prompt here. Tool descriptions come entirely from the MCP server's own docstrings.
- Two separate Python processes are involved: a FastMCP server, which is the tool provider, and a Gradio client, which is the chat UI and agent. The server must be running before the client can discover any tools.

## 3. Before You Start

Every previous section had exactly one Python file and one `@tool`-decorated function living in the same process as the agent. This section splits that in two: a tool server that knows nothing about agents, and an agent client that knows nothing about vManage. They only talk to each other over MCP. You will start the server first, then the client, and then ask it questions through a browser-based chat UI.

---

## 4. Key Terms

- MCP (Model Context Protocol) — a standard protocol for exposing tools to an LLM agent over a network connection, instead of defining them as local Python functions that the agent's process imports directly.
- FastMCP — the Python framework used here to build the MCP server, meaning the process that defines and exposes the actual vManage-calling tools.
- MultiServerMCPClient — the client-side object that connects to one or more MCP servers and discovers what tools they expose, so the agent can call them without knowing their implementation.
- Streamable HTTP transport — the specific connection method used between this client and server, `transport: "streamable_http"`, as opposed to the stdio-based MCP transports used for local-only tools.

---

## 5. Concept — Two Things Cached, Two Things Not

This section's client code makes a deliberate and easy-to-miss distinction. The MCP client and its discovered tools are cached globally, in `_mcp_client` and `_mcp_tools`, guarded by an `asyncio.Lock`. A fresh LLM and a fresh agent, by contrast, are created on every single chat message, because `create_llm()` and `create_agent(llm, tools)` both run inside `chat_handler` rather than once at startup.

Why the split?

- Discovering tools from the MCP server is a network round-trip. It is expensive to repeat on every message, and the tools themselves do not change between requests, so caching them is free efficiency.
- The LLM and agent are cheap to construct and hold no meaningful state worth preserving. Recreating them per request means one slow or failing user request can never leak state into another user's request. This is what "safe concurrency" means in the closing paragraph of the client code below.

A second and more surprising thing is worth confirming for yourself. Look at `chat_handler(message: str, history: List)` in the code below. The `history` parameter is a real parameter that Gradio populates with the full conversation so far, and it is never referenced anywhere else in the function. Only `message` reaches the agent. This app has the visual shape of a memory-preserving chatbot, which was the previous section's territory, but it is in fact completely memory-less between turns.

---

## 6. Key Characteristics

Single agent:

- One LangChain agent is created per request.
- There are no planner, executor, or validator agents.
- There is no agent-to-agent communication.

Multi-tool:

- Multiple SD-WAN capabilities are exposed as MCP tools.
- Tool discovery and invocation happen via MCP.

## 7. Features

- MCP-compliant SD-WAN tool server
- LLM-friendly tools, covering inventory, health, tunnels, templates, and policies
- Name-to-ID resolution, for both devices and templates
- Transport health and tunnel visibility
- A Gradio UI for manual testing and demonstrations

## 8. Requirements

- Python 3.9 or later
- Cisco vManage (SD-WAN)
- Network access to vManage
- Valid vManage credentials

---

Execute the following command on the `CCL Orchestrator` device

## 9. Path

Move into the MCP directory:

```bash
cd /home/ubuntu/agentic-ai-workshop/mcp/sdwan
```

---

## 10. The Client (`sdwan_mcp_client.py`)

View the client:

```bash
cat sdwan_mcp_client.py
```

```python
"""
Gradio UI + LangChain Agent + MCP Client
Used to connect SD-WAN / ThousandEyes MCP tools to an LLM agent
"""

import os
import asyncio
import gradio as gr
from dotenv import load_dotenv
from typing import List

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_openrouter import ChatOpenRouter

# =================================================
# 1. ENVIRONMENT SETUP
# =================================================

# Load variables from .env file
load_dotenv()

# API key for OpenRouter (LLM access)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# MCP server endpoint (your FastMCP SD-WAN server)
REMOTE_URL = os.getenv(
    "MCP_SERVER_URL",
    "http://127.0.0.1:7004/mcp"
)

if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY is not set")

# =================================================
# 2. MCP CLIENT (SINGLETON)
# =================================================

# Global cache variables
_mcp_client: MultiServerMCPClient | None = None
_mcp_tools = None

# Async lock for concurrency safety
_mcp_lock = asyncio.Lock()


async def get_mcp_tools():
    """
    Initialize MCP client once and cache tools.
    """
    global _mcp_client, _mcp_tools

    async with _mcp_lock:

        # Return cached tools
        if _mcp_tools is not None:
            return _mcp_tools

        # Configure MCP server
        _mcp_client = MultiServerMCPClient(
            {
                "sdwan": {
                    "transport": "streamable_http",
                    "url": REMOTE_URL,
                }
            }
        )

        try:
            # Discover tools from MCP server
            _mcp_tools = await asyncio.wait_for(
                _mcp_client.get_tools(),
                timeout=10,
            )

        except Exception as e:
            raise RuntimeError(
                f"Failed to connect to MCP server: {e}"
            )

        return _mcp_tools


# =================================================
# 3. LLM FACTORY
# =================================================

def create_llm():
    """
    Create a fresh LLM instance per request.
    """

    return ChatOpenRouter(
        model="google/gemini-3.1-flash-lite-preview",
        temperature=0,
        openrouter_api_key=OPENROUTER_API_KEY,
        timeout=30,
        max_retries=2,
    )


# =================================================
# 4. CHAT HANDLER (AGENT EXECUTION)
# =================================================

async def chat_handler(message: str, history: List):
    """
    Main Gradio chat handler.

    Flow:
    User → Agent → MCP Tools → LLM → Response
    """

    try:

        # Load MCP tools
        tools = await get_mcp_tools()

        # Create LLM instance
        llm = create_llm()

        # Create agent per request
        agent = create_agent(llm, tools)

        final_response = ""

        # Stream agent response
        async for chunk in agent.astream(
            {
                "messages": [
                    ("user", message),
                ]
            },
            stream_mode="values",
        ):

            if "messages" in chunk:

                msg = chunk["messages"][-1]

                if hasattr(msg, "content") and msg.content:
                    final_response = msg.content

        return final_response

    except asyncio.TimeoutError:

        return (
            "Timeout while contacting SD-WAN services."
        )

    except Exception as e:

        return (
            "Error processing request.\n\n"
            f"Details: {str(e)}\n"
            f"Ensure MCP server is running at "
            f"{REMOTE_URL}"
        )


# =================================================
# 5. GRADIO UI
# =================================================

demo = gr.ChatInterface(
    fn=chat_handler,
    title="SD-WAN Assistant",
    description=(
        "SD-WAN assistant using "
        "LangChain Agents + MCP tools"
    ),
)

# =================================================
# 6. APPLICATION ENTRYPOINT
# =================================================

if __name__ == "__main__":

    demo.launch(
        server_name="0.0.0.0",
        share=True
    )
```

This script builds a Gradio-based chat UI that runs a single LangChain agent backed by an LLM.

The agent dynamically discovers and invokes SD-WAN and ThousandEyes MCP tools from a FastMCP server using the Model Context Protocol (MCP). The MCP client and tools are cached for efficiency, while a new stateless agent and LLM instance are created per user request, to ensure safe concurrency.

---

## 10.1 The Server (`sdwan_mcp_server.py`)

View the server:

```bash
cat sdwan_mcp_server.py
```

```python
"""
SD-WAN MCP Server FastMCP implementation
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import json
from typing import Any, Dict

import httpx
from fastmcp import FastMCP
from dotenv import load_dotenv

from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware


load_dotenv()

# ---------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------
logging.basicConfig(
    level=os.getenv("MCP_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger("sdwan.mcp")


# ---------------------------------------------------------------------
# Environment Configuration
# ---------------------------------------------------------------------
VMANAGE_USERNAME = os.getenv("VMANAGE_USERNAME", "admin")
VMANAGE_PASSWORD = os.getenv("VMANAGE_PASSWORD", "admin123")
HTTP_TIMEOUT = float(os.getenv("VMANAGE_HTTP_TIMEOUT", "30"))
DEFAULT_FQDN = os.getenv("FQDN")

logger.debug("DEFAULT_FQDN=%s", DEFAULT_FQDN)

if not VMANAGE_USERNAME or not VMANAGE_PASSWORD:
    raise RuntimeError("vManage credentials are not configured")


# ---------------------------------------------------------------------
# Initialize FastMCP Server
# ---------------------------------------------------------------------
mcp = FastMCP(name="sdwan-mcp")


# ---------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------
def fix_url(fqdn: str) -> str:
    """
    Normalize vManage FQDN into HTTPS URL.
    Always returns: https://<fqdn>:443
    """
    fqdn = fqdn.strip().replace("https://", "").replace(":443", "")
    return f"https://{fqdn}:443"


async def vmanage_login(
    base_url: str,
    username: str,
    password: str,
) -> httpx.AsyncClient:
    """
    Login to vManage using j_security_check.
    Returns an authenticated AsyncClient.
    """

    client = httpx.AsyncClient(
        verify=False,
        timeout=httpx.Timeout(HTTP_TIMEOUT),
        follow_redirects=False,
    )

    login_url = f"{base_url}/j_security_check"

    resp = await client.post(
        login_url,
        data={
            "j_username": username,
            "j_password": password,
        },
    )

    # vManage returns HTML on auth failure
    if resp.status_code != 200 or "html" in resp.text.lower():
        await client.aclose()
        raise RuntimeError("vManage authentication failed")

    return client


async def vmanage_get(
    client: httpx.AsyncClient,
    base_url: str,
    path: str,
) -> Any:
    """Generic GET wrapper for vManage dataservice APIs."""

    url = f"{base_url}{path}"

    resp = await client.get(url)
    resp.raise_for_status()

    return resp.json().get("data", resp.json())


async def resolve_device_id(
    client,
    base_url,
    name_or_ip: str,
) -> str:

    devices = await vmanage_get(
        client,
        base_url,
        "/dataservice/device",
    )

    for d in devices:
        if (
            d.get("system-ip") == name_or_ip
            or d.get("host-name") == name_or_ip
        ):
            return d["system-ip"]

    raise ValueError(
        f"Device not found: {name_or_ip}"
    )


async def vmanage_get_raw(
    client,
    base_url: str,
    path: str,
) -> str:

    url = f"{base_url}{path}"

    resp = await client.get(url)
    resp.raise_for_status()

    return resp.text


async def resolve_feature_template_id(
    client: httpx.AsyncClient,
    base_url: str,
    name_or_id: str,
) -> str:
    """
    Resolve feature template name OR ID → templateId
    """

    templates = await vmanage_get(
        client,
        base_url,
        "/dataservice/template/feature",
    )

    for t in templates:
        if (
            t.get("templateId") == name_or_id
            or t.get("templateName") == name_or_id
        ):
            return t["templateId"]

    raise ValueError(
        f"Feature template not found: {name_or_id}"
    )


async def resolve_device_template_id(
    client: httpx.AsyncClient,
    base_url: str,
    name_or_id: str,
) -> str:
    """
    Resolve device template name OR ID → templateId
    """

    templates = await vmanage_get(
        client,
        base_url,
        "/dataservice/template/device",
    )

    for t in templates:
        if (
            t.get("templateId") == name_or_id
            or t.get("templateName") == name_or_id
        ):
            return t["templateId"]

    raise ValueError(
        f"Device template not found: {name_or_id}"
    )


# ---------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------

@mcp.tool()
async def get_inventory(
    fqdn: str | None = None,
) -> Dict[str, Any]:
    """Fetch full SD-WAN device inventory."""

    fqdn = fqdn or DEFAULT_FQDN

    logger.info(
        f"Tool called: get_inventory with {fqdn}"
    )

    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)

    client = await vmanage_login(
        base_url,
        VMANAGE_USERNAME,
        VMANAGE_PASSWORD,
    )

    try:
        devices = await vmanage_get(
            client,
            base_url,
            "/dataservice/device",
        )

        return {
            "inventory": devices
        }

    finally:
        await client.aclose()


@mcp.tool()
async def get_wan_edge_devices(
    fqdn: str | None = None,
) -> Dict[str, Any]:
    """Retrieve WAN Edge (vEdge / cEdge) inventory."""

    fqdn = fqdn or DEFAULT_FQDN

    logger.info(
        f"Tool called: get_wan_edge_devices with {fqdn}"
    )

    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)

    client = await vmanage_login(
        base_url,
        VMANAGE_USERNAME,
        VMANAGE_PASSWORD,
    )

    try:
        vedges = await vmanage_get(
            client,
            base_url,
            "/dataservice/system/device/vedges",
        )

        return {
            "wan_edges": vedges
        }

    finally:
        await client.aclose()


@mcp.tool()
async def get_control_plane_status(
    device: str,
    fqdn: str | None = None,
) -> Dict[str, Any]:
    """Fetch control plane connection status for a device."""

    fqdn = fqdn or DEFAULT_FQDN

    logger.info(
        f"Tool called: get_control_plane_status with {fqdn}"
    )

    if not fqdn:
        raise ValueError("fqdn must be provided")

    if not device:
        raise ValueError("device is required")

    base_url = fix_url(fqdn)

    client = await vmanage_login(
        base_url,
        VMANAGE_USERNAME,
        VMANAGE_PASSWORD,
    )

    device_id = await resolve_device_id(
        client,
        base_url,
        device,
    )

    try:
        status = await vmanage_get(
            client,
            base_url,
            f"/dataservice/device/control/connections?deviceId={device_id}",
        )

        return {
            "control_plane_status": status
        }

    finally:
        await client.aclose()


@mcp.tool()
async def get_device_interfaces(
    device: str,
    fqdn: str | None = None,
) -> Dict[str, Any]:
    """Retrieve interface details for a device (hostname or system-ip)."""

    fqdn = fqdn or DEFAULT_FQDN

    logger.info(
        f"Tool called: get_device_interfaces with {fqdn}"
    )

    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)

    client = await vmanage_login(
        base_url,
        VMANAGE_USERNAME,
        VMANAGE_PASSWORD,
    )

    try:
        device_id = await resolve_device_id(
            client,
            base_url,
            device,
        )

        interfaces = await vmanage_get(
            client,
            base_url,
            f"/dataservice/device/interface?deviceId={device_id}",
        )

        return {
            "device": device,
            "device_id": device_id,
            "interfaces": interfaces,
        }

    finally:
        await client.aclose()


@mcp.tool()
async def get_device_template_attachments(
    fqdn: str | None = None,
) -> Dict[str, Any]:
    """
    Returns device-to-template attachment mapping.
    Uses /dataservice/device.
    """

    fqdn = fqdn or DEFAULT_FQDN

    logger.info(
        f"Tool called: get_device_template_attachments with {fqdn}"
    )

    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)

    client = await vmanage_login(
        base_url,
        VMANAGE_USERNAME,
        VMANAGE_PASSWORD,
    )

    try:
        devices = await vmanage_get(
            client,
            base_url,
            "/dataservice/device",
        )

        attachments = [
            {
                "device": d.get("host-name"),
                "system_ip": d.get("system-ip"),
                "device_model": d.get("device-model"),
                "template_id": d.get("templateId"),
                "template_name": d.get("templateName"),
            }
            for d in devices
            if d.get("templateId")
        ]

        return {
            "total_attached_devices": len(attachments),
            "attachments": attachments,
        }

    finally:
        await client.aclose()


@mcp.tool()
async def get_transport_health_summary(
    device: str,
    fqdn: str | None = None,
) -> Dict[str, Any]:
    """Transport health using version-safe BFD API."""

    fqdn = fqdn or DEFAULT_FQDN

    logger.info(
        f"Tool called: get_transport_health_summary with {fqdn}"
    )

    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)

    client = await vmanage_login(
        base_url,
        VMANAGE_USERNAME,
        VMANAGE_PASSWORD,
    )

    try:
        device_id = await resolve_device_id(
            client,
            base_url,
            device,
        )

        device_bfd = await vmanage_get(
            client,
            base_url,
            f"/dataservice/device/bfd/sessions?deviceId={device_id}",
        )

        down = [
            s
            for s in device_bfd
            if s.get("state") != "up"
        ]

        return {
            "transport_health": {
                "device": device,
                "device_id": device_id,
                "total_sessions": len(device_bfd),
                "down_sessions": len(down),
                "down_details": down,
            }
        }

    finally:
        await client.aclose()


@mcp.tool()
async def get_health_status(
    fqdn: str | None = None,
) -> Dict[str, Any]:
    """Fetch health status for all SD-WAN devices."""

    fqdn = fqdn or DEFAULT_FQDN

    logger.info(
        f"Tool called: get_health_status with {fqdn}"
    )

    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)

    client = await vmanage_login(
        base_url,
        VMANAGE_USERNAME,
        VMANAGE_PASSWORD,
    )

    try:
        health = await vmanage_get(
            client,
            base_url,
            "/dataservice/device/monitor",
        )

        return {
            "health": health
        }

    finally:
        await client.aclose()


@mcp.tool()
async def get_alarms(
    fqdn: str | None = None,
) -> Dict[str, Any]:
    """Fetch all active SD-WAN alarms."""

    fqdn = fqdn or DEFAULT_FQDN

    logger.info(
        f"Tool called: get_alarms with {fqdn}"
    )

    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)

    client = await vmanage_login(
        base_url,
        VMANAGE_USERNAME,
        VMANAGE_PASSWORD,
    )

    try:
        alarms = await vmanage_get(
            client,
            base_url,
            "/dataservice/alarms",
        )

        return {
            "alarms": alarms
        }

    finally:
        await client.aclose()


@mcp.tool()
async def get_events(
    limit: int = 20,
    fqdn: str | None = None,
) -> Dict[str, Any]:
    """Retrieves recent events/logs. Use limit to control output size (default 20)."""

    fqdn = fqdn or DEFAULT_FQDN

    logger.info(
        f"Tool called: get_events with {fqdn}"
    )

    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)

    client = await vmanage_login(
        base_url,
        VMANAGE_USERNAME,
        VMANAGE_PASSWORD,
    )

    try:
        events = await vmanage_get(
            client,
            base_url,
            "/dataservice/event",
        )

        return {
            "events": events
        }

    finally:
        await client.aclose()


@mcp.tool()
async def get_device_tunnels(
    device: str,
    fqdn: str | None = None,
) -> Dict[str, Any]:
    """Retrieve SD-WAN tunnels using device-specific, RBAC-safe endpoints."""

    fqdn = fqdn or DEFAULT_FQDN

    logger.info(
        f"Tool called: get_device_tunnels with {fqdn}"
    )

    base_url = fix_url(fqdn)

    client = await vmanage_login(
        base_url,
        VMANAGE_USERNAME,
        VMANAGE_PASSWORD,
    )

    try:
        # Device ID must be the System-IP
        device_id = await resolve_device_id(
            client,
            base_url,
            device,
        )

        # Data-plane tunnels
        device_bfd = await vmanage_get(
            client,
            base_url,
            f"/dataservice/device/bfd/sessions?deviceId={device_id}",
        )

        # Control-plane tunnels
        control_connections = await vmanage_get(
            client,
            base_url,
            f"/dataservice/device/control/connections?deviceId={device_id}",
        )

        return {
            "device": device,
            "device_id": device_id,
            "tunnels": {
                "data_plane": {
                    "type": "IPsec / BFD",
                    "total": len(device_bfd),
                    "down": [
                        s
                        for s in device_bfd
                        if s.get("state") != "up"
                    ],
                    "sessions": device_bfd,
                },
                "control_plane": {
                    "type": "DTLS / TLS",
                    "total": len(control_connections),
                    "down": [
                        c
                        for c in control_connections
                        if c.get("state") != "up"
                    ],
                    "connections": control_connections,
                },
            },
        }

    finally:
        await client.aclose()


@mcp.tool()
async def get_down_devices(
    fqdn: str | None = None,
) -> Dict[str, Any]:
    """List devices that are not in normal health state."""

    fqdn = fqdn or DEFAULT_FQDN

    logger.info(
        f"Tool called: get_down_devices with {fqdn}"
    )

    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)

    client = await vmanage_login(
        base_url,
        VMANAGE_USERNAME,
        VMANAGE_PASSWORD,
    )

    try:
        health = await vmanage_get(
            client,
            base_url,
            "/dataservice/device/monitor",
        )

        down = [
            d
            for d in health
            if d.get("status") != "normal"
        ]

        return {
            "down_devices": down
        }

    finally:
        await client.aclose()


@mcp.tool()
async def get_feature_templates(
    fqdn: str | None = None,
) -> str:
    """Lists all Feature Templates."""

    fqdn = fqdn or DEFAULT_FQDN

    logger.info(
        f"Tool called: get_feature_templates with {fqdn}"
    )

    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)

    client = await vmanage_login(
        base_url,
        VMANAGE_USERNAME,
        VMANAGE_PASSWORD,
    )

    try:
        data = await vmanage_get(
            client,
            base_url,
            "/dataservice/template/feature",
        )

        if isinstance(data, dict) and "data" in data:
            simplified = [
                {
                    k: v
                    for k, v in item.items()
                    if k in [
                        "templateId",
                        "templateName",
                        "deviceType",
                        "templateType",
                    ]
                }
                for item in data["data"]
            ]

            return json.dumps(
                simplified,
                indent=2,
            )

        return json.dumps(
            data,
            indent=2,
        )

    finally:
        await client.aclose()


@mcp.tool()
async def get_device_templates(
    fqdn: str | None = None,
) -> str:
    """Lists all Device Templates defined in vManage."""

    fqdn = fqdn or DEFAULT_FQDN

    logger.info(
        f"Tool called: get_device_templates with {fqdn}"
    )

    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)

    client = await vmanage_login(
        base_url,
        VMANAGE_USERNAME,
        VMANAGE_PASSWORD,
    )

    try:
        data = await vmanage_get(
            client,
            base_url,
            "/dataservice/template/device",
        )

        if isinstance(data, dict) and "data" in data:
            simplified = [
                {
                    k: v
                    for k, v in item.items()
                    if k in [
                        "templateId",
                        "templateName",
                        "deviceType",
                        "devicesAttached",
                    ]
                }
                for item in data["data"]
            ]

            return json.dumps(
                simplified,
                indent=2,
            )

        return json.dumps(
            data,
            indent=2,
        )

    finally:
        await client.aclose()


@mcp.tool()
async def get_feature_template_details(
    template: str,
    fqdn: str | None = None,
) -> Dict[str, Any]:
    """Retrieves the full definition of a Feature Template, including variable names."""

    fqdn = fqdn or DEFAULT_FQDN

    logger.info(
        f"Tool called: get_feature_template_details with {fqdn}"
    )

    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)

    client = await vmanage_login(
        base_url,
        VMANAGE_USERNAME,
        VMANAGE_PASSWORD,
    )

    try:
        template_id = await resolve_feature_template_id(
            client,
            base_url,
            template,
        )

        template_details = await vmanage_get(
            client,
            base_url,
            f"/dataservice/template/feature/object/{template_id}",
        )

        return {
            "template_details": template_details
        }

    finally:
        await client.aclose()


@mcp.tool()
async def get_device_template_details(
    template: str,
    fqdn: str | None = None,
) -> Dict[str, Any]:
    """Retrieves the full configuration object for a specific Device Template."""

    fqdn = fqdn or DEFAULT_FQDN

    logger.info(
        f"Tool called: get_device_template_details with {fqdn}"
    )

    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)

    client = await vmanage_login(
        base_url,
        VMANAGE_USERNAME,
        VMANAGE_PASSWORD,
    )

    try:
        template_id = await resolve_device_template_id(
            client,
            base_url,
            template,
        )

        template_details = await vmanage_get(
            client,
            base_url,
            f"/dataservice/template/device/object/{template_id}",
        )

        return {
            "template_details": template_details
        }

    finally:
        await client.aclose()


@mcp.tool()
async def get_centralized_policies(
    fqdn: str | None = None,
) -> Dict[str, Any]:
    """Lists Centralized Policy definitions (vSmart policies)."""

    fqdn = fqdn or DEFAULT_FQDN

    logger.info(
        f"Tool called: get_centralized_policies with {fqdn}"
    )

    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)

    client = await vmanage_login(
        base_url,
        VMANAGE_USERNAME,
        VMANAGE_PASSWORD,
    )

    try:
        policies = await vmanage_get(
            client,
            base_url,
            "/dataservice/template/policy/vsmart",
        )

        return {
            "policies": policies
        }

    finally:
        await client.aclose()


@mcp.tool()
async def get_control_connections(
    device: str,
    fqdn: str | None = None,
) -> Dict[str, Any]:
    """Retrieves control connections (DTLS/TLS) for a device."""

    fqdn = fqdn or DEFAULT_FQDN

    logger.info(
        f"Tool called: get_control_connections with {fqdn}"
    )

    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)

    client = await vmanage_login(
        base_url,
        VMANAGE_USERNAME,
        VMANAGE_PASSWORD,
    )

    device_id = await resolve_device_id(
        client,
        base_url,
        device,
    )

    try:
        connections = await vmanage_get(
            client,
            base_url,
            f"/dataservice/device/control/connections?deviceId={device_id}",
        )

        return {
            "connections": connections
        }

    finally:
        await client.aclose()


@mcp.tool()
async def get_running_config(
    device: str,
    fqdn: str | None = None,
) -> str:
    """Retrieves the full running configuration of a device."""

    fqdn = fqdn or DEFAULT_FQDN

    logger.info(
        f"Tool called: get_running_config with {fqdn}"
    )

    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)

    client = await vmanage_login(
        base_url,
        VMANAGE_USERNAME,
        VMANAGE_PASSWORD,
    )

    try:
        device_id = await resolve_device_id(
            client,
            base_url,
            device,
        )

        config = await vmanage_get_raw(
            client,
            base_url,
            f"/dataservice/device/config?deviceId={device_id}",
        )

        return config

    finally:
        await client.aclose()


@mcp.tool()
async def generate_audit_report(
    fqdn: str | None = None,
) -> Dict[str, Any]:
    """Generate a simple SD-WAN audit summary."""

    fqdn = fqdn or DEFAULT_FQDN

    logger.info(
        f"Tool called: generate_audit_report with {fqdn}"
    )

    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)

    client = await vmanage_login(
        base_url,
        VMANAGE_USERNAME,
        VMANAGE_PASSWORD,
    )

    try:
        devices = await vmanage_get(
            client,
            base_url,
            "/dataservice/device",
        )

        health = await vmanage_get(
            client,
            base_url,
            "/dataservice/device/monitor",
        )

        alarms = await vmanage_get(
            client,
            base_url,
            "/dataservice/alarms",
        )

        return {
            "audit_report": {
                "total_devices": len(devices),
                "down_devices": len(
                    [
                        d
                        for d in health
                        if d.get("status") != "normal"
                    ]
                ),
                "alarm_count": len(alarms),
            }
        }

    finally:
        await client.aclose()


# ---------------------------------------------------------------------
# Server Entrypoint
# ---------------------------------------------------------------------
if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="SD-WAN MCP Server"
    )

    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Bind address",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=7004,
        help="Bind port",
    )

    args = parser.parse_args()

    logger.info(
        "Starting SD-WAN MCP server on %s:%s",
        args.host,
        args.port,
    )

    # -----------------------------------------------------------------
    # CORS configuration
    #
    # Required when connecting to this MCP server from the
    # browser-based MCP Inspector.
    # -----------------------------------------------------------------
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=[
                "GET",
                "POST",
                "DELETE",
                "OPTIONS",
            ],
            allow_headers=[
                "mcp-protocol-version",
                "mcp-session-id",
                "authorization",
                "content-type",
            ],
            expose_headers=[
                "mcp-session-id",
            ],
        )
    ]

    # -----------------------------------------------------------------
    # FastMCP Streamable HTTP application
    # -----------------------------------------------------------------
    app = mcp.http_app(
        path="/mcp",
        middleware=middleware,
    )

    # -----------------------------------------------------------------
    # Start Uvicorn
    # -----------------------------------------------------------------
    import uvicorn

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
    )

```

This script implements a FastMCP 2.x-based SD-WAN MCP server that exposes Cisco vManage capabilities as multiple MCP tools. Each tool authenticates with vManage, calls the appropriate dataservice REST APIs, and returns structured results.

The server acts purely as a tool provider, containing no agent logic, and is designed to be consumed by LLMs or agents via the Model Context Protocol (MCP) over streamable HTTP.

---

## 11. Run MCP Inspector

**Step 1:** Start the server on CCL-Device:**

```bash
python3 sdwan_mcp_server.py
```
![](https://sdcloud-imgs.s3.amazonaws.com/sandboxes/Screenshot_from_2026-09-10_12-26-28.png)
**Step 2:** start mcp inspector  on linux-desktop-65 **

```
HOST=0.0.0.0 DANGEROUSLY_BIND_ALL_INTERFACES=true npx @modelcontextprotocol/inspector@1.0.1 --port 6274
```
![](https://sdcloud-imgs.s3.amazonaws.com/sandboxes/Screenshot_from_2026-09-10_12-29-01.png)
**Step 3** open-inspector url**

```
copy the inspector url and replace localhost:6274 with fqdn:20790
```
**Step 4:** Accessing inspector via public-browser**

![](https://sdcloud-imgs.s3.amazonaws.com/sandboxes/e7d94383-d497-4aa9-a55a-1f69ae1f158f.PNG)


### Connect to the MCP Server

1. Select **Streamable HTTP** as the **Transport Type**.

2. Select **Direct** as the **Connection Type**.

3. In the **URL** field, copy and paste the following MCP server URL:


```
http://<fqdn>:20700/mcp
```
**Note:** Replace <fqdn> with the FQDN of your cluster.

4. Click **Connect** to establish the connection to the MCP server.

**Expected Result:**
The MCP Inspector connects successfully to the MCP server, and the available MCP tools can be viewed.



**Don't stop/Close the sdwan mcp server on CCL-Device; we will reuse this in MCP Defence**

Run this command in a new tab in CCL-Device to start the client:

```bash
python3 sdwan_mcp_client.py
```
![](https://sdcloud-imgs.s3.amazonaws.com/sandboxes/ubuntu-cclorchestrator78-agentic-ai-workshop-mcp-sdwan-09-10-2026_12_51_PM.png)
## 12. Test the SD-WAN Assistant

```
Are there any Devices Down in my SD-WAN network?
```

```
Get the full SD-WAN device inventory.
```
![](https://sdcloud-imgs.s3.amazonaws.com/sandboxes/SD-WAN-Assistant-09-10-2026_12_52_PM.png)
```
Show the health status of all SD-WAN devices.
```

```
Give me a complete SD-WAN audit report.
```

---

## 13. Walkthrough

### 1. Client — MCP Client Singleton

Purpose:

- Connects to the MCP server exactly once, discovers its tools, and caches both behind a lock, so that concurrent requests cannot trigger duplicate connections.
- The 10-second timeout is what turns "the server isn't running" into a clean `RuntimeError` instead of an indefinite hang.

Predict first: if the MCP server is not running yet when a user sends the very first chat message, what will the user actually see in the Gradio UI?

What actually happens: the `except Exception as e: raise RuntimeError(...)` inside `get_mcp_tools()` propagates up into `chat_handler`'s own broad `except Exception as e:` block, which returns the friendly "Error processing request... Ensure MCP server is running at {REMOTE_URL}" message rather than a raw traceback.

### 2. Client — Chat Handler and the Missing history

Purpose:

- Loads the cached tools, builds a fresh LLM and agent, and streams the agent's response using `stream_mode="values"`. This is a third stream mode, distinct from the `updates` and `custom` pair from the previous section. The `values` mode yields the full accumulated state after each step, which is why the code simply grabs `chunk&#91;"messages"&#93;&#91;-1&#93;` each time rather than branching on stream type.
- `history` is accepted but never used. See the Concept block above. Confirm this yourself by searching the function body for the word `history`.

Checkpoint: if a user asks "What's in my inventory?" and then, in the very next message, asks "How many of those are online?", will the agent be able to answer the second question correctly?

Answer: not reliably. Since `history` is not passed to the agent, the second message is sent with no awareness that a first question or its answer ever existed. The agent would need to call a tool again from scratch, and "those" has no antecedent for it to resolve.

### 3. Server — A Representative MCP Tool

Purpose:

- The `@mcp.tool()` decorator is this section's equivalent of the earlier sections' `@tool`. It is what makes this function discoverable and callable by any MCP client, including the one in this same section.
- All five tools on the server share this exact shape: resolve an `fqdn`, guard against a missing one, log in, call an endpoint, and always close the client in a `finally` block. `get_health_status`, `get_alarms`, `get_device_interfaces`, and `generate_audit_report` are variations on this same pattern. Once you understand this one, you understand all five.

Two behaviours to watch for when you run it, both visible directly in the source above:

- Each tool writes its own log line to the server's terminal, via `logger.info(f"Tool called: get_inventory with {fqdn}")`. That line is how you confirm which tool the agent actually chose.
- If no `fqdn` is passed and `FQDN` is absent from `.env`, the guard clause raises `ValueError("fqdn must be provided")` before any network call is attempted. This applies identically to all five tools, since they follow the same pattern.

### 4. Server — generate_audit_report Aggregates the Others

Purpose:

- Calls the same underlying `vmanage_get` requests that `get_inventory`, `get_health_status`, and `get_alarms` each make individually, but re-implements each call rather than reusing those three functions directly.
- Returns a single summarized dict, containing `total_devices`, `down_devices`, and `alarm_count`, instead of the three raw payloads. This is what makes it useful as a one-shot audit answer.

Checkpoint: if `get_health_status`'s underlying endpoint changed its response shape, would `generate_audit_report` be affected?

Answer: yes, and separately from `get_health_status` itself. Since the aggregation duplicates the same `vmanage_get` call rather than calling the `get_health_status` tool function, a shape change would need to be fixed in two places, not one.

---

## 14. Hands-On Challenge

Work in a copy of both files so the canonical lab stays intact:

```bash
cp sdwan_mcp_server.py my_mcp_server.py
cp sdwan_mcp_client.py my_mcp_client.py
```

### Challenge 1

- Start the server first, with `python3 my_mcp_server.py`, then the client, with `python3 my_mcp_client.py`, in a separate tab, and open the Gradio UI it launches.
- Ask one of the four sample prompts above and confirm, from the server's own terminal log, exactly which tool name got called.
- Stop the server, then send another message from the still-running client's UI. Confirm that you get the friendly "Ensure MCP server is running..." message rather than a raw error.
- You can name the exact tool the server logged for your chosen prompt.
- You can describe what happened in the UI when the server was stopped mid-session.

### Challenge 2

- Confirm the missing-memory behaviour yourself: ask "Get the full SD-WAN device inventory", then immediately ask "How many of those are online?" in the same chat session.
- Modify `my_mcp_client.py` so that `chat_handler` actually uses `history`, passing the prior turns into the `messages` list sent to `agent.astream(...)`, in the same `("user", ...)` and `("assistant", ...)` tuple shape that Gradio's history uses.
- Re-run the same two-question sequence and confirm that the second answer now correctly references the first.
- You can describe, from direct observation, how the unmodified code failed to connect the two questions.
- `history` is passed into the messages sent to the agent in your modified version.
- The second question is answered correctly using context from the first, in your modified version.

### Challenge 3

* Add one new @mcp.tool() function to my_mcp_server.py, under the MCP TOOLS section. The Features list at the top of this section promises tools for tunnel visibility, and it does not exist yet. You will add get_tunnel_status.
* Restart the server, then restart the client so that it rediscovers the tool list.
* Ask "Show me the tunnel status for all SD-WAN devices" in the Gradio UI and confirm from the server's own terminal which tool actually fired.
* Your tool follows the same six-step shape as the existing five, including the finally block that closes the client.
* Its docstring says what the tool is for and explicitly rules out at least one neighbouring tool.
* The server log line proves your tool fired, not one of the original five.

```python
@mcp.tool()
async def your_tool_name(
    fqdn: str | None = None
) -> Dict[str, Any]:
    """
    One line saying what this returns.
    Use this ONLY for questions about <your topic>.
    Do NOT use it for <a neighbouring tool's topic> --
    use <that tool's name> for that.
    """
    # 1. fall back to the .env FQDN if the caller did not pass one
    fqdn = fqdn or DEFAULT_FQDN
    # 2. log the call, so you can prove which tool the agent chose
    logger.info(
        f"Tool called: your_tool_name with {fqdn}"
    )
    # 3. guard clause -- fail before touching the network
    if not fqdn:
        raise ValueError("fqdn must be provided")
    # 4. normalise the FQDN and authenticate
    base_url = fix_url(fqdn)
    client = await vmanage_login(
        base_url,
        VMANAGE_USERNAME,
        VMANAGE_PASSWORD,
    )
    try:
        # 5. call your endpoint
        result = await vmanage_get(
            client,
            base_url,
            "/dataservice/<your-endpoint-here>"
        )
        return {
            "your_key": result
        }
    # 6. always close the client, even on failure
    finally:
        await client.aclose()
```
<details><summary><strong>Hint</strong></summary>
Use the below instruction inside Dict:
Retrieve SD-WAN overlay tunnel status for one device.
Use this ONLY for questions about BFD sessions, tunnel state, overlay connectivity, or which remote sites a device is currently reaching. 
Do NOT use this for device reachability or hardware health -- use `get_health_status` for that, and `get_device_interfaces` for physical interface details. </details>
---

## 15. Quiz

1. What does MCP let you do that the `@tool` decorator from the previous sections did not?

2. Why are the MCP client and its tools cached, while the agent and LLM are not?

3. Does this chat app remember earlier turns in the conversation? How do you know, from the code?

4. If the MCP server is not running when the client starts up, what does the end user actually see?

<details><summary><strong>Answer key</strong></summary>
<ul>
<li>Q1 — Tools can live in a completely separate process, even on a separate machine, be discovered dynamically at runtime, and be reused by any MCP-compatible client, rather than being local Python functions that the agent's own process has to import directly.</li>
<li>Q2 — Tool discovery is a network round-trip and the tool list does not change per request, so caching it is pure efficiency. The LLM and agent are cheap to recreate and hold no state worth preserving, so recreating them per request keeps concurrent users' requests fully isolated from each other.</li>
<li>Q3 — No. `chat_handler(message, history)` never references `history` anywhere in its body. Only `message` is sent to the agent, so every turn is answered with zero awareness of any prior turn.</li>
<li>Q4 — A friendly error message, "Error processing request... Ensure MCP server is running at {REMOTE_URL}", rather than a raw traceback, because `get_mcp_tools()`'s `RuntimeError` is caught by `chat_handler`'s own broad exception handler.</li>
</ul>
</details>

---

## 16. FAQ

Why split this into a client and a server instead of one file, like every previous section?

- This is the actual point of MCP: tools become a service that other agents or clients could also connect to, rather than being locked inside one script. It is a shift from "one agent, its own local tools" to "a tool provider anything can connect to".

Could I add a memory checkpointer to this client, the same way Agent with Memory did?

- Yes. Nothing about the MCP architecture prevents it. It is a separate concern from tool discovery; you would add a checkpointer and pass `history` into the agent call, similar to Challenge 2 above.

Why does generate_audit_report re-fetch data that the other tools already fetch separately?

- It is a design choice, not a requirement. This way `generate_audit_report` does not depend on the other tool functions still existing or behaving identically, at the cost of duplicating the underlying calls.

What happens if two users chat at the same time?

- Each gets a completely fresh LLM and agent instance for their own request, as described in the Concept block above. Both share the same cached MCP client and tool list, which is safe because that cache is read-only once populated.

---

## 17. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Every message in the Gradio UI returns "Error processing request... Ensure MCP server is running at {REMOTE_URL}" | The MCP server process is not running, has crashed, or is listening on a different host or port than `MCP_SERVER_URL`, or the default `http://127.0.0.1:7004/mcp`, points to | Confirm the server process is running, and check that its bound host and port match the client's configured URL |
| A follow-up question gets answered as if the first question never happened | This is expected behaviour, not a bug. `history` is never passed to the agent | See Challenge 2 for how to actually wire memory in |
| `RuntimeError: vManage credentials are not configured` on server startup | `VMANAGE_USERNAME` or `VMANAGE_PASSWORD` is missing from `.env`. Note that this server does fall back to `admin` and `admin123` defaults, so this error only appears if those environment variables are explicitly set to empty values | Either set real credentials in `.env`, or confirm the defaults are acceptable for your lab environment |
| The client hangs for exactly 10 seconds before failing | This matches the `asyncio.wait_for(..., timeout=10)` in `get_mcp_tools()`. The server is unreachable, or too slow to respond to tool discovery | The same as the first symptom above: verify that the server is actually running and reachable |

---

## 18. Quick Reference

| Concept | Detail |
|---|---|
| New architecture versus previous sections | Tools live on a separate FastMCP server process, and the client discovers them dynamically via `MultiServerMCPClient` instead of importing `@tool`-decorated functions directly |
| Cached | The MCP client connection and its discovered tool list, `_mcp_client` and `_mcp_tools` |
| Recreated every request | The LLM, via `create_llm()`, and the agent, via `create_agent(llm, tools)`, for safe concurrency |
| No memory between turns | `chat_handler`'s `history` parameter is accepted but never used |
| Five server-side MCP tools | `get_inventory`, `get_health_status`, `get_alarms`, `get_device_interfaces`, and `generate_audit_report`, all sharing one login, fetch, and return pattern |
| Run order matters | Start `sdwan_mcp_server.py` before `sdwan_mcp_client.py` |