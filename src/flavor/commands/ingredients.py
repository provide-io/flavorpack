#!/usr/bin/env python3
#
# flavor/commands/ingredients.py
#
"""Ingredient management commands for the flavor CLI."""

import os
from pathlib import Path

import click
from provide.foundation.process import run

from flavor.console import echo, echo_error, get_command_logger

# Get structured logger for ingredient commands
log = get_command_logger("ingredients")


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
        echo("No ingredients found. Build them with: flavor ingredients build")
        return

    echo("🔧 Available Flavor Ingredients")
    echo("=" * 60)

    # Ingredient function to get version
    def get_version(ingredient_path: Path) -> str | None:
        try:
            result = run(
                [str(ingredient_path), "--version"],
                capture_output=True,
                check=False,
                timeout=2,
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
        echo("\n📦 Launchers:")
        launchers = sorted(ingredients["launchers"], key=lambda h: h.name)
        for i, launcher in enumerate(launchers):
            if i > 0:
                echo("")  # Add newline between entries
            size_mb = launcher.size / (1024 * 1024)
            version = get_version(launcher.path) or launcher.version or "unknown"
            echo(f"  • {launcher.name} ({launcher.language}, {size_mb:.1f} MB) - {version}")
            echo(f"    Path: {launcher.path}")
            if launcher.checksum:
                echo(f"    SHA256: {launcher.checksum}")
            if verbose and launcher.built_from:
                echo(f"    Source: {launcher.built_from}")

    if ingredients["builders"]:
        echo("\n🔨 Builders:")
        builders = sorted(ingredients["builders"], key=lambda h: h.name)
        for i, builder in enumerate(builders):
            if i > 0:
                echo("")  # Add newline between entries
            size_mb = builder.size / (1024 * 1024)
            version = get_version(builder.path) or builder.version or "unknown"
            echo(f"  • {builder.name} ({builder.language}, {size_mb:.1f} MB) - {version}")
            echo(f"    Path: {builder.path}")
            if builder.checksum:
                echo(f"    SHA256: {builder.checksum}")
            if verbose and builder.built_from:
                echo(f"    Source: {builder.built_from}")


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

    echo(f"🔨 Building {lang} ingredients...")

    built = manager.build_ingredients(language=language, force=force)

    if built:
        echo(f"✅ Built {len(built)} ingredient(s):")
        for path in built:
            size_mb = path.stat().st_size / (1024 * 1024)
            echo(f"  • {path.name} ({size_mb:.1f} MB)")
    else:
        echo("⚠️  No ingredients were built")
        echo("Make sure you have the required compilers installed:")
        echo("  • Go: go version")
        echo("  • Rust: cargo --version")


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
        echo("Aborted.")
        return

    language = None if lang == "all" else lang

    removed = manager.clean_ingredients(language=language)

    if removed:
        echo(f"✅ Removed {len(removed)} ingredient(s):")
        for path in removed:
            echo(f"  • {path.name}")
    else:
        echo("No ingredients to remove")


@ingredient_group.command("info")
@click.argument("name")
def ingredient_info(name: str) -> None:
    """Show detailed information about a specific ingredient."""
    from flavor.ingredients.manager import IngredientManager

    manager = IngredientManager()
    info = manager.get_ingredient_info(name)

    if not info:
        echo_error(f"❌ Ingredient '{name}' not found")
        return

    echo(f"🔧 Ingredient Information: {info.name}")
    echo("=" * 60)
    echo(f"Type: {info.type}")
    echo(f"Language: {info.language}")
    echo(f"Path: {info.path}")
    echo(f"Size: {info.size / (1024 * 1024):.1f} MB")

    if info.version:
        echo(f"Version: {info.version}")

    if info.checksum:
        echo(f"Checksum: {info.checksum}")

    if info.built_from:
        echo(f"Source: {info.built_from}")
        if info.built_from.exists():
            echo("  ✅ Source directory exists")
        else:
            echo("  ⚠️  Source directory not found")

    # Check if executable
    if info.path.exists():
        if os.access(info.path, os.X_OK):
            echo("Status: ✅ Executable")
        else:
            echo("Status: ❌ Not executable")
    else:
        echo("Status: ❌ File not found")


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

    echo(f"🧪 Testing {lang} ingredients...")

    results = manager.test_ingredients(language=language)

    # Show results
    if results["passed"]:
        echo(f"✅ Passed: {len(results['passed'])}")
        for name in results["passed"]:
            echo(f"  • {name}")

    if results["failed"]:
        echo_error(f"❌ Failed: {len(results['failed'])}")
        for failure in results["failed"]:
            echo(f"  • {failure['name']}: {failure['error']}")
            if failure.get("stderr"):
                echo(f"    {failure['stderr']}")

    if results["skipped"]:
        echo(f"⏭️  Skipped: {len(results['skipped'])}")
        for name in results["skipped"]:
            echo(f"  • {name}")

    # Overall status
    if results["failed"]:
        echo_error("\n❌ Some tests failed")
        raise click.Abort()
    elif results["passed"]:
        echo("\n✅ All tests passed")
    else:
        echo("\n⚠️  No tests were run")
