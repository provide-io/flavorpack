#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Cache management commands for taster."""

import json
import os
from pathlib import Path
import shutil

import click


@click.group()
def cache() -> None:
    """Cache management commands."""
    pass


@cache.command()
@click.option("--all", is_flag=True, help="Clean all cache directories")
@click.option("--flavor", is_flag=True, help="Clean flavor cache")
@click.option("--verbose", is_flag=True, help="Show verbose output")
def clean(all, flavor, verbose) -> None:
    """Clean cache directories."""
    cleaned = []

    # Default to cleaning flavor cache if nothing specified
    if not all and not flavor:
        flavor = True

    if all or flavor:
        # Clean flavor cache
        flavor_cache = Path.home() / "Library" / "Caches" / "flavor"
        if flavor_cache.exists():
            if verbose:
                click.echo(f"Cleaning flavor cache: {flavor_cache}")
            try:
                shutil.rmtree(flavor_cache)
                flavor_cache.mkdir(parents=True, exist_ok=True)
                cleaned.append("flavor")
            except Exception as e:
                click.echo(f"Error cleaning flavor cache: {e}", err=True)

    # Also check for /tmp/pspf cache
    tmp_cache = Path("/tmp/pspf")
    if tmp_cache.exists():
        if verbose:
            click.echo(f"Cleaning tmp cache: {tmp_cache}")
        try:
            shutil.rmtree(tmp_cache)
            cleaned.append("tmp")
        except Exception as e:
            click.echo(f"Error cleaning tmp cache: {e}", err=True)

    # Check for /var/folders caches
    var_cache = Path("/var/folders")
    if var_cache.exists():
        for cache_dir in var_cache.glob("**/pspf"):
            if verbose:
                click.echo(f"Cleaning var cache: {cache_dir}")
            try:
                shutil.rmtree(cache_dir)
                cleaned.append(f"var ({cache_dir.parent.name})")
            except Exception as e:
                if verbose:
                    click.echo(f"Error cleaning var cache: {e}", err=True)

    if cleaned:
        pass
    else:
        click.echo("No caches to clean")


@cache.command()
@click.option("--verbose", is_flag=True, help="Show detailed information")
def info(verbose) -> None:
    """Show cache information."""
    # Flavor cache
    flavor_cache = Path.home() / "Library" / "Caches" / "flavor"
    if flavor_cache.exists():
        total_size = 0
        cache_count = 0
        for item in flavor_cache.iterdir():
            if item.is_dir():
                cache_count += 1
                if verbose:
                    item_size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                    total_size += item_size
                    click.echo(f"  {item.name}: {item_size / 1024 / 1024:.2f} MB")
                else:
                    total_size += sum(f.stat().st_size for f in item.rglob("*") if f.is_file())

        click.echo(f"Flavor cache: {cache_count} entries, {total_size / 1024 / 1024:.2f} MB total")
    else:
        click.echo("Flavor cache: empty")

    # Tmp cache
    tmp_cache = Path("/tmp/pspf")
    if tmp_cache.exists():
        size = sum(f.stat().st_size for f in tmp_cache.rglob("*") if f.is_file())
        click.echo(f"Tmp cache: {size / 1024 / 1024:.2f} MB")


@cache.command()
@click.argument("workenv", required=False)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--all", is_flag=True, help="Inspect all cached workenvs")
def inspect(workenv, output_json, all) -> None:
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

    results = {}

    for cache_base in cache_locations:
        # Handle glob patterns
        if "*" in str(cache_base):
            cache_dirs = list(Path("/").glob(str(cache_base).lstrip("/")))
        else:
            cache_dirs = [cache_base] if cache_base.exists() else []

        for cache_dir in cache_dirs:
            if not cache_dir.exists():
                continue

            if all:
                # Inspect all workenvs
                for entry in cache_dir.iterdir():
                    if entry.is_dir() and not entry.name.startswith("."):
                        _inspect_workenv(entry.name, cache_dir, results)
            elif workenv:
                # Inspect specific workenv
                _inspect_workenv(workenv, cache_dir, results)
                if results:
                    break  # Found it, stop searching

    if not results:
        if workenv:
            click.echo(f"❌ Workenv '{workenv}' not found in any cache location")
        else:
            click.echo("❌ No cached workenvs found")
        return

    if output_json:
        click.echo(json.dumps(results, indent=2, default=str))
    else:
        for name, info in results.items():
            _print_workenv_info(name, info)


def _inspect_workenv(name: str, cache_dir: Path, results: dict) -> None:
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
    try:
        total_size = sum(f.stat().st_size for f in workenv_dir.rglob("*") if f.is_file())
        info["size_mb"] = round(total_size / 1024 / 1024, 2)
    except:
        pass

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
                with open(index_file) as f:
                    info["index_metadata"] = json.load(f)
            except:
                pass

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
                with open(psp_file) as f:
                    info["package_metadata"] = json.load(f)
            except:
                pass

    elif package_metadata_dir.exists():
        info["metadata_type"] = "package"
        info["metadata_dir"] = str(package_metadata_dir)

        # Read package metadata
        psp_file = package_metadata_dir / "psp.json"
        if psp_file.exists():
            try:
                with open(psp_file) as f:
                    info["package_metadata"] = json.load(f)
            except:
                pass

    results[name] = info


def _print_workenv_info(name: str, info: dict) -> None:
    """Print workenv information in human-readable format."""
    click.echo("=" * 60)
    click.echo("-" * 60)
    click.echo(f"💾 Size: {info['size_mb']} MB")
    click.echo(f"🗂️  Metadata Type: {info.get('metadata_type', 'none')}")

    if info.get("extraction_complete"):
        pass
    else:
        click.echo("⚠️  Extraction: Incomplete or not started")

    # Display index metadata if available
    if info.get("index_metadata"):
        idx = info["index_metadata"]
        click.echo("\n📋 Index Metadata:")
        click.echo(f"  Format Version: 0x{idx.get('format_version', 0):08x}")
        click.echo(f"  Package Size: {idx.get('package_size', 0):,} bytes")
        click.echo(f"  Launcher Size: {idx.get('launcher_size', 0):,} bytes")
        click.echo(f"  Slot Count: {idx.get('slot_count', 0)}")
        click.echo(f"  Index Checksum: {idx.get('index_checksum', 'N/A')}")
        if idx.get("build_timestamp"):
            click.echo(f"  Build Timestamp: {idx.get('build_timestamp')}")

    # Display package metadata if available
    if info.get("package_metadata"):
        pkg = info["package_metadata"].get("package", {})
        click.echo(f"  Name: {pkg.get('name', 'unknown')}")
        click.echo(f"  Version: {pkg.get('version', 'unknown')}")

        # Show slots info if available
        if "slots" in info["package_metadata"]:
            slots = info["package_metadata"]["slots"]
            click.echo(f"\n📂 Slots ({len(slots)}):")
            for slot in slots[:5]:  # Show first 5 slots
                click.echo(
                    f"  [{slot['index']}] {slot['name']}: {slot.get('size', 0):,} bytes ({slot.get('lifecycle', 'unknown')})"
                )
            if len(slots) > 5:
                click.echo(f"  ... and {len(slots) - 5} more")

    click.echo()


# 🌶️📦🔚
