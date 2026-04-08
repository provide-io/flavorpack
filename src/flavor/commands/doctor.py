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


@click.command("doctor")
def doctor_command() -> None:  # noqa: C901
    """Check Flavorpack installation health and report findings."""

    errors: list[str] = []
    warnings: list[str] = []

    pout("Flavorpack Doctor")
    pout("=================")
    pout("")

    # --- Python version ---
    py_version = sys.version.split()[0]
    major, minor = sys.version_info.major, sys.version_info.minor
    if major < 3 or (major == 3 and minor < 11):
        py_status = "WARN"
        warnings.append(f"Python {py_version} is below the required 3.11")
    else:
        py_status = "OK"
    py_marker = "OK" if py_status == "OK" else "WARN"
    pout(f"Python:        {py_version} [{py_marker}]")

    # --- Flavorpack version ---
    pout(f"Flavorpack:    {flavor_version}")

    # --- Platform ---
    arch = platform.machine()
    pout(f"Platform:      {sys.platform} {arch}")
    pout("")

    # --- Helper binaries ---
    pout("Helpers:")
    manager = HelperManager()
    helpers = manager.list_helpers()
    all_helpers = helpers.get("launchers", []) + helpers.get("builders", [])

    if not all_helpers:
        pout("  (none found)")
        warnings.append("No helper binaries found — run: flavor helpers build")
    else:
        for helper in sorted(all_helpers, key=lambda h: h.name):
            exists = helper.path.exists()
            executable = exists and os.access(helper.path, os.X_OK)
            size_mb = helper.size / (1024 * 1024) if helper.size else 0
            version_str = helper.version or "unknown"

            if not exists:
                status = "MISSING"
                errors.append(f"Helper {helper.name} not found at {helper.path}")
            elif not executable:
                status = "NOT-EXEC"
                errors.append(f"Helper {helper.name} is not executable")
            else:
                status = "OK"

            pout(f"  {helper.name:<40} [{status}]  {version_str}  ({size_mb:.1f} MB)")

    pout("")

    # --- Directories ---
    pout("Directories:")

    # Cache dir
    cache_dir = get_cache_dir()
    cache_exists = cache_dir.exists()
    cache_writable = cache_exists and os.access(cache_dir, os.W_OK)
    if not cache_exists:
        cache_note = "(not created yet)"
    elif cache_writable:
        cache_note = "writable [OK]"
    else:
        cache_note = "NOT WRITABLE [ERR]"
        errors.append(f"Cache directory not writable: {cache_dir}")
    pout(f"  Cache:        {cache_dir}  {cache_note}")

    # Config dir
    config_dir = get_config_dir()
    config_note = "[OK]" if config_dir.exists() else "(not created yet)"
    pout(f"  Config:       {config_dir}  {config_note}")

    # Trusted keys dir
    keys_dir = get_trusted_keys_dir()
    if keys_dir.exists():
        key_count = len(list(keys_dir.glob("*.pub")))
        if key_count == 0:
            keys_note = "0 keys  [WARN]"
            warnings.append("No trusted public keys found — packages cannot be signature-verified")
        else:
            keys_note = f"{key_count} key(s)  [OK]"
    else:
        keys_note = "0 keys  [WARN]  (not created yet)"
        warnings.append("Trusted keys directory does not exist — packages cannot be signature-verified")
    pout(f"  Trusted keys: {keys_dir}  {keys_note}")

    pout("")

    # --- Overall status ---
    if errors:
        perr("Overall: [ERR] Not ready")
        for msg in errors:
            perr(f"  - {msg}")
        for msg in warnings:
            pout(f"  - {msg}")
        raise SystemExit(1)
    elif warnings:
        pout("Overall: [WARN] Warnings found")
        for msg in warnings:
            pout(f"  - {msg}")
    else:
        pout("Overall: [OK] Ready")


# 🌶️📦🔚
