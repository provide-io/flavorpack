#!/usr/bin/env python3
#
# flavor/commands/workenv.py
#
"""Work environment management commands for the flavor CLI."""

import datetime
import json

import click


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
        click.echo("No cached packages found.")
        return

    click.echo("🗂️  Cached Packages:")
    click.echo("=" * 60)

    for pkg in cached:
        size_mb = pkg["size"] / (1024 * 1024)
        name = pkg.get("name", pkg["id"])
        version = pkg.get("version", "")

        if version:
            click.echo(f"\n📦 {name} v{version}")
        else:
            click.echo(f"\n📦 {name}")

        click.echo(f"   ID: {pkg['id']}")
        click.echo(f"   Size: {size_mb:.1f} MB")

        modified = datetime.datetime.fromtimestamp(pkg["modified"])
        click.echo(f"   Modified: {modified.strftime('%Y-%m-%d %H:%M:%S')}")


@workenv_group.command("info")
def workenv_info() -> None:
    """Show work environment cache information."""
    from flavor.cache import CacheManager, get_cache_dir

    manager = CacheManager()
    cached = manager.list_cached()
    total_size = manager.get_cache_size()

    click.echo("📊 Cache Information")
    click.echo("=" * 40)
    click.echo(f"Cache directory: {get_cache_dir()}")
    click.echo(f"Total size: {total_size / (1024 * 1024):.1f} MB")
    click.echo(f"Number of packages: {len(cached)}")


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
            click.echo("Aborted.")
            return

    # Clean incomplete extractions first
    incomplete = manager.clean_incomplete()
    if incomplete:
        click.echo(f"Removed {len(incomplete)} incomplete extractions")

    # Clean old packages
    removed = manager.clean(max_age_days=older_than)

    if removed:
        click.secho(f"✅ Cleaned {len(removed)} packages from cache", fg="green")
    else:
        click.echo("No packages to clean")


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
        info = manager.get_info(package_id)
        if info:
            size_mb = info["size"] / (1024 * 1024)
            name = info.get("name", package_id)
            if not click.confirm(f"Remove {name} ({size_mb:.1f} MB)?"):
                click.echo("Aborted.")
                return

    if manager.remove(package_id):
        click.secho(f"✅ Removed package '{package_id}'", fg="green")
    else:
        click.secho(f"❌ Package '{package_id}' not found", fg="red")


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
        click.secho(f"❌ Package '{package_id}' not found", fg="red")
        return
    
    if output_json:
        # Output as JSON
        click.echo(json.dumps(info, indent=2, default=str))
    else:
        # Human-readable output
        click.echo("=" * 60)
        click.echo(f"📦 Package: {package_id}")
        click.echo("-" * 60)
        
        # Basic info
        click.echo(f"📁 Location: {info['content_dir']}")
        click.echo(f"🗂️  Metadata Type: {info.get('metadata_type', 'none')}")
        
        if info.get("extraction_complete"):
            click.echo("✅ Extraction: Complete")
        else:
            click.echo("⚠️  Extraction: Incomplete")
        
        if info.get("checksum"):
            click.echo(f"🔐 Checksum: {info['checksum']}")
        
        # Index metadata from index.json
        if info.get("metadata_dir"):
            from pathlib import Path
            index_file = Path(info["metadata_dir"]) / "instance" / "index.json"
            if index_file.exists():
                try:
                    with open(index_file) as f:
                        index_data = json.load(f)
                    
                    click.echo("\n📋 Index Metadata:")
                    click.echo(f"  Format Version: 0x{index_data.get('format_version', 0):08x}")
                    click.echo(f"  Package Size: {index_data.get('package_size', 0):,} bytes")
                    click.echo(f"  Launcher Size: {index_data.get('launcher_size', 0):,} bytes")
                    click.echo(f"  Slot Count: {index_data.get('slot_count', 0)}")
                    click.echo(f"  Index Checksum: {index_data.get('index_checksum', 'N/A')}")
                    
                    if index_data.get('build_timestamp'):
                        timestamp = index_data['build_timestamp']
                        if timestamp > 0:
                            dt = datetime.datetime.fromtimestamp(timestamp)
                            click.echo(f"  Build Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # Capabilities and requirements
                    if index_data.get('capabilities'):
                        click.echo(f"  Capabilities: 0x{index_data['capabilities']:016x}")
                    if index_data.get('requirements'):
                        click.echo(f"  Requirements: 0x{index_data['requirements']:016x}")
                except Exception as e:
                    click.echo(f"  ⚠️  Error reading index.json: {e}")
        
        # Package metadata
        if info.get("package_info"):
            pkg = info["package_info"]
            click.echo("\n📦 Package Info:")
            click.echo(f"  Name: {pkg.get('name', 'unknown')}")
            click.echo(f"  Version: {pkg.get('version', 'unknown')}")
            if pkg.get("builder"):
                click.echo(f"  Builder: {pkg.get('builder')}")
        
        click.echo()
