"""
SD-WAN MCP Server (FastMCP 2.x) — Module 5, exercise 5.1.

Vendored from agentic-ai-workshop/mcp/sdwan/sdwan_mcp_server.py with two
adaptations for the per-pod topology:
  * host is read from VMANAGE_HOST (falls back to FQDN) for consistency with
    code/agents and multi_agent_v2;
  * fix_url() respects an explicit :port (the pod exposes vManage on a NAT
    port, not :443) and only defaults to :443 when no port is given.

Serves Streamable HTTP on :7004 (path /mcp). Read-only: every tool is a GET
against the vManage dataservice API after a j_security_check login.

    export VMANAGE_HOST=<your pod FQDN>:<exposed vmanage port>
    export VMANAGE_USERNAME=admin VMANAGE_PASSWORD=admin123
    python sdwan_mcp_server.py        # or ./run.sh
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
DEFAULT_FQDN = os.getenv("VMANAGE_HOST") or os.getenv("FQDN")
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
    """Normalize a vManage host into an HTTPS base URL.

    Respects an explicit port (the pod exposes vManage on a NAT port);
    defaults to :443 only when no port is given.
    """
    fqdn = fqdn.strip().replace("https://", "").rstrip("/")
    if ":" not in fqdn:
        fqdn = f"{fqdn}:443"
    return f"https://{fqdn}"


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
        data={"j_username": username, "j_password": password},
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

async def resolve_device_id(client, base_url, name_or_ip: str) -> str:
    devices = await vmanage_get(client, base_url, "/dataservice/device")

    for d in devices:
        if (
            d.get("system-ip") == name_or_ip
            or d.get("host-name") == name_or_ip
        ):
            return d["system-ip"]

    raise ValueError(f"Device not found: {name_or_ip}")

async def vmanage_get_raw(client, base_url: str, path: str) -> str:
    url = f"{base_url}{path}"
    resp = await client.get(url)
    resp.raise_for_status()
    return resp.text

async def resolve_feature_template_id(client: httpx.AsyncClient, base_url: str, name_or_id: str) -> str:
    """
    Resolve feature template name OR ID → templateId
    """

    templates = await vmanage_get(
        client,
        base_url,
        "/dataservice/template/feature"
    )

    for t in templates:
        if (
            t.get("templateId") == name_or_id
            or t.get("templateName") == name_or_id
        ):
            return t["templateId"]

    raise ValueError(f"Feature template not found: {name_or_id}")

async def resolve_device_template_id(client: httpx.AsyncClient, base_url: str, name_or_id: str) -> str:
    """
    Resolve device template name OR ID → templateId
    """

    templates = await vmanage_get(
        client,
        base_url,
        "/dataservice/template/device"
    )

    for t in templates:
        if (
            t.get("templateId") == name_or_id
            or t.get("templateName") == name_or_id
        ):
            return t["templateId"]

    raise ValueError(f"Device template not found: {name_or_id}")

# ---------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------
@mcp.tool()
async def get_inventory(fqdn: str | None = None) -> Dict[str, Any]:
    """Fetch full SD-WAN device inventory."""

    fqdn = fqdn or DEFAULT_FQDN
    logger.info(f"Tool called: get_inventory with {fqdn}")
    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)
    client = await vmanage_login(base_url, VMANAGE_USERNAME, VMANAGE_PASSWORD)

    try:
        devices = await vmanage_get(client, base_url, "/dataservice/device")
        return {"inventory": devices}
    finally:
        await client.aclose()

@mcp.tool()
async def get_wan_edge_devices(fqdn: str | None = None) -> Dict[str, Any]:
    """Retrieve WAN Edge (vEdge / cEdge) inventory."""
    fqdn = fqdn or DEFAULT_FQDN
    logger.info(f"Tool called: get_wan_edge_devices with {fqdn}")
    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)
    client = await vmanage_login(base_url, VMANAGE_USERNAME, VMANAGE_PASSWORD)

    try:
        vedges = await vmanage_get(
            client,
            base_url,
            "/dataservice/system/device/vedges"
        )
        return {"wan_edges": vedges}
    finally:
        await client.aclose()

@mcp.tool()
async def get_control_plane_status(
    device: str,
    fqdn: str | None = None
) -> Dict[str, Any]:
    """Fetch control plane connection status for a device."""
    fqdn = fqdn or DEFAULT_FQDN
    logger.info(f"Tool called: get_control_plane_status with {fqdn}")
    if not fqdn:
        raise ValueError("fqdn must be provided")
    if not device:
        raise ValueError("device is required")

    base_url = fix_url(fqdn)
    client = await vmanage_login(base_url, VMANAGE_USERNAME, VMANAGE_PASSWORD)
    device_id = await resolve_device_id(client, base_url, device)
    try:
        status = await vmanage_get(
            client,
            base_url,
            f"/dataservice/device/control/connections?deviceId={device_id}"
        )
        return {"control_plane_status": status}
    finally:
        await client.aclose()


@mcp.tool()
async def get_device_interfaces(
    device: str,
    fqdn: str | None = None,
) -> Dict[str, Any]:
    """Retrieve interface details for a device (hostname or system-ip)."""

    fqdn = fqdn or DEFAULT_FQDN
    logger.info(f"Tool called: get_device_interfaces with {fqdn}")
    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)
    client = await vmanage_login(base_url, VMANAGE_USERNAME, VMANAGE_PASSWORD)

    try:
        device_id = await resolve_device_id(client, base_url, device)

        interfaces = await vmanage_get(
            client,
            base_url,
            f"/dataservice/device/interface?deviceId={device_id}"
        )
        return {
            "device": device,
            "device_id": device_id,
            "interfaces": interfaces,
        }
    finally:
        await client.aclose()


@mcp.tool()
async def get_device_template_attachments(fqdn: str | None = None) -> Dict[str, Any]:
    """Returns device-to-template attachment mapping (uses /dataservice/device)."""

    fqdn = fqdn or DEFAULT_FQDN
    logger.info(f"Tool called: get_device_template_attachments with {fqdn}")
    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)
    client = await vmanage_login(base_url, VMANAGE_USERNAME, VMANAGE_PASSWORD)

    try:
        devices = await vmanage_get(client, base_url, "/dataservice/device")

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
async def get_transport_health_summary(device: str, fqdn: str | None = None) -> Dict[str, Any]:
    """Transport health using version-safe BFD API."""

    fqdn = fqdn or DEFAULT_FQDN
    logger.info(f"Tool called: get_transport_health_summary with {fqdn}")
    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)
    client = await vmanage_login(base_url, VMANAGE_USERNAME, VMANAGE_PASSWORD)

    try:
        device_id = await resolve_device_id(client, base_url, device)

        device_bfd = await vmanage_get(client, base_url, f"/dataservice/device/bfd/sessions?deviceId={device_id}")

        down = [s for s in device_bfd if s.get("state") != "up"]

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
async def get_health_status(fqdn: str | None = None) -> Dict[str, Any]:
    """Fetch health status for all SD-WAN devices."""
    fqdn = fqdn or DEFAULT_FQDN
    logger.info(f"Tool called: get_health_status with {fqdn}")
    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)
    client = await vmanage_login(base_url, VMANAGE_USERNAME, VMANAGE_PASSWORD)

    try:
        health = await vmanage_get(client, base_url, "/dataservice/device/monitor")
        return {"health": health}
    finally:
        await client.aclose()


@mcp.tool()
async def get_alarms(fqdn: str | None = None) -> Dict[str, Any]:
    """Fetch all active SD-WAN alarms."""
    fqdn = fqdn or DEFAULT_FQDN
    logger.info(f"Tool called: get_alarms with {fqdn}")
    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)
    client = await vmanage_login(base_url, VMANAGE_USERNAME, VMANAGE_PASSWORD)

    try:
        alarms = await vmanage_get(client, base_url, "/dataservice/alarms")
        return {"alarms": alarms}
    finally:
        await client.aclose()

@mcp.tool()
async def get_events(limit: int = 20, fqdn: str | None = None) -> Dict[str, Any]:
    """Retrieves recent events/logs. Use limit to control output size (default 20)."""
    fqdn = fqdn or DEFAULT_FQDN
    logger.info(f"Tool called: get_events with {fqdn}")
    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)
    client = await vmanage_login(base_url, VMANAGE_USERNAME, VMANAGE_PASSWORD)

    try:
        events = await vmanage_get(client, base_url, "/dataservice/event")
        return {"events": events}
    finally:
        await client.aclose()

@mcp.tool()
async def get_device_tunnels(device: str, fqdn: str | None = None) -> Dict[str, Any]:
    """Retrieve SD-WAN tunnels using device-specific, RBAC-safe endpoints."""

    fqdn = fqdn or DEFAULT_FQDN
    logger.info(f"Tool called: get_device_tunnels with {fqdn}")
    base_url = fix_url(fqdn)
    client = await vmanage_login(base_url, VMANAGE_USERNAME, VMANAGE_PASSWORD)

    try:
        # device_id must be the System-IP
        device_id = await resolve_device_id(client, base_url, device)

        # Use deviceId parameter to avoid 403 Forbidden (data plane: BFD/IPsec)
        device_bfd = await vmanage_get(
            client,
            base_url,
            f"/dataservice/device/bfd/sessions?deviceId={device_id}"
        )

        # Control-plane tunnels (DTLS / TLS)
        control_connections = await vmanage_get(
            client,
            base_url,
            f"/dataservice/device/control/connections?deviceId={device_id}"
        )

        return {
            "device": device,
            "device_id": device_id,
            "tunnels": {
                "data_plane": {
                    "type": "IPsec / BFD",
                    "total": len(device_bfd),
                    "down": [s for s in device_bfd if s.get("state") != "up"],
                    "sessions": device_bfd,
                },
                "control_plane": {
                    "type": "DTLS / TLS",
                    "total": len(control_connections),
                    "down": [c for c in control_connections if c.get("state") != "up"],
                    "connections": control_connections,
                },
            },
        }
    finally:
        await client.aclose()


@mcp.tool()
async def get_down_devices(fqdn: str | None = None) -> Dict[str, Any]:
    """List devices that are not in normal health state."""
    fqdn = fqdn or DEFAULT_FQDN
    logger.info(f"Tool called: get_down_devices with {fqdn}")
    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)
    client = await vmanage_login(base_url, VMANAGE_USERNAME, VMANAGE_PASSWORD)

    try:
        health = await vmanage_get(client, base_url, "/dataservice/device/monitor")
        down = [d for d in health if d.get("status") != "normal"]
        return {"down_devices": down}
    finally:
        await client.aclose()

@mcp.tool()
async def get_feature_templates(fqdn: str | None = None) -> str:
    """Lists all Feature Templates."""
    fqdn = fqdn or DEFAULT_FQDN
    logger.info(f"Tool called: get_feature_templates with {fqdn}")
    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)
    client = await vmanage_login(base_url, VMANAGE_USERNAME, VMANAGE_PASSWORD)

    try:
        data = await vmanage_get(client, base_url, "/dataservice/template/feature")
        if isinstance(data, dict) and 'data' in data:
            simplified = [
                {k: v for k, v in item.items() if k in ['templateId', 'templateName', 'deviceType', 'templateType']}
                for item in data['data']
            ]
            return json.dumps(simplified, indent=2)
        return json.dumps(data, indent=2)
    finally:
        await client.aclose()

@mcp.tool()
async def get_device_templates(fqdn: str | None = None) -> str:
    """Lists all Device Templates defined in vManage."""
    fqdn = fqdn or DEFAULT_FQDN
    logger.info(f"Tool called: get_device_templates with {fqdn}")
    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)
    client = await vmanage_login(base_url, VMANAGE_USERNAME, VMANAGE_PASSWORD)

    try:
        data = await vmanage_get(client, base_url, "/dataservice/template/device")
        if isinstance(data, dict) and 'data' in data:
            simplified = [
                {k: v for k, v in item.items() if k in ['templateId', 'templateName', 'deviceType', 'devicesAttached']}
                for item in data['data']
            ]
            return json.dumps(simplified, indent=2)
        return json.dumps(data, indent=2)
    finally:
        await client.aclose()

@mcp.tool()
async def get_feature_template_details(template: str, fqdn: str | None = None) -> Dict[str, Any]:
    """Retrieves the full definition of a Feature Template, including variable names."""
    fqdn = fqdn or DEFAULT_FQDN
    logger.info(f"Tool called: get_feature_template_details with {fqdn}")
    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)
    client = await vmanage_login(base_url, VMANAGE_USERNAME, VMANAGE_PASSWORD)

    try:
        template_id = await resolve_feature_template_id(client, base_url, template)
        template_details = await vmanage_get(client, base_url, f"/dataservice/template/feature/object/{template_id}")
        return {"template_details": template_details}
    finally:
        await client.aclose()

@mcp.tool()
async def get_device_template_details(template: str, fqdn: str | None = None) -> Dict[str, Any]:
    """Retrieves the full configuration object for a specific Device Template."""
    fqdn = fqdn or DEFAULT_FQDN
    logger.info(f"Tool called: get_device_template_details with {fqdn}")
    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)
    client = await vmanage_login(base_url, VMANAGE_USERNAME, VMANAGE_PASSWORD)

    try:
        template_id = await resolve_device_template_id(client, base_url, template)
        template_details = await vmanage_get(client, base_url, f"/dataservice/template/device/object/{template_id}")
        return {"template_details": template_details}
    finally:
        await client.aclose()

@mcp.tool()
async def get_centralized_policies(fqdn: str | None = None) -> Dict[str, Any]:
    """Lists Centralized Policy definitions (vSmart policies)."""
    fqdn = fqdn or DEFAULT_FQDN
    logger.info(f"Tool called: get_centralized_policies with {fqdn}")
    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)
    client = await vmanage_login(base_url, VMANAGE_USERNAME, VMANAGE_PASSWORD)

    try:
        policies = await vmanage_get(client, base_url, "/dataservice/template/policy/vsmart")
        return {"policies": policies}
    finally:
        await client.aclose()

@mcp.tool()
async def get_control_connections(device: str, fqdn: str | None = None) -> Dict[str, Any]:
    """Retrieves control connections (DTLS/TLS) for a device."""
    fqdn = fqdn or DEFAULT_FQDN
    logger.info(f"Tool called: get_control_connections with {fqdn}")
    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)
    client = await vmanage_login(base_url, VMANAGE_USERNAME, VMANAGE_PASSWORD)
    device_id = await resolve_device_id(client, base_url, device)
    try:
        connections = await vmanage_get(client, base_url, f"/dataservice/device/control/connections?deviceId={device_id}")
        return {"connections": connections}
    finally:
        await client.aclose()

@mcp.tool()
async def get_running_config(device: str, fqdn: str | None = None) -> str:
    """Retrieves the full running configuration of a device."""

    fqdn = fqdn or DEFAULT_FQDN
    logger.info(f"Tool called: get_running_config with {fqdn}")
    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)
    client = await vmanage_login(base_url, VMANAGE_USERNAME, VMANAGE_PASSWORD)

    try:
        device_id = await resolve_device_id(client, base_url, device)

        config = await vmanage_get_raw(
            client,
            base_url,
            f"/dataservice/device/config?deviceId={device_id}"
        )

        return config
    finally:
        await client.aclose()


@mcp.tool()
async def generate_audit_report(fqdn: str | None = None) -> Dict[str, Any]:
    """Generate a simple SD-WAN audit summary."""
    fqdn = fqdn or DEFAULT_FQDN
    logger.info(f"Tool called: generate_audit_report with {fqdn}")
    if not fqdn:
        raise ValueError("fqdn must be provided")

    base_url = fix_url(fqdn)
    client = await vmanage_login(base_url, VMANAGE_USERNAME, VMANAGE_PASSWORD)

    try:
        devices = await vmanage_get(client, base_url, "/dataservice/device")
        health = await vmanage_get(client, base_url, "/dataservice/device/monitor")
        alarms = await vmanage_get(client, base_url, "/dataservice/alarms")

        return {
            "audit_report": {
                "total_devices": len(devices),
                "down_devices": len([d for d in health if d.get("status") != "normal"]),
                "alarm_count": len(alarms),
            }
        }
    finally:
        await client.aclose()


# ---------------------------------------------------------------------
# Server Entrypoint
# ---------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SD-WAN MCP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address")
    parser.add_argument("--port", type=int, default=7004, help="Bind port")
    args = parser.parse_args()

    logger.info("Starting SD-WAN MCP server on %s:%s", args.host, args.port)

    mcp.run(
        transport="streamable-http",
        host=args.host,
        port=args.port,
    )
