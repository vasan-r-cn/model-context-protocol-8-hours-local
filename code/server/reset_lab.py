"""Lab reset: remove workshop-created loopbacks from Router1.

Deletes every Loopback interface whose description is MCP_CREATED (the
marker create_loopback sets). Run between cohorts, after reviewing the
planned changes it prints. Interface IP changes made via configure_interface
must be restored manually from the latest snapshot (see snapshots/).

Usage: python3 reset_lab.py [--apply]
Without --apply it only prints what would be removed.
"""

import os
import re
import sys

from netmiko import ConnectHandler

ROUTER_CONFIG = {
    "device_type": "cisco_ios",
    "host": os.environ.get("ROUTER_HOST", "172.18.2.6"),
    "username": os.environ.get("ROUTER_USER", "admin"),
    "password": os.environ.get("ROUTER_PASSWORD", "admin"),
    "secret": os.environ.get("ROUTER_SECRET", "admin"),
}


def find_workshop_loopbacks(running_config: str) -> list[str]:
    loopbacks = []
    current = None
    for line in running_config.splitlines():
        match = re.match(r"^interface (Loopback\d+)$", line.strip())
        if match:
            current = match.group(1)
        elif current and line.strip() == "description MCP_CREATED":
            loopbacks.append(current)
        elif not line.startswith(" "):
            current = None
    return loopbacks


def main() -> int:
    apply_changes = "--apply" in sys.argv
    connection = ConnectHandler(**ROUTER_CONFIG)
    try:
        connection.enable()
        running_config = connection.send_command("show running-config")
        loopbacks = find_workshop_loopbacks(running_config)
        if not loopbacks:
            print("No MCP_CREATED loopbacks found — router is clean.")
            return 0
        print("Workshop loopbacks found:", ", ".join(loopbacks))
        if not apply_changes:
            print("Dry run only. Re-run with --apply to remove them.")
            return 0
        commands = [f"no interface {name}" for name in loopbacks]
        output = connection.send_config_set(commands)
        print(output)
        connection.save_config()
        print(f"Removed {len(loopbacks)} loopback(s) and saved config.")
        return 0
    finally:
        connection.disconnect()


if __name__ == "__main__":
    sys.exit(main())
