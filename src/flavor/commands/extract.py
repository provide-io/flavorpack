#!/usr/bin/env python3
#
# flavor/commands/extract.py
#
"""Extract command for the flavor CLI - extract slots from packages."""

from pathlib import Path

import click
from provide.foundation.file import atomic_write
from provide.foundation.file.directory import ensure_dir, ensure_parent_dir
from provide.foundation.file.formats import write_json
from provide.foundation.formatting import format_size

from flavor.console import echo, echo_error, get_command_logger
from flavor.psp.format_2025.reader import PSPFReader

# Get structured logger for this command
log = get_command_logger("extract")


@click.command("extract")
@click.argument(
    "package_file",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    required=True,
)
@click.argument(
    "slot_index",
    type=int,
    required=True,
)
@click.argument(
    "output_path",
    type=click.Path(dir_okay=False, resolve_path=True),
    required=True,
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing output file",
)
def extract_command(package_file: str, slot_index: int, output_path: str, force: bool) -> None:
    """Extract a specific slot from a flavor package.

    SLOT_INDEX is the 0-based index of the slot to extract.
    OUTPUT_PATH is where to write the extracted data.
    """
    package_path = Path(package_file)
    output = Path(output_path)
    log.debug(
        "Extracting slot",
        package=str(package_path),
        slot_index=slot_index,
        output=str(output),
        force=force,
    )

    # Check if output exists
    if output.exists() and not force:
        log.error("Output file already exists", output=str(output))
        echo_error(f"❌ Output file already exists: {output}")
        echo_error("Use --force to overwrite")
        raise click.Abort()

    try:
        with PSPFReader(package_path) as reader:
            # Get slot descriptors and metadata
            slot_descriptors = reader.read_slot_descriptors()
            metadata = reader.read_metadata()
            slots_metadata = metadata.get("slots", [])

            # Validate slot index
            if slot_index < 0 or slot_index >= len(slot_descriptors):
                log.error(
                    "Invalid slot index",
                    slot_index=slot_index,
                    slot_count=len(slot_descriptors),
                )
                echo_error(
                    f"❌ Invalid slot index {slot_index}. Package has {len(slot_descriptors)} slots (0-{len(slot_descriptors) - 1})"
                )
                raise click.Abort()

            slot = slot_descriptors[slot_index]
            slot_name = (
                slots_metadata[slot_index].get(
                    "id", slots_metadata[slot_index].get("name", f"slot_{slot_index}")
                )
                if slot_index < len(slots_metadata)
                else f"slot_{slot_index}"
            )
            echo(f"Extracting slot {slot_index}: {slot_name} ({format_size(slot.size)})")

            # Extract the slot data
            data = reader.read_slot(slot_index)

            # Write to output (atomic for safety)
            ensure_parent_dir(output)
            atomic_write(output, data)

            log.info(
                "Slot extracted successfully",
                slot_index=slot_index,
                size=len(data),
                output=str(output),
            )
            echo(f"✅ Extracted {format_size(len(data))} to {output}")

    except FileNotFoundError as e:
        log.error("Package not found", package=package_file)
        echo_error(f"❌ Package not found: {package_file}")
        raise click.Abort() from e
    except Exception as e:
        log.error("Error extracting slot", error=str(e), package=package_file)
        echo_error(f"❌ Error extracting slot: {e}")
        raise click.Abort() from e


@click.command("extract-all")
@click.argument(
    "package_file",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    required=True,
)
@click.argument(
    "output_dir",
    type=click.Path(file_okay=False, resolve_path=True),
    required=True,
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing files",
)
def extract_all_command(package_file: str, output_dir: str, force: bool) -> None:
    """Extract all slots from a flavor package to a directory."""
    package_path = Path(package_file)
    output = Path(output_dir)
    log.debug(
        "Extracting all slots",
        package=str(package_path),
        output_dir=str(output),
        force=force,
    )

    # Create output directory
    ensure_dir(output)

    try:
        with PSPFReader(package_path) as reader:
            # Get slot descriptors and metadata
            slot_descriptors = reader.read_slot_descriptors()
            metadata = reader.read_metadata()
            slots_metadata = metadata.get("slots", [])

            echo(f"Extracting {len(slot_descriptors)} slots from {package_path.name}")

            for i, slot in enumerate(slot_descriptors):
                # Get slot metadata
                if i < len(slots_metadata):
                    slot_meta = slots_metadata[i]
                    slot_name = slot_meta.get("id", f"slot_{i}")
                    slot_codec = slot_meta.get("codec", "raw")
                else:
                    slot_name = f"slot_{i}"
                    slot_codec = "raw"

                # Determine output filename
                filename = f"{i:02d}_{slot_name}"
                # Add appropriate extension based on encoding
                if slot_codec in ["tar", "tgz"]:
                    filename += f".{slot_codec}"
                elif slot_codec == "gzip":
                    filename += ".gz"

                output_file = output / filename

                # Check if exists
                if output_file.exists() and not force:
                    echo(f"⏭️  Skipping {filename} (exists)")
                    continue

                # Extract slot data
                log.debug("Extracting slot", slot_index=i, slot_name=slot_name)
                echo(f"📦 Extracting slot {i}: {slot_name} ({format_size(slot.size)})")
                data = reader.read_slot(i)

                # Write to file (atomic for safety)
                atomic_write(output_file, data)
                echo(f"   → {output_file}")

            # Also write metadata
            metadata_file = output / "metadata.json"
            if not metadata_file.exists() or force:
                write_json(metadata_file, metadata, indent=2)
                echo(f"📋 Metadata → {metadata_file}")

            log.info(
                "All slots extracted successfully",
                slot_count=len(slot_descriptors),
                output_dir=str(output),
            )
            echo(f"✅ Extracted all slots to {output}")

    except FileNotFoundError as e:
        log.error("Package not found", package=package_file)
        echo_error(f"❌ Package not found: {package_file}")
        raise click.Abort() from e
    except Exception as e:
        log.error("Error extracting", error=str(e), package=package_file)
        echo_error(f"❌ Error extracting: {e}")
        raise click.Abort() from e
