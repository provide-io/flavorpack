#!/usr/bin/env python3
#
# flavor/commands/utils.py
#
"""Utility commands for the flavor CLI."""

from pathlib import Path

import click


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
    from flavor.cache import CacheManager

    # Determine what to clean
    clean_workenv = not ingredients or all
    clean_ingredients = ingredients or all

    if dry_run:
        click.echo("🔍 DRY RUN - Nothing will be removed\n")

    total_freed = 0

    # Clean workenv
    if clean_workenv:
        manager = CacheManager()
        cached = manager.list_cached()

        if cached:
            size = manager.get_cache_size()
            size_mb = size / (1024 * 1024)

            if dry_run:
                click.echo(
                    f"Would remove {len(cached)} cached packages ({size_mb:.1f} MB):"
                )
                for pkg in cached:
                    pkg_size_mb = pkg["size"] / (1024 * 1024)
                    name = pkg.get("name", pkg["id"])
                    click.echo(f"  - {name} ({pkg_size_mb:.1f} MB)")
            else:
                if not yes and not click.confirm(
                    f"Remove {len(cached)} cached packages ({size_mb:.1f} MB)?"
                ):
                    click.echo("Aborted.")
                    return

                removed = manager.clean()
                if removed:
                    click.secho(
                        f"✅ Removed {len(removed)} cached packages", fg="green"
                    )
                    total_freed += size

    # Clean ingredients
    if clean_ingredients:
        ingredient_dir = Path.home() / ".cache" / "flavor" / "bin"
        if ingredient_dir.exists():
            ingredients_list = list(ingredient_dir.glob("flavor-*"))
            ingredients_list = [
                h for h in ingredients_list if h.suffix != ".d"
            ]  # Skip .d files

            if ingredients_list:
                total_size = sum(h.stat().st_size for h in ingredients_list)
                size_mb = total_size / (1024 * 1024)

                if dry_run:
                    click.echo(
                        f"\nWould remove {len(ingredients_list)} ingredient binaries ({size_mb:.1f} MB):"
                    )
                    for ingredient in ingredients_list:
                        h_size_mb = ingredient.stat().st_size / (1024 * 1024)
                        click.echo(f"  - {ingredient.name} ({h_size_mb:.1f} MB)")
                else:
                    if not yes and not click.confirm(
                        f"Remove {len(ingredients_list)} ingredient binaries ({size_mb:.1f} MB)?"
                    ):
                        click.echo("Aborted.")
                        return

                    import shutil

                    shutil.rmtree(ingredient_dir)
                    click.secho(
                        f"✅ Removed {len(ingredients_list)} ingredient binaries",
                        fg="green",
                    )
                    total_freed += total_size

    if not dry_run and total_freed > 0:
        freed_mb = total_freed / (1024 * 1024)
        click.secho(f"\n💾 Total freed: {freed_mb:.1f} MB", fg="green")


