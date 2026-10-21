"""Lab device inventory and the write-safety rules built on top of it.

Loaded from inventory.yaml at import. Three things live here and nowhere else:

1. What devices exist, how to reach them, and what Netmiko/pyATS call them.
2. Which devices may be written to (`role`), which is what keeps a careless
   tool call off production.
3. Credential resolution, so no credential is ever written in a lab guide.

The blast-radius rule, stated once: `writable_roles()` is the only answer to
"may I configure this device", every config path asks it, and production is
not in it. Promotion to production goes through change_workflow, which asks
`may_promote_to()` instead.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

INVENTORY_PATH = Path(
    os.environ.get("MCP_INVENTORY", Path(__file__).resolve().parent.parent / "inventory.yaml")
)

Role = Literal["production", "prod-rep", "branch", "legacy", "controller"]

#: Roles a normal config tool may write to. Production is deliberately absent.
WRITABLE_ROLES: frozenset[str] = frozenset({"prod-rep"})

#: Roles promote_change may write to, after a validation on a prod-rep device.
PROMOTABLE_ROLES: frozenset[str] = frozenset({"production"})


class InventoryError(RuntimeError):
    """Raised at startup only. Never raised on a tool call path."""


@dataclass(frozen=True)
class Device:
    name: str
    host: str | None
    device_type: str          # Netmiko platform, e.g. cisco_nxos / cisco_xe
    os: str                   # pyATS os, e.g. nxos / iosxe
    role: str
    site: str
    username: str
    password: str
    secret: str
    notes: str = ""

    @property
    def reachable(self) -> bool:
        """False when no management address has been configured yet."""
        return bool(self.host)

    @property
    def writable(self) -> bool:
        return self.role in WRITABLE_ROLES

    def netmiko_args(self) -> dict[str, str]:
        """Connection kwargs for Netmiko.

        Credentials are per device, because the platforms genuinely differ
        (NX-OS and the SD-WAN edges do not share a password). Per-device env
        vars win, then a global override, then the inventory value.
        """
        return {
            "device_type": self.device_type,
            "host": self.host or "",
            "username": _device_env(self.name, "USER") or os.environ.get("DEVICE_USER") or self.username,
            "password": _device_env(self.name, "PASSWORD") or os.environ.get("DEVICE_PASSWORD") or self.password,
            "secret": _device_env(self.name, "SECRET") or os.environ.get("DEVICE_SECRET") or self.secret,
        }


def _device_env(name: str, field: str) -> str | None:
    """MCP_DEV_<NAME>_<FIELD> — per-device override, so a seat can re-point or
    re-credential one device without editing a shared file."""
    key = "MCP_DEV_" + re.sub(r"[^A-Za-z0-9]", "_", name).upper() + "_" + field
    return os.environ.get(key)


def _env_host_override(name: str) -> str | None:
    return _device_env(name, "HOST")


def _load() -> tuple[dict[str, Device], str]:
    if not INVENTORY_PATH.is_file():
        raise InventoryError(f"inventory file not found: {INVENTORY_PATH}")
    raw = yaml.safe_load(INVENTORY_PATH.read_text()) or {}

    entries = raw.get("devices") or {}
    if not entries:
        raise InventoryError(f"{INVENTORY_PATH} lists no devices")

    devices: dict[str, Device] = {}
    for name, spec in entries.items():
        try:
            devices[name] = Device(
                name=name,
                host=_env_host_override(name) or spec.get("host"),
                device_type=spec["device_type"],
                os=spec["os"],
                role=spec["role"],
                site=spec.get("site", "unknown"),
                username=spec.get("username", "admin"),
                password=spec.get("password", "admin"),
                secret=spec.get("secret", spec.get("password", "admin")),
                notes=spec.get("notes", ""),
            )
        except KeyError as exc:
            raise InventoryError(f"device {name!r} is missing required key {exc}") from exc

    default = raw.get("default_device")
    if default not in devices:
        raise InventoryError(f"default_device {default!r} is not a device in the inventory")
    if devices[default].role not in WRITABLE_ROLES:
        # The whole point of the default is that an omitted argument is safe.
        raise InventoryError(
            f"default_device {default!r} has role {devices[default].role!r}; "
            f"it must be one of {sorted(WRITABLE_ROLES)} so that a tool call "
            f"with no device argument cannot reach production"
        )
    return devices, default


DEVICES, DEFAULT_DEVICE = _load()
DEVICE_NAMES: tuple[str, ...] = tuple(DEVICES)


def get(name: str) -> Device:
    """Look up a device. Raises KeyError; callers turn that into a tool result."""
    return DEVICES[name]


def names_with_role(*roles: str) -> tuple[str, ...]:
    return tuple(n for n, d in DEVICES.items() if d.role in roles)


def writable_names() -> tuple[str, ...]:
    return names_with_role(*WRITABLE_ROLES)


def may_write_to(name: str) -> tuple[bool, str]:
    """(allowed, reason). `reason` is written to be read by a model."""
    try:
        device = DEVICES[name]
    except KeyError:
        return False, (
            f"Unknown device {name!r}. Known devices: {', '.join(DEVICE_NAMES)}."
        )
    # Role is policy, so it is checked first: a production device is refused
    # for the right reason whether or not it has a management address yet.
    if not device.writable:
        return False, (
            f"Refusing to configure {name!r}: it is a {device.role} device in "
            f"{device.site}. Configuration changes are only applied to "
            f"production-representative devices ({', '.join(writable_names())}). "
            f"To change production, validate the change on a "
            f"production-representative device first, then promote it."
        )
    if not device.reachable:
        return False, (
            f"Device {name!r} has no management address configured in "
            f"{INVENTORY_PATH.name}; it cannot be reached."
        )
    return True, ""


def may_promote_to(name: str) -> tuple[bool, str]:
    """Used only by the change-promotion path, never by an ordinary tool."""
    try:
        device = DEVICES[name]
    except KeyError:
        return False, f"Unknown device {name!r}."
    if device.role not in PROMOTABLE_ROLES:
        return False, (
            f"{name!r} is a {device.role} device; promotion targets production "
            f"devices ({', '.join(names_with_role(*PROMOTABLE_ROLES))})."
        )
    if not device.reachable:
        return False, f"Device {name!r} has no management address configured."
    return True, ""


def describe() -> str:
    """Human/model-readable inventory summary, used by the inventory tool."""
    lines = []
    for site in dict.fromkeys(d.site for d in DEVICES.values()):
        lines.append(f"{site}:")
        for d in DEVICES.values():
            if d.site != site:
                continue
            flags = []
            if not d.reachable:
                flags.append("NO MANAGEMENT ADDRESS")
            if d.writable:
                flags.append("writable")
            suffix = f"  [{', '.join(flags)}]" if flags else ""
            lines.append(f"  {d.name:<18} {d.role:<11} {d.os:<6}{suffix}")
    return "\n".join(lines)
