"""Test fixtures: an MCP client session wired to the server in memory.

No router, no network, no uvicorn. The SDK connects a client and server
over an in-memory transport, so these tests exercise the real protocol
surface — tool schemas, annotations, and tool results — at unit-test speed.
That is what makes a CI gate possible for a server whose devices live in a lab.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SERVER_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVER_ROOT))

from mcp.shared.memory import create_connected_server_and_client_session  # noqa: E402

from app import main as server_main  # noqa: E402


@pytest.fixture
def anyio_backend():
    """Run the async tests on asyncio only (the server's own runtime)."""
    return "asyncio"


@pytest.fixture
async def session():
    """A connected MCP client session. Declares no client capabilities —
    the same posture as a client without elicitation support."""
    async with create_connected_server_and_client_session(
        server_main.mcp._mcp_server
    ) as client:
        yield client


@pytest.fixture
def no_ssh(monkeypatch):
    """Replace the SSH layer. Records what *would* have been sent to a device.

    If a test finds a call recorded here for a production device, the
    blast-radius rule has been broken.
    """
    calls: list[tuple[str, str, object]] = []

    async def fake_show(command: str, device: str = server_main.DEFAULT_DEVICE) -> str:
        calls.append(("show", device, command))
        return f"<fake output of {command!r} from {device}>"

    async def fake_config(commands, device: str = server_main.DEFAULT_DEVICE) -> str:
        calls.append(("config", device, list(commands)))
        return "<fake config applied>"

    monkeypatch.setattr(server_main, "run_show", fake_show)
    monkeypatch.setattr(server_main, "run_config", fake_config)
    return calls
