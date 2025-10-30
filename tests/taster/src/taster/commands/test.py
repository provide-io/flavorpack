#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test management commands for Flavor"""

from pathlib import Path
import subprocess
import sys

import click
from click.testing import CliRunner


def _get_flavor_api():
    """Get the Flavor API."""
    try:
        sys.path.insert(0, str(Path(__file__).parents[4] / "src"))
        import flavor.api as flavor_api

        return flavor_api
    except ImportError:
        return None


@click.group("test")
def test_command() -> None:
    """🧪 Test management for Flavor"""
    pass


@test_command.command("suite")
@click.pass_context
def test_suite(ctx) -> None:
    """Run taster's built-in test suite"""
    from .argv import argv_command
    from .env import env_command
    from .features import features_command
    from .info import info_command

    click.secho("=" * 60, fg="cyan", bold=True)
    click.secho("🧪 RUNNING TASTER TEST SUITE", fg="cyan", bold=True)
    click.secho("=" * 60, fg="cyan", bold=True)

    # List of commands to run
    commands = [
        ("Environment Variables", env_command),
        ("argv[0] and Command", argv_command),
        ("System Information", info_command),
        ("Feature Parity", features_command),
    ]

    results = []
    runner = CliRunner()

    for name, command in commands:
        click.secho(f"\n{'=' * 60}", fg="blue")
        click.secho(f"Running: {name}", fg="blue", bold=True)
        click.secho("=" * 60, fg="blue")

        # Run the command
        result = runner.invoke(command)

        # Check result
        if result.exit_code == 0:
            click.secho(f"✅ {name}: PASSED", fg="green")
            results.append((name, True))
        else:
            click.secho(f"❌ {name}: FAILED", fg="red")
            results.append((name, False))
            if result.exception:
                click.echo(f"  Error: {result.exception}")

        # Show output
        if result.output:
            for line in result.output.split("\n")[:10]:  # First 10 lines
                if line.strip():
                    click.echo(f"  {line}")

    # Summary
    click.secho(f"\n{'=' * 60}", fg="cyan", bold=True)
    click.secho("📊 TEST SUMMARY", fg="cyan", bold=True)
    click.secho("=" * 60, fg="cyan", bold=True)

    passed = sum(1 for _, success in results if success)
    total = len(results)
    percentage = (passed / total * 100) if total > 0 else 0

    click.echo(f"\nTests Passed: {passed}/{total} ({percentage:.1f}%)")

    # List results
    for name, success in results:
        symbol = "✅" if success else "❌"
        click.echo(f"  {symbol} {name}")

    # Overall result
    if passed == total:
        click.secho("\n✅ ALL TESTS PASSED!", fg="green", bold=True)
        ctx.exit(0)
    else:
        click.secho(f"\n❌ {total - passed} TEST(S) FAILED", fg="red", bold=True)
        ctx.exit(1)


@test_command.command("flavor")
@click.option("--coverage", is_flag=True, help="Run with coverage")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def test_flavor(coverage, verbose) -> None:
    """Run Flavor's test suite"""
    flavor_root = Path(__file__).parents[4]
    pytest_cmd = flavor_root / "workenv" / "flavor_darwin_arm64" / "bin" / "pytest"

    if not pytest_cmd.exists():
        click.echo("Error: pytest not found in workenv", err=True)
        sys.exit(1)

    args = [str(pytest_cmd), "tests/", "tests/taster/tests"]

    if coverage:
        args.extend(["--cov=src/flavor", "--cov-report=term-missing"])

    if not verbose:
        args.append("-q")

    click.echo(f"Running: {' '.join(args)}")
    result = subprocess.run(args, cwd=flavor_root)
    sys.exit(result.returncode)


@test_command.command("clean")
def clean() -> None:
    """Clean test artifacts and caches"""
    flavor_root = Path(__file__).parents[4]

    # Clean Python cache
    subprocess.run(
        [
            "find",
            ".",
            "-type",
            "d",
            "-name",
            "__pycache__",
            "-exec",
            "rm",
            "-rf",
            "{}",
            "+",
        ],
        cwd=flavor_root,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["find", ".", "-name", "*.pyc", "-delete"],
        cwd=flavor_root,
        stderr=subprocess.DEVNULL,
    )

    # Clean test artifacts
    artifacts = [".pytest_cache", ".coverage", "reports"]
    for artifact in artifacts:
        subprocess.run(["rm", "-rf", artifact], cwd=flavor_root)

    # Clean Flavor cache using API
    flavor_api = _get_flavor_api()
    if flavor_api:
        flavor_api.clean_cache()
        click.echo("✅ Cleaned Flavor cache")

    click.echo("✅ Cleaned test artifacts")

# 🌶️📦🔚
