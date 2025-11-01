#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Utility commands for the flavor CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
from provide.foundation.console import pout
from provide.foundation.file.directory import safe_rmtree

from flavor.console import get_command_logger

# Get structured logger for this command
log = get_command_logger("clean")


@click.command("clean")
@click.option(
    "--all",
    is_flag=True,
    help="Clean both work environment and helpers",
)
@click.option(
    "--helpers",
    is_flag=True,
    help="Clean only helper binaries",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be removed without removing",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def clean_command(all: bool, helpers: bool, dry_run: bool, yes: bool) -> None:
    """Clean work environment cache (default) or helpers."""
    log.debug(
        "Clean command started",
        all=all,
        helpers=helpers,
        dry_run=dry_run,
        yes=yes,
    )

    # Determine what to clean
    clean_workenv = not helpers or all
    clean_helpers = helpers or all

    if dry_run:
        pout("🔍 DRY RUN - Nothing will be removed\n")

    total_freed = 0

    if clean_workenv:
        total_freed += _clean_workenv_cache(dry_run, yes)

    if clean_helpers:
        total_freed += _clean_helper_binaries(dry_run, yes)

    _show_total_freed(dry_run, total_freed)


def _clean_workenv_cache(dry_run: bool, yes: bool) -> int:
    """Clean workenv cache and return bytes freed."""
    from flavor.cache import CacheManager

    manager = CacheManager()
    cached = manager.list_cached()

    if not cached:
        return 0

    size = manager.get_cache_size()
    size_mb = size / (1024 * 1024)

    if dry_run:
        _show_workenv_dry_run(cached, size_mb)
        return 0

    if not yes and not click.confirm(f"Remove {len(cached)} cached packages ({size_mb:.1f} MB)?"):
        pout("Aborted.")
        return 0

    removed = manager.clean()
    if removed:
        log.info("Removed cached packages", count=len(removed), size_bytes=size)
        pout(f"✅ Removed {len(removed)} cached packages")
        return size

    return 0


def _show_workenv_dry_run(cached: list[dict[str, Any]], size_mb: float) -> None:
    """Show what would be removed from workenv cache."""
    pout(f"Would remove {len(cached)} cached packages ({size_mb:.1f} MB):")
    for pkg in cached:
        pkg_size_mb = pkg["size"] / (1024 * 1024)
        name = pkg.get("name", pkg["id"])
        pout(f"  - {name} ({pkg_size_mb:.1f} MB)")


def _clean_helper_binaries(dry_run: bool, yes: bool) -> int:
    """Clean helper binaries and return bytes freed."""
    helper_dir = Path.home() / ".cache" / "flavor" / "bin"
    if not helper_dir.exists():
        return 0

    helpers_list = _get_helper_files(helper_dir)
    if not helpers_list:
        return 0

    total_size = sum(h.stat().st_size for h in helpers_list)
    size_mb = total_size / (1024 * 1024)

    if dry_run:
        _show_helpers_dry_run(helpers_list, size_mb)
        return 0

    if not yes and not click.confirm(f"Remove {len(helpers_list)} helper binaries ({size_mb:.1f} MB)?"):
        pout("Aborted.")
        return 0

    safe_rmtree(helper_dir)
    log.info(
        "Removed helper binaries",
        count=len(helpers_list),
        size_bytes=total_size,
    )
    pout(f"✅ Removed {len(helpers_list)} helper binaries")
    return total_size


def _get_helper_files(helper_dir: Path) -> list[Path]:
    """Get list of helper files, excluding .d files."""
    helpers_list = list(helper_dir.glob("flavor-*"))
    return [h for h in helpers_list if h.suffix != ".d"]


def _show_helpers_dry_run(helpers_list: list[Path], size_mb: float) -> None:
    """Show what helper binaries would be removed."""
    pout(f"\nWould remove {len(helpers_list)} helper binaries ({size_mb:.1f} MB):")
    for helper in helpers_list:
        h_size_mb = helper.stat().st_size / (1024 * 1024)
        pout(f"  - {helper.name} ({h_size_mb:.1f} MB)")


def _show_total_freed(dry_run: bool, total_freed: int) -> None:
    """Show total space freed if not a dry run."""
    if not dry_run and total_freed > 0:
        freed_mb = total_freed / (1024 * 1024)
        log.info("Total space freed", size_mb=freed_mb, size_bytes=total_freed)
        pout(f"\n💾 Total freed: {freed_mb:.1f} MB")


# 🌶️📦🔚
