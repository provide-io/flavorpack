#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Verify command for the flavor CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
from provide.foundation.console import perr, pout

from flavor.console import get_command_logger
from flavor.package import verify_package

# Get structured logger for this command
log = get_command_logger("verify")


@click.command("verify")
@click.argument(
    "package_file",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    required=True,
)
def verify_command(package_file: str) -> None:
    """Verifies a flavor package."""
    final_package_file = Path(package_file)
    log.debug("Starting package verification", package=str(final_package_file))
    pout(f"🔍 Verifying package '{final_package_file}'...")

    try:
        result = verify_package(final_package_file)
        log.debug(
            "Package verification completed",
            format=result.get("format"),
            signature_valid=result.get("signature_valid"),
        )

        _display_basic_info(result)
        if result["format"] == "PSPF/2025":
            _display_pspf_info(result)
        _display_signature_status(result)

    except Exception as e:
        log.error("Verification failed", error=str(e), package=str(final_package_file))
        perr(f"❌ Verification failed: {e}")
        raise click.Abort() from e


def _display_basic_info(result: dict[str, Any]) -> None:
    """Display basic package information."""
    pout(f"\nPackage Format: {result['format']}")
    pout(f"Version: {result['version']}")
    pout(f"Launcher Size: {result['launcher_size'] / (1024 * 1024):.1f} MB")


def _display_pspf_info(result: dict[str, Any]) -> None:
    """Display PSPF-specific package information."""
    pout(f"Slot Count: {result['slot_count']}")

    _display_package_metadata(result)
    _display_build_metadata(result)
    _display_slot_information(result)


def _display_package_metadata(result: dict[str, Any]) -> None:
    """Display package metadata."""
    if "package" in result:
        pkg = result["package"]
        pout(f"Package: {pkg.get('name', 'unknown')} v{pkg.get('version', 'unknown')}")


def _display_build_metadata(result: dict[str, Any]) -> None:
    """Display build metadata."""
    if result.get("build"):
        build = result["build"]
        if "timestamp" in build:
            pout(f"Built: {build['timestamp']}")
        if "builder_version" in build:
            pout(f"Builder: {build['builder_version']}")
        if "launcher_type" in build:
            pout(f"Launcher Type: {build['launcher_type']}")


def _display_slot_information(result: dict[str, Any]) -> None:
    """Display comprehensive slot information."""
    if "slots" in result:
        pout("\nSlots:")
        for slot in result["slots"]:
            _display_single_slot(slot)


def _display_single_slot(slot: dict[str, Any]) -> None:
    """Display information for a single slot."""
    # Format size
    size_str = (
        f"{slot['size'] / 1024:.1f} KB"
        if slot["size"] < 1024 * 1024
        else f"{slot['size'] / (1024 * 1024):.1f} MB"
    )

    # Basic slot info
    slot_line = f"  [{slot['index']}] {slot['id']}: {size_str}"

    # Add operations if not raw
    if slot.get("operations") and slot["operations"] != "raw":
        slot_line += f" [{slot['operations']}]"

    pout(slot_line)

    # Additional metadata on separate lines
    metadata_fields = [
        ("purpose", "Purpose"),
        ("lifecycle", "Lifecycle"),
        ("target", "Target"),
        ("type", "Type"),
        ("permissions", "Permissions"),
        ("checksum", "Checksum"),
    ]

    for field, label in metadata_fields:
        if slot.get(field):
            pout(f"      {label}: {slot[field]}")


def _display_signature_status(result: dict[str, Any]) -> None:
    """Display signature verification status."""
    if result["signature_valid"]:
        log.info("Signature verification successful")
    else:
        log.error("Signature verification failed")
        perr("\n❌ Signature verification failed")
        raise click.Abort()


# 🌶️📦🔚
