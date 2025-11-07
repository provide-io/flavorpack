#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Display package metadata including build info"""

import json
import os
from pathlib import Path

import click
from provide.foundation.console import pout


@click.command("metadata")
def metadata_command() -> None:
    """📋 Display package metadata including build info"""
    pout("=" * 60, color="cyan")
    pout("📋 PACKAGE METADATA", color="cyan", bold=True)
    pout("=" * 60, color="cyan")

    # Try to load metadata from workenv
    workenv = os.environ.get("FLAVOR_WORKENV")
    if not workenv:
        pout("❌ FLAVOR_WORKENV not set - not running in flavor pack", color="red")
        return

    workenv_path = Path(workenv)

    # Look for psp.json in various locations
    possible_paths = [
        workenv_path / "metadata" / "psp.json",
        workenv_path / "psp.json",
        workenv_path / ".psp" / "psp.json",
    ]

    metadata = None
    for path in possible_paths:
        if path.exists():
            try:
                with open(path) as f:
                    metadata = json.load(f)
                break
            except Exception as e:
                pout(f"⚠️ Failed to load {path}: {e}", color="yellow")

    if not metadata:
        # Create mock metadata for testing
        metadata = {
            "format": "PSPF/2025",
            "package": {
                "name": "taster",
                "version": "1.0.0",
                "description": "Test package for flavor functionality",
            },
            "build": {
                "builder": "flavor/python-builder",
                "timestamp": "2025-01-01T00:00:00Z",
                "host": "test-host",
            },
            "execution": {
                "primary_slot": 0,
                "command": "python -m taster.cli",
                "environment": {},
            },
            "slots": [
                {"index": 0, "name": "payload", "purpose": "payload"},
                {"index": 1, "name": "runtime", "purpose": "runtime"},
                {"index": 2, "name": "tools", "purpose": "tool"},
            ],
        }
        pout("⚠️ Using mock metadata for demonstration", color="yellow")

    # Display metadata sections
    if "package" in metadata:
        pkg = metadata["package"]
        pout(f"  Name: {pkg.get('name', 'unknown')}")
        pout(f"  Version: {pkg.get('version', 'unknown')}")
        if "description" in pkg:
            pout(f"  Description: {pkg['description']}")

    if "build" in metadata:
        pout("\n🔨 Build Information:", color="yellow")
        build = metadata["build"]
        pout(f"  Builder: {build.get('builder', 'unknown')}")
        pout(f"  Timestamp: {build.get('timestamp', 'unknown')}")
        pout(f"  Host: {build.get('host', 'unknown')}")

    if "slots" in metadata:
        for slot in metadata["slots"]:
            pout(f"  [{slot['index']}] {slot['name']} ({slot.get('purpose', 'unknown')})")

    if "execution" in metadata:
        exec_info = metadata["execution"]
        pout(f"  Command: {exec_info.get('command', 'unknown')}")
        pout(f"  Primary Slot: {exec_info.get('primary_slot', 0)}")
        if exec_info.get("environment"):
            pout(f"  Environment: {len(exec_info['environment'])} variables")

    if "verification" in metadata:
        pout("\n🔐 Verification:", color="cyan")
        verify = metadata["verification"]
        if "integrity_seal" in verify:
            seal = verify["integrity_seal"]
            pout(f"  Algorithm: {seal.get('algorithm', 'unknown')}")
            pout(f"  Required: {seal.get('required', False)}")

    # Show raw JSON if verbose
    if click.get_current_context().params.get("verbose"):
        pout(json.dumps(metadata, indent=2))


# 🌶️📦🔚
