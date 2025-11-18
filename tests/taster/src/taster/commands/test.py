#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test management commands for Flavor"""

from pathlib import Path
import subprocess
import sys
from typing import Any

import click
from click.testing import CliRunner
from provide.foundation.console import perr, pout


def _get_flavor_api() -> Any | None:
    """Get the Flavor API."""
    try:
        sys.path.insert(0, str(Path(__file__).parents[4] / "src"))
        import flavor.api as flavor_api

        return flavor_api
    except ImportError:
        return None


@click.group("test")
def test_command() -> None:
    pass


@test_command.command("suite")
@click.pass_context
def test_suite(ctx: click.Context) -> None:
    """Run taster's built-in test suite"""
    from .argv import argv_command
    from .env import env_command
    from .features import features_command
    from .info import info_command

    pout("=" * 60, color="cyan", bold=True)
    pout("=" * 60, color="cyan", bold=True)

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
        pout(f"\n{'=' * 60}", color="blue")
        pout(f"Running: {name}", color="blue", bold=True)
        pout("=" * 60, color="blue")

        # Run the command
        result = runner.invoke(command)

        # Check result
        if result.exit_code == 0:
            results.append((name, True))
        else:
            pout(f"❌ {name}: FAILED", color="red")
            results.append((name, False))
            if result.exception:
                pout(f"  Error: {result.exception}")

        # Show output
        if result.output:
            for line in result.output.split("\n")[:10]:  # First 10 lines
                if line.strip():
                    pout(f"  {line}")

    # Summary
    pout(f"\n{'=' * 60}", color="cyan", bold=True)
    pout("📊 TEST SUMMARY", color="cyan", bold=True)
    pout("=" * 60, color="cyan", bold=True)

    passed = sum(1 for _, success in results if success)
    total = len(results)
    percentage = (passed / total * 100) if total > 0 else 0

    pout(f"\nTests Passed: {passed}/{total} ({percentage:.1f}%)")

    # List results
    for name, success in results:
        symbol = "✅" if success else "❌"
        pout(f"  {symbol} {name}")

    # Overall result
    if passed == total:
        ctx.exit(0)
    else:
        pout(f"\n❌ {total - passed} TEST(S) FAILED", fg="red", bold=True)
        ctx.exit(1)


@test_command.command("flavor")
@click.option("--coverage", is_flag=True, help="Run with coverage")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def test_flavor(coverage: bool, verbose: bool) -> None:
    """Run Flavor's test suite"""
    flavor_root = Path(__file__).parents[4]
    pytest_cmd = flavor_root / "workenv" / "flavor_darwin_arm64" / "bin" / "pytest"

    if not pytest_cmd.exists():
        perr("Error: pytest not found in workenv")
        sys.exit(1)

    args = [str(pytest_cmd), "tests/", "tests/taster/tests"]

    if coverage:
        args.extend(["--cov=src/flavor", "--cov-report=term-missing"])

    if not verbose:
        args.append("-q")

    pout(f"Running: {' '.join(args)}")
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


# 🌶️📦🔚
