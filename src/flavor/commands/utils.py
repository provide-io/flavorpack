#!/usr/bin/env python3
#
# flavor/commands/utils.py
#
"""Utility commands for the flavor CLI."""

from pathlib import Path

import click
from provide.foundation.file.directory import safe_rmtree


@click.command("clean")
@click.option(
    "--all",
    is_flag=True,
    help="Clean both work environment and ingredients",
)
@click.option(
    "--ingredients",
    is_flag=True,
    help="Clean only ingredient binaries",
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
def clean_command(all: bool, ingredients: bool, dry_run: bool, yes: bool) -> None:
    """Clean work environment cache (default) or ingredients."""
    # Determine what to clean
    clean_workenv = not ingredients or all
    clean_ingredients = ingredients or all

    if dry_run:
        click.echo("🔍 DRY RUN - Nothing will be removed\n")

    total_freed = 0

    if clean_workenv:
        total_freed += _clean_workenv_cache(dry_run, yes)

    if clean_ingredients:
        total_freed += _clean_ingredient_binaries(dry_run, yes)

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

    if not yes and not click.confirm(
        f"Remove {len(cached)} cached packages ({size_mb:.1f} MB)?"
    ):
        click.echo("Aborted.")
        return 0

    removed = manager.clean()
    if removed:
        click.secho(f"✅ Removed {len(removed)} cached packages", fg="green")
        return size

    return 0


def _show_workenv_dry_run(cached: list, size_mb: float) -> None:
    """Show what would be removed from workenv cache."""
    click.echo(f"Would remove {len(cached)} cached packages ({size_mb:.1f} MB):")
    for pkg in cached:
        pkg_size_mb = pkg["size"] / (1024 * 1024)
        name = pkg.get("name", pkg["id"])
        click.echo(f"  - {name} ({pkg_size_mb:.1f} MB)")


def _clean_ingredient_binaries(dry_run: bool, yes: bool) -> int:
    """Clean ingredient binaries and return bytes freed."""
    ingredient_dir = Path.home() / ".cache" / "flavor" / "bin"
    if not ingredient_dir.exists():
        return 0

    ingredients_list = _get_ingredient_files(ingredient_dir)
    if not ingredients_list:
        return 0

    total_size = sum(h.stat().st_size for h in ingredients_list)
    size_mb = total_size / (1024 * 1024)

    if dry_run:
        _show_ingredients_dry_run(ingredients_list, size_mb)
        return 0

    if not yes and not click.confirm(
        f"Remove {len(ingredients_list)} ingredient binaries ({size_mb:.1f} MB)?"
    ):
        click.echo("Aborted.")
        return 0

    safe_rmtree(ingredient_dir)
    click.secho(
        f"✅ Removed {len(ingredients_list)} ingredient binaries",
        fg="green",
    )
    return total_size


def _get_ingredient_files(ingredient_dir: Path) -> list[Path]:
    """Get list of ingredient files, excluding .d files."""
    ingredients_list = list(ingredient_dir.glob("flavor-*"))
    return [h for h in ingredients_list if h.suffix != ".d"]


def _show_ingredients_dry_run(ingredients_list: list[Path], size_mb: float) -> None:
    """Show what ingredient binaries would be removed."""
    click.echo(
        f"\nWould remove {len(ingredients_list)} ingredient binaries ({size_mb:.1f} MB):"
    )
    for ingredient in ingredients_list:
        h_size_mb = ingredient.stat().st_size / (1024 * 1024)
        click.echo(f"  - {ingredient.name} ({h_size_mb:.1f} MB)")


def _show_total_freed(dry_run: bool, total_freed: int) -> None:
    """Show total space freed if not a dry run."""
    if not dry_run and total_freed > 0:
        freed_mb = total_freed / (1024 * 1024)
        click.secho(f"\n💾 Total freed: {freed_mb:.1f} MB", fg="green")
