#!/usr/bin/env python3
#
# flavor/commands/extract.py
#
"""Extract command for the flavor CLI - extract slots from packages."""

from pathlib import Path

import click

from flavor.psp.format_2025.reader import PSPFReader
from flavor.utils.formatting import format_size


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
def extract_command(
    package_file: str, slot_index: int, output_path: str, force: bool
) -> None:
    """Extract a specific slot from a flavor package.

    SLOT_INDEX is the 0-based index of the slot to extract.
    OUTPUT_PATH is where to write the extracted data.
    """
    package_path = Path(package_file)
    output = Path(output_path)

    # Check if output exists
    if output.exists() and not force:
        click.secho(f"❌ Output file already exists: {output}", fg="red", err=True)
        click.echo("Use --force to overwrite", err=True)
        raise click.Abort()

    try:
        with PSPFReader(package_path) as reader:
            # Get slot descriptors and metadata
            slot_descriptors = reader.read_slot_descriptors()
            metadata = reader.read_metadata()
            slots_metadata = metadata.get("slots", [])

            # Validate slot index
            if slot_index < 0 or slot_index >= len(slot_descriptors):
                click.secho(
                    f"❌ Invalid slot index {slot_index}. Package has {len(slot_descriptors)} slots (0-{len(slot_descriptors) - 1})",
                    fg="red",
                    err=True,
                )
                raise click.Abort()

            slot = slot_descriptors[slot_index]
            slot_name = (
                slots_metadata[slot_index].get("id", slots_metadata[slot_index].get("name", f"slot_{slot_index}"))
                if slot_index < len(slots_metadata)
                else f"slot_{slot_index}"
            )
            click.echo(
                f"Extracting slot {slot_index}: {slot_name} ({format_size(slot.size)})"
            )

            # Extract the slot data
            data = reader.read_slot(slot_index)

            # Write to output
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(data)

            click.secho(
                f"✅ Extracted {format_size(len(data))} to {output}", fg="green"
            )

    except FileNotFoundError:
        click.secho(f"❌ Package not found: {package_file}", fg="red", err=True)
        raise click.Abort()
    except Exception as e:
        click.secho(f"❌ Error extracting slot: {e}", fg="red", err=True)
        raise click.Abort()


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

    # Create output directory
    output.mkdir(parents=True, exist_ok=True)

    try:
        with PSPFReader(package_path) as reader:
            # Get slot descriptors and metadata
            slot_descriptors = reader.read_slot_descriptors()
            metadata = reader.read_metadata()
            slots_metadata = metadata.get("slots", [])

            click.echo(
                f"Extracting {len(slot_descriptors)} slots from {package_path.name}"
            )

            for i, slot in enumerate(slot_descriptors):
                # Get slot metadata
                if i < len(slots_metadata):
                    slot_meta = slots_metadata[i]
                    slot_name = slot_meta.get("id", f"slot_{i}")
                    slot_encoding = slot_meta.get("encoding", "raw")
                else:
                    slot_name = f"slot_{i}"
                    slot_encoding = "raw"

                # Determine output filename
                filename = f"{i:02d}_{slot_name}"
                # Add appropriate extension based on encoding
                if slot_encoding in ["tar", "tgz"]:
                    filename += f".{slot_encoding}"
                elif slot_encoding == "gzip":
                    filename += ".gz"

                output_file = output / filename

                # Check if exists
                if output_file.exists() and not force:
                    click.echo(f"⏭️  Skipping {filename} (exists)")
                    continue

                # Extract slot data
                click.echo(
                    f"📦 Extracting slot {i}: {slot_name} ({format_size(slot.size)})"
                )
                data = reader.read_slot(i)

                # Write to file
                output_file.write_bytes(data)
                click.echo(f"   → {output_file}")

            # Also write metadata
            metadata_file = output / "metadata.json"
            if not metadata_file.exists() or force:
                import json

                metadata_file.write_text(json.dumps(metadata, indent=2))
                click.echo(f"📋 Metadata → {metadata_file}")

            click.secho(f"✅ Extracted all slots to {output}", fg="green")

    except FileNotFoundError:
        click.secho(f"❌ Package not found: {package_file}", fg="red", err=True)
        raise click.Abort()
    except Exception as e:
        click.secho(f"❌ Error extracting: {e}", fg="red", err=True)
        raise click.Abort()
