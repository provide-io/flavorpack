#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Security feature tests: SBOM, provenance, policy, and trust."""

from __future__ import annotations

import subprocess
import sys

import click


def _package_path() -> str:
    """Return the path to the current package (this executable)."""
    return sys.argv[0]


def _run_flavor(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run the flavor CLI with the given arguments."""
    return subprocess.run(["flavor", *args], capture_output=True, text=True)


@click.group("security")
def security_group() -> None:
    """Security feature tests: SBOM, provenance, policy, and trust."""


@security_group.command("inspect-sbom")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def inspect_sbom(output_json: bool) -> None:
    """Run 'flavor inspect --sbom' on this package."""
    pkg = _package_path()
    cmd = ["inspect", "--sbom", pkg]
    if output_json:
        cmd.append("--json")
    result = _run_flavor(cmd)
    if result.stdout:
        click.echo(result.stdout, nl=False)
    if result.stderr:
        click.echo(result.stderr, nl=False, err=True)
    sys.exit(result.returncode)


@security_group.command("inspect-provenance")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def inspect_provenance(output_json: bool) -> None:
    """Run 'flavor inspect --provenance' on this package."""
    pkg = _package_path()
    cmd = ["inspect", "--provenance", pkg]
    if output_json:
        cmd.append("--json")
    result = _run_flavor(cmd)
    if result.stdout:
        click.echo(result.stdout, nl=False)
    if result.stderr:
        click.echo(result.stderr, nl=False, err=True)
    sys.exit(result.returncode)


@security_group.command("policy-check")
def policy_check() -> None:
    """Run 'flavor policy check' on this package."""
    pkg = _package_path()
    result = _run_flavor(["policy", "check", pkg])
    if result.stdout:
        click.echo(result.stdout, nl=False)
    if result.stderr:
        click.echo(result.stderr, nl=False, err=True)
    sys.exit(result.returncode)


@security_group.command("trust-list")
def trust_list() -> None:
    """Run 'flavor trust list'."""
    result = _run_flavor(["trust", "list"])
    if result.stdout:
        click.echo(result.stdout, nl=False)
    if result.stderr:
        click.echo(result.stderr, nl=False, err=True)
    sys.exit(result.returncode)


@security_group.command("all")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def run_all(output_json: bool) -> None:
    """Run all security checks and report results."""
    pkg = _package_path()

    checks: list[tuple[str, list[str]]] = [
        ("inspect-sbom", ["inspect", "--sbom", pkg]),
        ("inspect-provenance", ["inspect", "--provenance", pkg]),
        ("policy-check", ["policy", "check", pkg]),
        ("trust-list", ["trust", "list"]),
    ]

    results: list[tuple[str, bool]] = []
    for name, args in checks:
        proc = _run_flavor(args)
        results.append((name, proc.returncode == 0))

    all_passed = all(passed for _, passed in results)

    click.echo("Security Check Results:")
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        click.echo(f"  {name:<22} {status}")

    sys.exit(0 if all_passed else 1)


# 🌶️📦🔚
