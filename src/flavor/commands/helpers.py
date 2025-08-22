#!/usr/bin/env python3
#
# flavor/commands/helpers.py
#
"""Helper management commands for the flavor CLI."""

import os

import click

from flavor.utils.subprocess import run_command


@click.group("helpers")
def helper_group() -> None:
    """Manage Flavor helper binaries (launchers and builders)."""
    pass


@helper_group.command("list")
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed information",
)
def helper_list(verbose: bool) -> None:
    """List available helper binaries."""
    from flavor.helpers import HelperManager

    manager = HelperManager()
    helpers = manager.list_helpers()

    if not helpers["launchers"] and not helpers["builders"]:
        click.echo("No helpers found. Build them with: flavor helpers build")
        return

    click.echo("🔧 Available Flavor Helpers")
    click.echo("=" * 60)

    # Helper function to get version
    def get_version(helper_path):
        try:
            result = run_command(
                [str(helper_path), "--version"],
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

    if helpers["launchers"]:
        click.echo("\n📦 Launchers:")
        launchers = sorted(helpers["launchers"], key=lambda h: h.name)
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

    if helpers["builders"]:
        click.echo("\n🔨 Builders:")
        builders = sorted(helpers["builders"], key=lambda h: h.name)
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


@helper_group.command("build")
@click.option(
    "--lang",
    type=click.Choice(["go", "rust", "all"], case_sensitive=False),
    default="all",
    help="Language to build helpers for (default: all)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force rebuild even if binaries exist",
)
def helper_build(lang: str, force: bool) -> None:
    """Build helper binaries from source."""
    from flavor.helpers import HelperManager

    manager = HelperManager()

    language = None if lang == "all" else lang

    click.echo(f"🔨 Building {lang} helpers...")

    built = manager.build_helpers(language=language, force=force)

    if built:
        click.secho(f"✅ Built {len(built)} helper(s):", fg="green")
        for path in built:
            size_mb = path.stat().st_size / (1024 * 1024)
            click.echo(f"  • {path.name} ({size_mb:.1f} MB)")
    else:
        click.secho("⚠️  No helpers were built", fg="yellow")
        click.echo("Make sure you have the required compilers installed:")
        click.echo("  • Go: go version")
        click.echo("  • Rust: cargo --version")


@helper_group.command("clean")
@click.option(
    "--lang",
    type=click.Choice(["go", "rust", "all"], case_sensitive=False),
    default="all",
    help="Language to clean helpers for (default: all)",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def helper_clean(lang: str, yes: bool) -> None:
    """Remove built helper binaries."""
    from flavor.helpers import HelperManager

    manager = HelperManager()

    if not yes and not click.confirm(f"Remove {lang} helper binaries?"):
        click.echo("Aborted.")
        return

    language = None if lang == "all" else lang

    removed = manager.clean_helpers(language=language)

    if removed:
        click.secho(f"✅ Removed {len(removed)} helper(s):", fg="green")
        for path in removed:
            click.echo(f"  • {path.name}")
    else:
        click.echo("No helpers to remove")


@helper_group.command("info")
@click.argument("name")
def helper_info(name: str) -> None:
    """Show detailed information about a specific helper."""
    from flavor.helpers import HelperManager

    manager = HelperManager()
    info = manager.get_helper_info(name)

    if not info:
        click.secho(f"❌ Helper '{name}' not found", fg="red")
        return

    click.echo(f"🔧 Helper Information: {info.name}")
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


@helper_group.command("test")
@click.option(
    "--lang",
    type=click.Choice(["go", "rust", "all"], case_sensitive=False),
    default="all",
    help="Language to test helpers for (default: all)",
)
def helper_test(lang: str) -> None:
    """Test helper binaries."""
    from flavor.helpers import HelperManager

    manager = HelperManager()

    language = None if lang == "all" else lang

    click.echo(f"🧪 Testing {lang} helpers...")

    results = manager.test_helpers(language=language)

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
