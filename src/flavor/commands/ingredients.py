#!/usr/bin/env python3
#
# flavor/commands/ingredients.py
#
"""Ingredient management commands for the flavor CLI."""

import os

import click

from flavor.utils.subprocess import run_command


@click.group("ingredients")
def ingredient_group() -> None:
    """Manage Flavor ingredient binaries (launchers and builders)."""
    pass


@ingredient_group.command("list")
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed information",
)
def ingredient_list(verbose: bool) -> None:
    """List available ingredient binaries."""
    from flavor.ingredients.manager import IngredientManager

    manager = IngredientManager()
    ingredients = manager.list_ingredients()

    if not ingredients["launchers"] and not ingredients["builders"]:
        click.echo("No ingredients found. Build them with: flavor ingredients build")
        return

    click.echo("🔧 Available Flavor Ingredients")
    click.echo("=" * 60)

    # Ingredient function to get version
    def get_version(ingredient_path):
        try:
            result = run_command(
                [str(ingredient_path), "--version"],
                capture_output=True,
                check=False,
                timeout=2,
                log_command=False,
            )
            if result.returncode == 0:
                # Parse version from output (first line usually)
                lines = result.stdout.strip().split("\n")
                if lines:
                    return lines[0]
        except Exception:
            pass
        return None

    if ingredients["launchers"]:
        click.echo("\n📦 Launchers:")
        launchers = sorted(ingredients["launchers"], key=lambda h: h.name)
        for i, launcher in enumerate(launchers):
            if i > 0:
                click.echo()  # Add newline between entries
            size_mb = launcher.size / (1024 * 1024)
            version = get_version(launcher.path) or launcher.version or "unknown"
            click.echo(
                f"  • {launcher.name} ({launcher.language}, {size_mb:.1f} MB) - {version}"
            )
            click.echo(f"    Path: {launcher.path}")
            if launcher.checksum:
                click.echo(f"    SHA256: {launcher.checksum}")
            if verbose:
                if launcher.built_from:
                    click.echo(f"    Source: {launcher.built_from}")

    if ingredients["builders"]:
        click.echo("\n🔨 Builders:")
        builders = sorted(ingredients["builders"], key=lambda h: h.name)
        for i, builder in enumerate(builders):
            if i > 0:
                click.echo()  # Add newline between entries
            size_mb = builder.size / (1024 * 1024)
            version = get_version(builder.path) or builder.version or "unknown"
            click.echo(
                f"  • {builder.name} ({builder.language}, {size_mb:.1f} MB) - {version}"
            )
            click.echo(f"    Path: {builder.path}")
            if builder.checksum:
                click.echo(f"    SHA256: {builder.checksum}")
            if verbose:
                if builder.built_from:
                    click.echo(f"    Source: {builder.built_from}")


@ingredient_group.command("build")
@click.option(
    "--lang",
    type=click.Choice(["go", "rust", "all"], case_sensitive=False),
    default="all",
    help="Language to build ingredients for (default: all)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force rebuild even if binaries exist",
)
def ingredient_build(lang: str, force: bool) -> None:
    """Build ingredient binaries from source."""
    from flavor.ingredients.manager import IngredientManager

    manager = IngredientManager()

    language = None if lang == "all" else lang

    click.echo(f"🔨 Building {lang} ingredients...")

    built = manager.build_ingredients(language=language, force=force)

    if built:
        click.secho(f"✅ Built {len(built)} ingredient(s):", fg="green")
        for path in built:
            size_mb = path.stat().st_size / (1024 * 1024)
            click.echo(f"  • {path.name} ({size_mb:.1f} MB)")
    else:
        click.secho("⚠️  No ingredients were built", fg="yellow")
        click.echo("Make sure you have the required compilers installed:")
        click.echo("  • Go: go version")
        click.echo("  • Rust: cargo --version")


@ingredient_group.command("clean")
@click.option(
    "--lang",
    type=click.Choice(["go", "rust", "all"], case_sensitive=False),
    default="all",
    help="Language to clean ingredients for (default: all)",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def ingredient_clean(lang: str, yes: bool) -> None:
    """Remove built ingredient binaries."""
    from flavor.ingredients.manager import IngredientManager

    manager = IngredientManager()

    if not yes and not click.confirm(f"Remove {lang} ingredient binaries?"):
        click.echo("Aborted.")
        return

    language = None if lang == "all" else lang

    removed = manager.clean_ingredients(language=language)

    if removed:
        click.secho(f"✅ Removed {len(removed)} ingredient(s):", fg="green")
        for path in removed:
            click.echo(f"  • {path.name}")
    else:
        click.echo("No ingredients to remove")


@ingredient_group.command("info")
@click.argument("name")
def ingredient_info(name: str) -> None:
    """Show detailed information about a specific ingredient."""
    from flavor.ingredients.manager import IngredientManager

    manager = IngredientManager()
    info = manager.get_ingredient_info(name)

    if not info:
        click.secho(f"❌ Ingredient '{name}' not found", fg="red")
        return

    click.echo(f"🔧 Ingredient Information: {info.name}")
    click.echo("=" * 60)
    click.echo(f"Type: {info.type}")
    click.echo(f"Language: {info.language}")
    click.echo(f"Path: {info.path}")
    click.echo(f"Size: {info.size / (1024 * 1024):.1f} MB")

    if info.version:
        click.echo(f"Version: {info.version}")

    if info.checksum:
        click.echo(f"Checksum: {info.checksum}")

    if info.built_from:
        click.echo(f"Source: {info.built_from}")
        if info.built_from.exists():
            click.echo("  ✅ Source directory exists")
        else:
            click.echo("  ⚠️  Source directory not found")

    # Check if executable
    if info.path.exists():
        if os.access(info.path, os.X_OK):
            click.echo("Status: ✅ Executable")
        else:
            click.echo("Status: ❌ Not executable")
    else:
        click.echo("Status: ❌ File not found")


@ingredient_group.command("test")
@click.option(
    "--lang",
    type=click.Choice(["go", "rust", "all"], case_sensitive=False),
    default="all",
    help="Language to test ingredients for (default: all)",
)
def ingredient_test(lang: str) -> None:
    """Test ingredient binaries."""
    from flavor.ingredients.manager import IngredientManager

    manager = IngredientManager()

    language = None if lang == "all" else lang

    click.echo(f"🧪 Testing {lang} ingredients...")

    results = manager.test_ingredients(language=language)

    # Show results
    if results["passed"]:
        click.secho(f"✅ Passed: {len(results['passed'])}", fg="green")
        for name in results["passed"]:
            click.echo(f"  • {name}")

    if results["failed"]:
        click.secho(f"❌ Failed: {len(results['failed'])}", fg="red")
        for failure in results["failed"]:
            click.echo(f"  • {failure['name']}: {failure['error']}")
            if failure.get("stderr"):
                click.echo(f"    {failure['stderr']}")

    if results["skipped"]:
        click.echo(f"⏭️  Skipped: {len(results['skipped'])}")
        for name in results["skipped"]:
            click.echo(f"  • {name}")

    # Overall status
    if results["failed"]:
        click.secho("\n❌ Some tests failed", fg="red")
        raise click.Abort()
    elif results["passed"]:
        click.secho("\n✅ All tests passed", fg="green")
    else:
        click.echo("\n⚠️  No tests were run")
