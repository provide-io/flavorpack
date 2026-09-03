#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Diagnostic command for Flavorpack installation health checks."""

from __future__ import annotations

import os
import platform
import sys

import click
from provide.foundation.console import perr, pout

from flavor import __version__ as flavor_version
from flavor.cache import get_cache_dir
from flavor.config.dirs import get_config_dir, get_trusted_keys_dir
from flavor.console import get_command_logger
from flavor.helpers.manager import HelperManager

log = get_command_logger("doctor")


# Each check prints its own section and returns what it found, so the command
# below reads as the list of things being checked.
Findings = tuple[list[str], list[str]]  # (errors, warnings)


def _check_python_version() -> Findings:
    """Report the interpreter, warning below the version the project needs."""
    py_version = sys.version.split()[0]
    major, minor = sys.version_info.major, sys.version_info.minor

    warnings: list[str] = []
    marker = "OK"
    if major < 3 or (major == 3 and minor < 11):
        marker = "WARN"
        warnings.append(f"Python {py_version} is below the required 3.11")

    pout(f"Python:        {py_version} [{marker}]")
    return [], warnings


def _report_versions() -> None:
    """Print what this installation is, which fixes nothing but frames the rest."""
    pout(f"Flavorpack:    {flavor_version}")
    pout(f"Platform:      {sys.platform} {platform.machine()}")
    pout("")


def _check_one_helper(helper: object) -> tuple[str, list[str]]:
    """Classify one helper binary. Returns (status, errors)."""
    path = helper.path  # type: ignore[attr-defined]
    name = helper.name  # type: ignore[attr-defined]

    if not path.exists():
        return "MISSING", [f"Helper {name} not found at {path}"]
    if not os.access(path, os.X_OK):
        return "NOT-EXEC", [f"Helper {name} is not executable"]
    return "OK", []


def _check_helpers() -> Findings:
    """Report every helper binary this installation can find."""
    pout("Helpers:")

    helpers = HelperManager().list_helpers()
    all_helpers = helpers.get("launchers", []) + helpers.get("builders", [])

    if not all_helpers:
        pout("  (none found)")
        pout("")
        return [], ["No helper binaries found — run: flavor helpers build"]

    errors: list[str] = []
    for helper in sorted(all_helpers, key=lambda h: h.name):
        status, helper_errors = _check_one_helper(helper)
        errors.extend(helper_errors)
        size_mb = helper.size / (1024 * 1024) if helper.size else 0
        pout(f"  {helper.name:<40} [{status}]  {helper.version or 'unknown'}  ({size_mb:.1f} MB)")

    pout("")
    return errors, []


def _check_cache_dir() -> Findings:
    """A cache directory that exists but cannot be written stops every build."""
    cache_dir = get_cache_dir()

    errors: list[str] = []
    if not cache_dir.exists():
        note = "(not created yet)"
    elif os.access(cache_dir, os.W_OK):
        note = "writable [OK]"
    else:
        note = "NOT WRITABLE [ERR]"
        errors.append(f"Cache directory not writable: {cache_dir}")

    pout(f"  Cache:        {cache_dir}  {note}")
    return errors, []


def _check_trusted_keys_dir() -> Findings:
    """No trusted keys means no package can be signature-verified."""
    keys_dir = get_trusted_keys_dir()

    warnings: list[str] = []
    if not keys_dir.exists():
        note = "0 keys  [WARN]  (not created yet)"
        warnings.append("Trusted keys directory does not exist — packages cannot be signature-verified")
    elif (key_count := len(list(keys_dir.glob("*.pub")))) == 0:
        note = "0 keys  [WARN]"
        warnings.append("No trusted public keys found — packages cannot be signature-verified")
    else:
        note = f"{key_count} key(s)  [OK]"

    pout(f"  Trusted keys: {keys_dir}  {note}")
    return [], warnings


def _check_directories() -> Findings:
    """Report the three directories a working installation needs."""
    pout("Directories:")

    cache_errors, cache_warnings = _check_cache_dir()

    config_dir = get_config_dir()
    pout(f"  Config:       {config_dir}  {'[OK]' if config_dir.exists() else '(not created yet)'}")

    key_errors, key_warnings = _check_trusted_keys_dir()

    pout("")
    return cache_errors + key_errors, cache_warnings + key_warnings


def _report_overall(errors: list[str], warnings: list[str]) -> None:
    """State the verdict, and exit non-zero when the installation cannot work.

    Errors exit 1 so a script can act on the result; warnings do not, because
    the installation still runs.
    """
    if errors:
        perr("Overall: [ERR] Not ready")
        for msg in errors:
            perr(f"  - {msg}")
        for msg in warnings:
            pout(f"  - {msg}")
        raise SystemExit(1)

    if warnings:
        pout("Overall: [WARN] Warnings found")
        for msg in warnings:
            pout(f"  - {msg}")
        return

    pout("Overall: [OK] Ready")


@click.command("doctor")
def doctor_command() -> None:
    """Check Flavorpack installation health and report findings."""
    pout("Flavorpack Doctor")
    pout("=================")
    pout("")

    python_errors, python_warnings = _check_python_version()
    _report_versions()
    helper_errors, helper_warnings = _check_helpers()
    dir_errors, dir_warnings = _check_directories()

    _report_overall(
        python_errors + helper_errors + dir_errors,
        python_warnings + helper_warnings + dir_warnings,
    )


# 🌶️📦🔚
