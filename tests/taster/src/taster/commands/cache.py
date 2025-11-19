#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Cache management commands for taster."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
import json
import os
from pathlib import Path
import shutil
from typing import Any

import click
from provide.foundation.console import perr, pout


@click.group()
def cache() -> None:
    """Cache management commands."""


@cache.command()
@click.option("--all", "all_caches", is_flag=True, help="Clean all cache directories")
@click.option("--flavor", "flavor_only", is_flag=True, help="Clean flavor cache")
@click.option("--verbose", is_flag=True, help="Show verbose output")
def clean(all_caches: bool, flavor_only: bool, verbose: bool) -> None:
    """Clean cache directories."""

    cleaned: list[str] = []
    clean_flavor = flavor_only or not all_caches

    if all_caches or clean_flavor:
        flavor_cache = Path.home() / "Library" / "Caches" / "flavor"
        _clean_directory(flavor_cache, "flavor", cleaned, verbose, recreate=True)

    _clean_directory(Path("/tmp/pspf"), "tmp", cleaned, verbose)

    for cache_dir in _iter_var_caches():
        _clean_directory(cache_dir, f"var ({cache_dir.parent.name})", cleaned, verbose)

    if not cleaned:
        pout("No caches to clean")


@cache.command()
@click.option("--verbose", is_flag=True, help="Show detailed information")
def info(verbose: bool) -> None:
    """Show cache information."""

    flavor_cache = Path.home() / "Library" / "Caches" / "flavor"
    if flavor_cache.exists():
        cache_dirs = [item for item in flavor_cache.iterdir() if item.is_dir()]
        total_size = 0
        for item in cache_dirs:
            item_size = _safe_dir_size(item)
            total_size += item_size
            if verbose:
                pout(f"  {item.name}: {item_size / 1024 / 1024:.2f} MB")

        pout(f"Flavor cache: {len(cache_dirs)} entries, {total_size / 1024 / 1024:.2f} MB total")
    else:
        pout("Flavor cache: empty")

    tmp_cache = Path("/tmp/pspf")
    if tmp_cache.exists():
        size = _safe_dir_size(tmp_cache)
        pout(f"Tmp cache: {size / 1024 / 1024:.2f} MB")


@cache.command()
@click.argument("workenv", required=False)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--all", "inspect_all", is_flag=True, help="Inspect all cached workenvs")
def inspect(workenv: str | None, output_json: bool, inspect_all: bool) -> None:
    """Inspect cached workenv metadata including index.json."""

    # Check multiple possible cache locations
    cache_locations = [
        Path.home() / "Library" / "Caches" / "flavor" / "workenv",  # macOS
        Path.home() / ".cache" / "flavor" / "workenv",  # Linux/fallback
        Path("/var/folders")
        / os.environ.get("USER", "unknown")
        / "*"
        / "*"
        / "pspf"
        / "workenv",  # macOS temp
        Path("/tmp/pspf/workenv"),  # Linux temp
    ]

    results: dict[str, dict[str, Any]] = {}

    should_stop = False
    for cache_base in cache_locations:
        for cache_dir in _expand_cache_base(cache_base):
            should_stop = _inspect_cache_dir(cache_dir, workenv, inspect_all, results)
            if should_stop:
                break
        if should_stop:
            break

    if not results:
        if workenv:
            pout(f"❌ Workenv '{workenv}' not found in any cache location")
        else:
            pout("❌ No cached workenvs found")
        return

    if output_json:
        pout(json.dumps(results, indent=2, default=str))
    else:
        for name, info in results.items():
            _print_workenv_info(name, info)


def _expand_cache_base(cache_base: Path) -> list[Path]:
    """Return all concrete cache directories for a base path (with glob support)."""
    cache_pattern = str(cache_base)
    if "*" in cache_pattern:
        return list(Path("/").glob(cache_pattern.lstrip("/")))
    if cache_base.exists():
        return [cache_base]
    return []


def _inspect_cache_dir(
    cache_dir: Path,
    workenv: str | None,
    inspect_all: bool,
    results: dict[str, dict[str, Any]],
) -> bool:
    """Inspect cache_dir. Returns True if the search can stop early."""
    if not cache_dir.exists():
        return False

    if inspect_all:
        for entry in cache_dir.iterdir():
            if entry.is_dir() and not entry.name.startswith("."):
                _inspect_workenv(entry.name, cache_dir, results)
        return False

    if workenv:
        _inspect_workenv(workenv, cache_dir, results)
        return bool(results)

    return False


def _inspect_workenv(name: str, cache_dir: Path, results: dict[str, dict[str, Any]]) -> None:
    """Inspect a single workenv and add to results."""
    workenv_dir = cache_dir / name
    if not workenv_dir.exists():
        return

    info = {
        "cache_location": str(cache_dir),
        "workenv_path": str(workenv_dir),
        "exists": True,
        "metadata_type": None,
        "index_metadata": None,
        "package_metadata": None,
        "extraction_complete": False,
        "size_mb": 0,
    }

    # Calculate size
    total_size = _safe_dir_size(workenv_dir)
    info["size_mb"] = round(total_size / 1024 / 1024, 2)

    # Check for metadata directories
    instance_metadata_dir = cache_dir / f".{name}.pspf"
    package_metadata_dir = workenv_dir / ".pspf"

    if instance_metadata_dir.exists():
        info["metadata_type"] = "instance"
        info["metadata_dir"] = str(instance_metadata_dir)

        # Read index.json
        index_file = instance_metadata_dir / "instance" / "index.json"
        if index_file.exists():
            try:
                with index_file.open(encoding="utf-8") as file:
                    info["index_metadata"] = json.load(file)
            except (OSError, json.JSONDecodeError):
                info["index_metadata"] = None

        # Check extraction complete
        complete_markers = [
            instance_metadata_dir / "instance" / "extract" / "complete",
            instance_metadata_dir / "instance" / "extraction.complete",
        ]
        info["extraction_complete"] = any(m.exists() for m in complete_markers)

        # Read package metadata
        psp_file = instance_metadata_dir / "package" / "psp.json"
        if psp_file.exists():
            try:
                with psp_file.open(encoding="utf-8") as file:
                    info["package_metadata"] = json.load(file)
            except (OSError, json.JSONDecodeError):
                info["package_metadata"] = None

    elif package_metadata_dir.exists():
        info["metadata_type"] = "package"
        info["metadata_dir"] = str(package_metadata_dir)

        # Read package metadata
        psp_file = package_metadata_dir / "psp.json"
        if psp_file.exists():
            try:
                with psp_file.open(encoding="utf-8") as file:
                    info["package_metadata"] = json.load(file)
            except (OSError, json.JSONDecodeError):
                info["package_metadata"] = None

    results[name] = info


def _print_workenv_info(name: str, info: Mapping[str, Any]) -> None:
    """Print workenv information in human-readable format."""
    pout("=" * 60)
    pout("-" * 60)
    pout(f"💾 Size: {info['size_mb']} MB")
    pout(f"🗂️  Metadata Type: {info.get('metadata_type', 'none')}")

    if info.get("extraction_complete"):
        pass
    else:
        pout("⚠️  Extraction: Incomplete or not started")

    # Display index metadata if available
    if info.get("index_metadata"):
        idx = info["index_metadata"]
        pout("\n📋 Index Metadata:")
        pout(f"  Format Version: 0x{idx.get('format_version', 0):08x}")
        pout(f"  Package Size: {idx.get('package_size', 0):,} bytes")
        pout(f"  Launcher Size: {idx.get('launcher_size', 0):,} bytes")
        pout(f"  Slot Count: {idx.get('slot_count', 0)}")
        pout(f"  Index Checksum: {idx.get('index_checksum', 'N/A')}")
        if idx.get("build_timestamp"):
            pout(f"  Build Timestamp: {idx.get('build_timestamp')}")

    # Display package metadata if available
    if info.get("package_metadata"):
        pkg = info["package_metadata"].get("package", {})
        pout(f"  Name: {pkg.get('name', 'unknown')}")
        pout(f"  Version: {pkg.get('version', 'unknown')}")

        # Show slots info if available
        if "slots" in info["package_metadata"]:
            slots = info["package_metadata"]["slots"]
            pout(f"\n📂 Slots ({len(slots)}):")
            for slot in slots[:5]:  # Show first 5 slots
                pout(
                    f"  [{slot['index']}] {slot['name']}: {slot.get('size', 0):,} bytes ({slot.get('lifecycle', 'unknown')})"
                )
            if len(slots) > 5:
                pout(f"  ... and {len(slots) - 5} more")

    pout("")


def _clean_directory(
    path: Path, label: str, cleaned: list[str], verbose: bool, *, recreate: bool = False
) -> None:
    """Remove a cache directory, optionally recreating it afterwards."""
    if not path.exists():
        return

    if verbose:
        pout(f"Cleaning {label} cache: {path}")

    try:
        shutil.rmtree(path)
        if recreate:
            path.mkdir(parents=True, exist_ok=True)
        cleaned.append(label)
    except OSError as exc:
        perr(f"Error cleaning {label} cache: {exc}")


def _iter_var_caches() -> Iterator[Path]:
    """Yield cache directories discovered under /var/folders."""
    var_root = Path("/var/folders")
    if not var_root.exists():
        return
    yield from var_root.glob("**/pspf")


def _safe_dir_size(path: Path) -> int:
    """Return directory size in bytes, ignoring I/O errors."""
    total = 0
    try:
        for entry in path.rglob("*"):
            if not entry.is_file():
                continue
            try:
                total += entry.stat().st_size
            except OSError:
                continue
    except OSError:
        return total
    return total


# 🌶️📦🔚
