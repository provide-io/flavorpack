#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Inspect command for the flavor CLI - quick package overview."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
from provide.foundation.console import perr, pout
from provide.foundation.formatting import format_size
from provide.foundation.serialization import json_dumps

from flavor.console import get_command_logger
from flavor.psp.format_2025.operations import operations_to_string
from flavor.psp.format_2025.reader import PSPFReader

# Get structured logger for this command
log = get_command_logger("inspect")


@click.command("inspect")
@click.argument(
    "package_file",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    required=True,
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
def inspect_command(package_file: str, output_json: bool) -> None:
    """Quick inspection of a flavor package."""
    package_path = Path(package_file)
    log.debug("Inspecting package", package=str(package_path), output_json=output_json)

    try:
        with PSPFReader(package_path) as reader:
            index = reader.read_index()
            metadata = reader.read_metadata()
            slot_descriptors = reader.read_slot_descriptors()
            slots_metadata = metadata.get("slots", [])

            log.debug(
                "Package inspection completed",
                format_version=f"0x{index.format_version:08x}",
                slot_count=len(slot_descriptors),
            )

            if output_json:
                _output_json_format(package_path, index, metadata, slot_descriptors, slots_metadata)
            else:
                _output_human_format(package_path, index, metadata, slot_descriptors, slots_metadata)

    except FileNotFoundError as e:
        log.error("Package not found", package=package_file)
        perr(f"❌ Package not found: {package_file}")
        raise click.Abort() from e
    except Exception as e:
        log.error("Error inspecting package", package=package_file, error=str(e))
        perr(f"❌ Error inspecting package: {e}")
        raise click.Abort() from e


def _output_json_format(
    package_path: Path,
    index: Any,
    metadata: dict[str, Any],
    slot_descriptors: list[Any],
    slots_metadata: list[dict[str, Any]],
) -> None:
    """Output package information in JSON format."""
    output = {
        "package": str(package_path.name),
        "format": f"PSPF/0x{index.format_version:08x}",
        "format_version": f"0x{index.format_version:08x}",
        "size": package_path.stat().st_size,
        "launcher_size": index.launcher_size,
        "package_metadata": metadata.get("package", {}),
        "build_metadata": metadata.get("build", {}),
        "slots": [
            {
                "index": i,
                "name": slots_metadata[i].get("id", f"slot_{i}") if i < len(slots_metadata) else f"slot_{i}",
                "purpose": slots_metadata[i].get("purpose", "unknown")
                if i < len(slots_metadata)
                else "unknown",
                "size": slot.size,
                "operations": operations_to_string(slot.operations),
            }
            for i, slot in enumerate(slot_descriptors)
        ],
    }
    pout(json_dumps(output, indent=2))


def _output_human_format(
    package_path: Path,
    index: Any,
    metadata: dict[str, Any],
    slot_descriptors: list[Any],
    slots_metadata: list[dict[str, Any]],
) -> None:
    """Output package information in human-readable format."""

    file_size = package_path.stat().st_size
    launcher_size = index.launcher_size

    # Package header
    pout(f"\nPackage: {package_path.name} ({format_size(file_size)})")
    pout(f"├── Format: PSPF/0x{index.format_version:08x}")
    pout(
        f"├── Launcher: {metadata.get('build', {}).get('launcher_type', 'Unknown')} ({format_size(launcher_size)})"
    )

    # Build info
    build_time = _format_build_time(metadata.get("build", {}).get("timestamp", "Unknown"))
    builder_version = metadata.get("build", {}).get("builder_version", "Unknown")
    pout(f"├── Built: {build_time} with {builder_version}")

    # Package info
    pkg_name = metadata.get("package", {}).get("name", "Unknown")
    pkg_version = metadata.get("package", {}).get("version", "Unknown")
    if pkg_name != "Unknown":
        pout(f"├── Package: {pkg_name} v{pkg_version}")

    # Slots
    pout(f"└── Slots: {len(slot_descriptors)}")
    _output_slot_details(slot_descriptors, slots_metadata)
    pout("")  # Empty line at end


def _format_build_time(build_time: str) -> str:
    """Format build timestamp for human-readable output."""
    from datetime import datetime

    if build_time == "Unknown":
        return build_time

    try:
        dt = datetime.fromisoformat(build_time.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return build_time  # Keep original timestamp if parsing fails


def _output_slot_details(slot_descriptors: list[Any], slots_metadata: list[dict[str, Any]]) -> None:
    """Output detailed slot information."""
    for i, slot in enumerate(slot_descriptors):
        is_last = i == len(slot_descriptors) - 1
        prefix = "    └──" if is_last else "    ├──"

        # Get slot metadata from JSON
        if i < len(slots_metadata):
            slot_meta = slots_metadata[i]
            slot_name = slot_meta.get("id", f"slot_{i}")
            slot_purpose = slot_meta.get("purpose", "")
        else:
            slot_name = f"slot_{i}"
            slot_purpose = ""

        # Get operations from slot descriptor
        slot_operations = operations_to_string(slot.operations)

        # Format slot info
        slot_size = format_size(slot.size)
        slot_info = f"[{i}] {slot_name} ({slot_size})"

        # Add purpose if available
        if slot_purpose:
            slot_info += f" - {slot_purpose}"
        if slot_operations != "raw":
            slot_info += f" [{slot_operations}]"

        pout(f"{prefix} {slot_info}")


# 🌶️📦🔚
