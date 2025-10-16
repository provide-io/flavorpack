#!/usr/bin/env python3
#
# flavor/commands/workenv.py
#
"""Work environment management commands for the flavor CLI."""

import datetime

import click
from provide.foundation.file.formats import read_json
from provide.foundation.serialization import json_dumps

from flavor.console import echo, echo_error, get_command_logger

# Get structured logger for workenv commands
log = get_command_logger("workenv")


@click.group("workenv")
def workenv_group() -> None:
    """Manage the Flavor work environment cache."""
    pass


@workenv_group.command("list")
def workenv_list() -> None:
    """List cached package extractions."""
    from flavor.cache import CacheManager

    manager = CacheManager()
    cached = manager.list_cached()

    if not cached:
        echo("No cached packages found.")
        return

    echo("🗂️  Cached Packages:")
    echo("=" * 60)

    for pkg in cached:
        size_mb = pkg["size"] / (1024 * 1024)
        name = pkg.get("name", pkg["id"])
        version = pkg.get("version", "")

        if version:
            echo(f"\n📦 {name} v{version}")
        else:
            echo(f"\n📦 {name}")

        echo(f"   ID: {pkg['id']}")
        echo(f"   Size: {size_mb:.1f} MB")

        modified = datetime.datetime.fromtimestamp(pkg["modified"])
        echo(f"   Modified: {modified.strftime('%Y-%m-%d %H:%M:%S')}")


@workenv_group.command("info")
def workenv_info() -> None:
    """Show work environment cache information."""
    from flavor.cache import CacheManager, get_cache_dir

    manager = CacheManager()
    cached = manager.list_cached()
    total_size = manager.get_cache_size()

    echo("📊 Cache Information")
    echo("=" * 40)
    echo(f"Cache directory: {get_cache_dir()}")
    echo(f"Total size: {total_size / (1024 * 1024):.1f} MB")
    echo(f"Number of packages: {len(cached)}")


@workenv_group.command("clean")
@click.option(
    "--older-than",
    type=int,
    help="Remove packages older than N days",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def workenv_clean(older_than: int | None, yes: bool) -> None:
    """Clean the work environment cache."""
    from flavor.cache import CacheManager

    manager = CacheManager()

    if not yes:
        if older_than:
            prompt = f"Remove cached packages older than {older_than} days?"
        else:
            prompt = "Remove all cached packages?"

        if not click.confirm(prompt):
            echo("Aborted.")
            return

    # Clean old packages
    removed = manager.clean(max_age_days=older_than)

    if removed:
        echo(f"""✅ Removed {len(removed)} cached package(s)""")
    else:
        echo("No packages to clean")


@workenv_group.command("remove")
@click.argument("package_id")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def workenv_remove(package_id: str, yes: bool) -> None:
    """Remove a specific cached package extraction."""
    from flavor.cache import CacheManager

    manager = CacheManager()

    if not yes:
        info = manager.inspect_workenv(package_id)
        if info and info.get("exists"):
            from pathlib import Path

            size_mb = manager._get_dir_size(Path(info["content_dir"])) / (1024 * 1024)
            name = info.get("package_info", {}).get("name", package_id)
            if not click.confirm(f"""Remove {name} ({size_mb:.1f} MB)?"""):
                echo("Aborted.")
                return

    if manager.remove(package_id):
        echo(f"✅ Removed package '{package_id}'")
    else:
        echo_error(f"❌ Package '{package_id}' not found")


@workenv_group.command("inspect")
@click.argument("package_id")
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON format",
)
def workenv_inspect(package_id: str, output_json: bool) -> None:
    """Inspect detailed metadata for a cached package extraction."""
    from flavor.cache import CacheManager

    manager = CacheManager()
    info = manager.inspect_workenv(package_id)

    if not info.get("exists"):
        echo_error(f"❌ Package '{package_id}' not found")
        return

    if output_json:
        # Output as JSON
        echo(json_dumps(info, indent=2, default=str))
    else:
        # Human-readable output
        echo("=" * 60)
        echo(f"📦 Package: {package_id}")
        echo("-" * 60)

        # Basic info
        echo(f"📁 Location: {info['content_dir']}")
        echo(f"🗂️  Metadata Type: {info.get('metadata_type', 'none')}")

        if info.get("extraction_complete"):
            echo("✅ Extraction: Complete")
        else:
            echo("⚠️  Extraction: Incomplete")

        if info.get("checksum"):
            echo(f"🔐 Checksum: {info['checksum']}")

        # Index metadata from index.json
        if info.get("metadata_dir"):
            from pathlib import Path

            index_file = Path(info["metadata_dir"]) / "instance" / "index.json"
            if index_file.exists():
                try:
                    index_data = read_json(index_file)

                    echo("\n📋 Index Metadata:")
                    echo(f"  Format Version: 0x{index_data.get('format_version', 0):08x}")
                    echo(f"  Package Size: {index_data.get('package_size', 0):,} bytes")
                    echo(f"  Launcher Size: {index_data.get('launcher_size', 0):,} bytes")
                    echo(f"  Slot Count: {index_data.get('slot_count', 0)}")
                    echo(f"  Index Checksum: {index_data.get('index_checksum', 'N/A')}")

                    if index_data.get("build_timestamp"):
                        timestamp = index_data["build_timestamp"]
                        if timestamp > 0:
                            dt = datetime.datetime.fromtimestamp(timestamp)
                            echo(f"  Build Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}")

                    # Capabilities and requirements
                    if index_data.get("capabilities"):
                        echo(f"  Capabilities: 0x{index_data['capabilities']:016x}")
                    if index_data.get("requirements"):
                        echo(f"  Requirements: 0x{index_data['requirements']:016x}")
                except Exception as e:
                    echo(f"  ⚠️  Error reading index.json: {e}")

        # Package metadata
        if info.get("package_info"):
            pkg = info["package_info"]
            echo("\n📦 Package Info:")
            echo(f"  Name: {pkg.get('name', 'unknown')}")
            echo(f"  Version: {pkg.get('version', 'unknown')}")
            if pkg.get("builder"):
                echo(f"  Builder: {pkg.get('builder')}")

        echo("")
