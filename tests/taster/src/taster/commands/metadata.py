#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Display package metadata including build info."""

from __future__ import annotations

from collections.abc import Mapping
import json
import os
from pathlib import Path
from typing import Any

import click
from provide.foundation.console import pout


@click.command("metadata")
@click.option("--verbose", "-v", is_flag=True, help="Show raw JSON metadata")
def metadata_command(verbose: bool) -> None:
    """Display package metadata including build info."""
    pout("=" * 60, color="cyan")
    pout("📋 PACKAGE METADATA", color="cyan", bold=True)
    pout("=" * 60, color="cyan")

    workenv_path = _resolve_workenv()
    metadata = _load_metadata(workenv_path)

    _print_package_info(metadata)
    _print_build_info(metadata)
    _print_slot_info(metadata)
    _print_execution_info(metadata)
    _print_verification_info(metadata)

    if verbose:
        pout("\nRAW METADATA:", color="magenta")
        pout(json.dumps(metadata, indent=2))


def _resolve_workenv() -> Path:
    """Return the path to the active workenv or raise if missing."""
    workenv = os.environ.get("FLAVOR_WORKENV")
    if not workenv:
        raise click.ClickException("FLAVOR_WORKENV not set - not running in a flavor pack.")
    return Path(workenv)


def _load_metadata(workenv_path: Path) -> dict[str, Any]:
    """Load metadata JSON from known locations, falling back to mock data."""
    search_paths = [
        workenv_path / "metadata" / "psp.json",
        workenv_path / "psp.json",
        workenv_path / ".psp" / "psp.json",
    ]

    for path in search_paths:
        if not path.exists():
            continue
        try:
            with path.open(encoding="utf-8") as handle:
                return json.load(handle)
        except Exception as exc:
            pout(f"⚠️ Failed to load {path}: {exc}", color="yellow")

    pout("⚠️ Using mock metadata for demonstration", color="yellow")
    return {
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


def _print_package_info(metadata: Mapping[str, Any]) -> None:
    """Print high-level package information."""
    package = metadata.get("package")
    if not package:
        return
    pout(f"  Name: {package.get('name', 'unknown')}")
    pout(f"  Version: {package.get('version', 'unknown')}")
    description = package.get("description")
    if description:
        pout(f"  Description: {description}")


def _print_build_info(metadata: Mapping[str, Any]) -> None:
    """Print build-specific information."""
    build = metadata.get("build")
    if not build:
        return
    pout("\n🔨 Build Information:", color="yellow")
    pout(f"  Builder: {build.get('builder', 'unknown')}")
    pout(f"  Timestamp: {build.get('timestamp', 'unknown')}")
    pout(f"  Host: {build.get('host', 'unknown')}")


def _print_slot_info(metadata: Mapping[str, Any]) -> None:
    """Print slot details."""
    slots = metadata.get("slots")
    if not slots:
        return
    pout("\n📦 Slots:", color="yellow")
    for slot in slots:
        index = slot.get("index", "?")
        name = slot.get("name", "unknown")
        purpose = slot.get("purpose", "unknown")
        pout(f"  [{index}] {name} ({purpose})")


def _print_execution_info(metadata: Mapping[str, Any]) -> None:
    """Print execution metadata."""
    execution = metadata.get("execution")
    if not execution:
        return
    pout("\n🚀 Execution:", color="magenta")
    pout(f"  Command: {execution.get('command', 'unknown')}")
    pout(f"  Primary Slot: {execution.get('primary_slot', 0)}")
    env = execution.get("environment") or {}
    pout(f"  Environment: {len(env)} variables")


def _print_verification_info(metadata: Mapping[str, Any]) -> None:
    """Print verification metadata if available."""
    verification = metadata.get("verification")
    if not verification:
        return
    pout("\n🔐 Verification:", color="cyan")
    seal = verification.get("integrity_seal", {})
    pout(f"  Algorithm: {seal.get('algorithm', 'unknown')}")
    pout(f"  Required: {seal.get('required', False)}")


# 🌶️📦🔚
