#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Helper management commands for the flavor CLI."""

from __future__ import annotations

import os
from pathlib import Path

import click
from provide.foundation.console import perr, pout
from provide.foundation.process import run

from flavor.console import get_command_logger

# Get structured logger for helper commands
log = get_command_logger("helpers")


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
def helper_list(verbose: bool) -> None:  # noqa: C901
    """List available helper binaries."""
    from flavor.helpers.manager import HelperManager

    manager = HelperManager()
    helpers = manager.list_helpers()

    if not helpers["launchers"] and not helpers["builders"]:
        pout("No helpers found. Build them with: flavor helpers build")
        return

    pout("🔧 Available Flavor Helpers")
    pout("=" * 60)

    # Helper function to get version
    def get_version(helper_path: Path) -> str | None:
        try:
            result = run(
                [str(helper_path), "--version"],
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

    if helpers["launchers"]:
        pout("\n📦 Launchers:")
        launchers = sorted(helpers["launchers"], key=lambda h: h.name)
        for i, launcher in enumerate(launchers):
            if i > 0:
                pout("")  # Add newline between entries
            size_mb = launcher.size / (1024 * 1024)
            version = get_version(launcher.path) or launcher.version or "unknown"
            pout(f"  • {launcher.name} ({launcher.language}, {size_mb:.1f} MB) - {version}")
            pout(f"    Path: {launcher.path}")
            if launcher.checksum:
                pout(f"    SHA256: {launcher.checksum}")
            if verbose and launcher.built_from:
                pout(f"    Source: {launcher.built_from}")

    if helpers["builders"]:
        pout("\n🔨 Builders:")
        builders = sorted(helpers["builders"], key=lambda h: h.name)
        for i, builder in enumerate(builders):
            if i > 0:
                pout("")  # Add newline between entries
            size_mb = builder.size / (1024 * 1024)
            version = get_version(builder.path) or builder.version or "unknown"
            pout(f"  • {builder.name} ({builder.language}, {size_mb:.1f} MB) - {version}")
            pout(f"    Path: {builder.path}")
            if builder.checksum:
                pout(f"    SHA256: {builder.checksum}")
            if verbose and builder.built_from:
                pout(f"    Source: {builder.built_from}")


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
    from flavor.helpers.manager import HelperManager

    manager = HelperManager()

    language = None if lang == "all" else lang

    pout(f"🔨 Building {lang} helpers...")

    built = manager.build_helpers(language=language, force=force)

    if built:
        pout(f"✅ Built {len(built)} helper(s):")
        for path in built:
            size_mb = path.stat().st_size / (1024 * 1024)
            pout(f"  • {path.name} ({size_mb:.1f} MB)")
    else:
        pout("⚠️  No helpers were built")
        pout("Make sure you have the required compilers installed:")
        pout("  • Go: go version")
        pout("  • Rust: cargo --version")


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
    from flavor.helpers.manager import HelperManager

    manager = HelperManager()

    if not yes and not click.confirm(f"Remove {lang} helper binaries?"):
        pout("Aborted.")
        return

    language = None if lang == "all" else lang

    removed = manager.clean_helpers(language=language)

    if removed:
        pout(f"✅ Removed {len(removed)} helper(s):")
        for path in removed:
            pout(f"  • {path.name}")
    else:
        pout("No helpers to remove")


@helper_group.command("info")
@click.argument("name")
def helper_info(name: str) -> None:
    """Show detailed information about a specific helper."""
    from flavor.helpers.manager import HelperManager

    manager = HelperManager()
    info = manager.get_helper_info(name)

    if not info:
        perr(f"❌ Helper '{name}' not found")
        return

    pout(f"🔧 Helper Information: {info.name}")
    pout("=" * 60)
    pout(f"Type: {info.type}")
    pout(f"Language: {info.language}")
    pout(f"Path: {info.path}")
    pout(f"Size: {info.size / (1024 * 1024):.1f} MB")

    if info.version:
        pout(f"Version: {info.version}")

    if info.checksum:
        pout(f"Checksum: {info.checksum}")

    if info.built_from:
        pout(f"Source: {info.built_from}")
        if info.built_from.exists():
            pout("  ✅ Source directory exists")
        else:
            pout("  ⚠️  Source directory not found")

    # Check if executable
    if info.path.exists():
        if os.access(info.path, os.X_OK):
            pass
        else:
            pout("Status: ❌ Not executable")
    else:
        pout("Status: ❌ File not found")


@helper_group.command("test")
@click.option(
    "--lang",
    type=click.Choice(["go", "rust", "all"], case_sensitive=False),
    default="all",
    help="Language to test helpers for (default: all)",
)
def helper_test(lang: str) -> None:
    """Test helper binaries."""
    from flavor.helpers.manager import HelperManager

    manager = HelperManager()

    language = None if lang == "all" else lang

    pout(f"🧪 Testing {lang} helpers...")

    results = manager.test_helpers(language=language)

    # Show results
    if results["passed"]:
        pout(f"✅ Passed: {len(results['passed'])}")
        for name in results["passed"]:
            pout(f"  • {name}")

    if results["failed"]:
        perr(f"❌ Failed: {len(results['failed'])}")
        for failure in results["failed"]:
            pout(f"  • {failure['name']}: {failure['error']}")
            if failure.get("stderr"):
                pout(f"    {failure['stderr']}")

    if results["skipped"]:
        pout(f"⏭️  Skipped: {len(results['skipped'])}")
        for name in results["skipped"]:
            pout(f"  • {name}")

    # Overall status
    if results["failed"]:
        perr("\n❌ Some tests failed")
        raise click.Abort()
    elif results["passed"]:
        pout("\n✅ All tests passed")
    else:
        pout("\n⚠️  No tests were run")


# 🌶️📦🔚
