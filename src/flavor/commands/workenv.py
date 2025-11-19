#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Work environment management commands for the flavor CLI."""

from __future__ import annotations

import datetime

import click
from provide.foundation.console import perr, pout
from provide.foundation.file.formats import read_json
from provide.foundation.serialization import json_dumps

from flavor.console import get_command_logger

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
        pout("No cached packages found.")
        return

    pout("🗂️  Cached Packages:")
    pout("=" * 60)

    for pkg in cached:
        # Type check: size should be int or float from cache manager
        pkg_size = pkg["size"]
        size_mb = pkg_size / (1024 * 1024) if isinstance(pkg_size, (int, float)) else 0.0
        name = pkg.get("name", pkg["id"])
        version = pkg.get("version", "")

        if version:
            pout(f"\n📦 {name} v{version}")
        else:
            pout(f"\n📦 {name}")

        pout(f"   ID: {pkg['id']}")
        pout(f"   Size: {size_mb:.1f} MB")

        # Type check: modified should be a float timestamp
        modified_ts = pkg.get("modified", 0)
        if isinstance(modified_ts, (int, float)):
            modified = datetime.datetime.fromtimestamp(modified_ts)
        else:
            modified = datetime.datetime.now()
        pout(f"   Modified: {modified.strftime('%Y-%m-%d %H:%M:%S')}")


@workenv_group.command("info")
def workenv_info() -> None:
    """Show work environment cache information."""
    from flavor.cache import CacheManager, get_cache_dir

    manager = CacheManager()
    cached = manager.list_cached()
    total_size = manager.get_cache_size()

    pout("📊 Cache Information")
    pout("=" * 40)
    pout(f"Cache directory: {get_cache_dir()}")
    pout(f"Total size: {total_size / (1024 * 1024):.1f} MB")
    pout(f"Number of packages: {len(cached)}")


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
            pout("Aborted.")
            return

    # Clean old packages
    removed = manager.clean(max_age_days=older_than)

    if removed:
        pout(f"✅ Removed {len(removed)} cached package(s)")
    else:
        pout("No packages to clean")


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
                pout("Aborted.")
                return

    if manager.remove(package_id):
        pass
    else:
        perr(f"❌ Package '{package_id}' not found")


@workenv_group.command("inspect")
@click.argument("package_id")
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON format",
)
def workenv_inspect(package_id: str, output_json: bool) -> None:  # noqa: C901
    """Inspect detailed metadata for a cached package extraction."""
    from flavor.cache import CacheManager

    manager = CacheManager()
    info = manager.inspect_workenv(package_id)

    if not info.get("exists"):
        perr(f"❌ Package '{package_id}' not found")
        return

    if output_json:
        # Output as JSON
        pout(json_dumps(info, indent=2, default=str))
    else:
        # Human-readable output
        pout("=" * 60)
        pout(f"📦 Package: {package_id}")
        pout("-" * 60)

        # Basic info
        pout(f"📁 Location: {info['content_dir']}")
        pout(f"🗂️  Metadata Type: {info.get('metadata_type', 'none')}")

        if info.get("extraction_complete"):
            pout("✅ Extraction: Complete")
        else:
            pout("⚠️  Extraction: Incomplete")

        if info.get("checksum"):
            pout(f"🔐 Checksum: {info['checksum']}")

        # Index metadata from index.json
        if info.get("metadata_dir"):
            from pathlib import Path

            index_file = Path(info["metadata_dir"]) / "instance" / "index.json"
            if index_file.exists():
                try:
                    index_data = read_json(index_file)

                    pout("\n📋 Index Metadata:")
                    pout(f"  Format Version: 0x{index_data.get('format_version', 0):08x}")
                    pout(f"  Package Size: {index_data.get('package_size', 0):,} bytes")
                    pout(f"  Launcher Size: {index_data.get('launcher_size', 0):,} bytes")
                    pout(f"  Slot Count: {index_data.get('slot_count', 0)}")
                    pout(f"  Index Checksum: {index_data.get('index_checksum', 'N/A')}")

                    if index_data.get("build_timestamp"):
                        timestamp = index_data["build_timestamp"]
                        if timestamp > 0:
                            dt = datetime.datetime.fromtimestamp(timestamp)
                            pout(f"  Build Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}")

                    # Capabilities and requirements
                    if index_data.get("capabilities"):
                        pout(f"  Capabilities: 0x{index_data['capabilities']:016x}")
                    if index_data.get("requirements"):
                        pout(f"  Requirements: 0x{index_data['requirements']:016x}")
                except Exception as e:
                    pout(f"  ⚠️  Error reading index.json: {e}")

        # Package metadata
        if info.get("package_info"):
            pkg = info["package_info"]
            pout(f"  Name: {pkg.get('name', 'unknown')}")
            pout(f"  Version: {pkg.get('version', 'unknown')}")
            if pkg.get("builder"):
                pout(f"  Builder: {pkg.get('builder')}")

        pout("")


# 🌶️📦🔚
