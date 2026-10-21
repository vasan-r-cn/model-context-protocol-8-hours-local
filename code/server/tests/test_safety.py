"""The blast-radius rule, asserted rather than inspected.

Promise of the workshop lab: a tool call cannot change a production device.
These tests fail loudly if that stops being true — including the case that
matters most, a call that simply omits the `device` argument.
"""

from __future__ import annotations

import pytest

from app import inventory as inv
from app import main as server_main

pytestmark = pytest.mark.anyio

CONFIG_TOOLS = ("configure_interface", "create_loopback")

PRODUCTION = inv.names_with_role("production")
READ_ONLY_ROLES = inv.names_with_role("production", "branch", "legacy")


def _text(result) -> str:
    return "\n".join(c.text for c in result.content if c.type == "text")


def _args(tool: str, device: str | None) -> dict:
    args: dict[str, object] = {"loopback_id": 901}
    if tool == "configure_interface":
        args = {"interface": "Loopback901", "ip_address": "10.90.1.1"}
    if device is not None:
        args["device"] = device
    return args


class TestInventoryContract:
    def test_default_device_is_production_representative(self):
        assert inv.DEVICES[inv.DEFAULT_DEVICE].role == "prod-rep"

    def test_production_is_never_writable(self):
        assert "production" not in inv.WRITABLE_ROLES
        for name in PRODUCTION:
            allowed, reason = inv.may_write_to(name)
            assert not allowed
            assert "production-representative" in reason

    def test_only_prod_rep_devices_are_writable(self):
        assert set(inv.writable_names()) == set(inv.names_with_role("prod-rep"))

    def test_promotion_targets_production_only(self):
        for name in inv.names_with_role("prod-rep", "branch", "legacy"):
            assert not inv.may_promote_to(name)[0]


class TestConfigToolsRefuse:
    @pytest.mark.parametrize("tool", CONFIG_TOOLS)
    @pytest.mark.parametrize("device", READ_ONLY_ROLES)
    async def test_refuses_non_writable_device_and_sends_nothing(
        self, session, no_ssh, tool, device
    ):
        result = await session.call_tool(tool, _args(tool, device))
        assert "Refusing to configure" in _text(result)
        assert no_ssh == [], f"{tool} reached {device}: {no_ssh}"

    @pytest.mark.parametrize("tool", CONFIG_TOOLS)
    async def test_omitted_device_never_reaches_production(self, session, no_ssh, tool):
        await session.call_tool(tool, _args(tool, None))
        touched = {device for _, device, _ in no_ssh}
        assert not touched & set(PRODUCTION), f"{tool} touched production: {touched}"

    @pytest.mark.parametrize("tool", CONFIG_TOOLS)
    async def test_unknown_device_is_rejected(self, session, no_ssh, tool):
        # "router1" is the old lab's device name — a stale guide or a model
        # working from memory will try it.
        result = await session.call_tool(tool, _args(tool, "router1"))
        assert no_ssh == []
        assert result.isError or "router1" in _text(result)


class TestReadOnlyToolsAreAnnotated:
    async def test_read_only_tools_carry_read_only_hint(self, session):
        tools = {t.name: t for t in (await session.list_tools()).tools}
        for name in ("get_interfaces", "get_router_info", "dynamic_show",
                     "snapshot_config", "list_devices"):
            assert tools[name].annotations.readOnlyHint is True, name

    async def test_config_tools_are_marked_destructive(self, session):
        tools = {t.name: t for t in (await session.list_tools()).tools}
        for name in CONFIG_TOOLS:
            assert tools[name].annotations.destructiveHint is True, name
            assert tools[name].annotations.readOnlyHint is False, name


class TestDeviceArgumentIsAContract:
    async def test_device_parameter_is_an_enum_of_real_devices(self, session):
        tools = {t.name: t for t in (await session.list_tools()).tools}
        for name in ("get_interfaces", "dynamic_show", *CONFIG_TOOLS):
            schema = tools[name].inputSchema
            device = schema["properties"]["device"]
            enum = device.get("enum") or schema["$defs"][
                device["allOf"][0]["$ref"].split("/")[-1]
            ]["enum"]
            assert set(enum) == set(inv.DEVICE_NAMES), name

    async def test_device_defaults_to_the_safe_device(self, session):
        tools = {t.name: t for t in (await session.list_tools()).tools}
        for name in ("get_interfaces", *CONFIG_TOOLS):
            assert tools[name].inputSchema["properties"]["device"]["default"] == (
                inv.DEFAULT_DEVICE
            ), name


class TestAllowlistStillHolds:
    """The 4h lesson that must not regress: dynamic_show is exact-match."""

    @pytest.mark.parametrize(
        "command",
        [
            "show running-config",
            "show ip route | include 10.",
            "show ip interface brief ; show version",
            "show run | redirect tftp://10.0.0.1/x",
        ],
    )
    async def test_rejects_commands_outside_the_allowlist(self, session, no_ssh, command):
        result = await session.call_tool("dynamic_show", {"command": command})
        assert "Command rejected" in _text(result)
        assert no_ssh == []

    async def test_accepts_an_allowlisted_command_case_and_space_insensitively(
        self, session, no_ssh
    ):
        await session.call_tool("dynamic_show", {"command": "SHOW   IP   ROUTE"})
        assert [c[0] for c in no_ssh] == ["show"]
