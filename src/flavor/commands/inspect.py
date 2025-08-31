#!/usr/bin/env python3
#
# flavor/commands/inspect.py
#
"""Inspect command for the flavor CLI - quick package overview."""

from pathlib import Path

import click

from flavor.psp.format_2025.reader import PSPFReader
from flavor.utils.formatting import format_size


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
    import json
    from datetime import datetime

    package_path = Path(package_file)

    try:
        with PSPFReader(package_path) as reader:
            # Get basic info
            index = reader.read_index()
            metadata = reader.read_metadata()
            slot_descriptors = reader.read_slot_descriptors()

            # Get slot metadata from JSON
            slots_metadata = metadata.get("slots", [])

            if output_json:
                # JSON output
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
                            "name": slots_metadata[i].get("id", f"slot_{i}")
                            if i < len(slots_metadata)
                            else f"slot_{i}",
                            "purpose": slots_metadata[i].get("purpose", "unknown")
                            if i < len(slots_metadata)
                            else "unknown",
                            "size": slot.size,
                            "encoding": slots_metadata[i].get("encoding", "raw")
                            if i < len(slots_metadata)
                            else "raw",
                        }
                        for i, slot in enumerate(slot_descriptors)
                    ],
                }
                click.echo(json.dumps(output, indent=2))
            else:
                # Human-readable columnar output
                file_size = package_path.stat().st_size
                launcher_size = index.launcher_size

                # Package header
                click.echo(f"\nPackage: {package_path.name} ({format_size(file_size)})")
                click.echo(f"├── Format: PSPF/0x{index.format_version:08x}")
                click.echo(
                    f"├── Launcher: {metadata.get('build', {}).get('launcher_type', 'Unknown')} ({format_size(launcher_size)})"
                )

                # Build info
                build_time = metadata.get("build", {}).get("timestamp", "Unknown")
                if build_time != "Unknown":
                    try:
                        dt = datetime.fromisoformat(build_time.replace("Z", "+00:00"))
                        build_time = dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        pass
                builder_version = metadata.get("build", {}).get(
                    "builder_version", "Unknown"
                )
                click.echo(f"├── Built: {build_time} with {builder_version}")

                # Package info
                pkg_name = metadata.get("package", {}).get("name", "Unknown")
                pkg_version = metadata.get("package", {}).get("version", "Unknown")
                if pkg_name != "Unknown":
                    click.echo(f"├── Package: {pkg_name} v{pkg_version}")

                # Slots
                click.echo(f"└── Slots: {len(slot_descriptors)}")
                for i, slot in enumerate(slot_descriptors):
                    is_last = i == len(slot_descriptors) - 1
                    prefix = "    └──" if is_last else "    ├──"

                    # Get slot metadata from JSON
                    if i < len(slots_metadata):
                        slot_meta = slots_metadata[i]
                        slot_name = slot_meta.get("id", f"slot_{i}")
                        slot_purpose = slot_meta.get("purpose", "")
                        slot_encoding = slot_meta.get("encoding", "raw")
                    else:
                        slot_name = f"slot_{i}"
                        slot_purpose = ""
                        slot_encoding = "raw"

                    # Format slot info
                    slot_size = format_size(slot.size)
                    slot_info = f"[{i}] {slot_name} ({slot_size})"

                    # Add purpose if available
                    if slot_purpose:
                        slot_info += f" - {slot_purpose}"
                    if slot_encoding != "raw":
                        slot_info += f" [{slot_encoding}]"

                    click.echo(f"{prefix} {slot_info}")

                click.echo()  # Empty line at end

    except FileNotFoundError:
        click.secho(f"❌ Package not found: {package_file}", fg="red", err=True)
        raise click.Abort()
    except Exception as e:
        click.secho(f"❌ Error inspecting package: {e}", fg="red", err=True)
        raise click.Abort()
