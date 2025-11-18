#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Environment variable testing command."""

from __future__ import annotations

from collections.abc import Mapping
import os

import click
from provide.foundation.console import pout


@click.command("env")
def env_command() -> None:
    """Inspect, categorize, and validate environment variables."""
    env_vars = dict(os.environ)
    pout("=" * 60, color="cyan")
    pout("=" * 60, color="cyan")
    pout(f"📊 Total variables: {len(env_vars)}", fg="yellow")

    categories = _categorize_env_vars(env_vars)
    _display_categories(env_vars, categories)
    _check_expected_vars(env_vars)
    _validate_mappings(env_vars)
    _run_whitelist_check(env_vars)
    _print_env_source(env_vars)


def _categorize_env_vars(env_vars: Mapping[str, str]) -> dict[str, list[str]]:
    """Bucket environment variables into high level categories."""
    categories: dict[str, list[str]] = {
        "System": [var for var in ["PATH", "HOME", "USER", "TERM", "SHELL", "PWD"] if var in env_vars],
        "Locale": [k for k in env_vars if k.startswith("LANG") or k.startswith("LC_")],
        "Flavor": [k for k in env_vars if k.startswith("FLAVOR_")],
        "Taster": [k for k in env_vars if k.startswith("TASTER_")],
        "Keep": [k for k in env_vars if k.startswith("KEEP_")],
        "Terraform": [k for k in env_vars if k.startswith("TF_")],
        "Go": [k for k in env_vars if k.startswith("GO")],
        "Python": [k for k in env_vars if k.startswith("PYTHON") or k.startswith("PY")],
        "Other": [],
    }

    categorized = {item for values in categories.values() for item in values}
    for key in env_vars:
        if key not in categorized:
            categories["Other"].append(key)

    return categories


def _display_categories(env_vars: Mapping[str, str], categories: Mapping[str, list[str]]) -> None:
    """Print category breakdown with example values."""
    for _, vars_in_cat in categories.items():
        if not vars_in_cat:
            continue

        for var in sorted(vars_in_cat)[:5]:
            value = env_vars.get(var, "")
            display_value = value if len(value) <= 50 else f"{value[:47]}..."
            pout(f"  {var} = {display_value}")
        if len(vars_in_cat) > 5:
            pout(f"  ... and {len(vars_in_cat) - 5} more", dim=True)

    pout("\n" + "=" * 60, color="cyan")
    pout("=" * 60, color="cyan")


def _check_expected_vars(env_vars: Mapping[str, str]) -> None:
    """Validate required runtime.env values."""
    expected_vars = {
        "TASTER_MODE": "test",
        "TASTER_VERSION": "1.0.0",
    }

    pout("\n📋 Expected Variables (from runtime.env.set):", fg="green")
    for var, expected in expected_vars.items():
        actual = env_vars.get(var)
        if actual != expected:
            pout(f"  ❌ {var} = {actual} (expected: {expected})")


def _validate_mappings(env_vars: Mapping[str, str]) -> None:
    """Ensure legacy variables are correctly remapped."""
    pout("\n🔄 Mapped Variables (from runtime.env.map):", fg="yellow")
    mappings = {"OLD_VAR": "NEW_VAR"}
    for source, target in mappings.items():
        if source in env_vars:
            pout(f"  ⚠️ {source} still exists (should be mapped to {target})")
        if target in env_vars:
            pout(f"  ✅ {target} present", fg="green")


def _run_whitelist_check(env_vars: Mapping[str, str]) -> None:
    """Simulate whitelist enforcement logic."""
    pout("\n🔒 Whitelist Mode Test:", color="magenta")
    allowed_patterns = [
        "PATH",
        "HOME",
        "USER",
        "TERM",
        "LANG",
        "LC_*",
        "FLAVOR_*",
        "TASTER_*",
        "KEEP_*",
    ]
    pout(f"  Allowed patterns: {', '.join(allowed_patterns)}")

    unexpected = []
    for key in env_vars:
        if key in {"NEW_VAR", "TASTER_MODE", "TASTER_VERSION"}:
            continue

        allowed = False
        for pattern in allowed_patterns:
            if pattern.endswith("*") and key.startswith(pattern[:-1]):
                allowed = True
                break
            if key == pattern:
                allowed = True
                break
        if not allowed:
            unexpected.append(key)

    if unexpected:
        pout(f"\n  ⚠️ Found {len(unexpected)} unexpected variables:", fg="red")
        for var in unexpected[:5]:
            pout(f"    - {var}")
        if len(unexpected) > 5:
            pout(f"    ... and {len(unexpected) - 5} more")
    else:
        pout("  ✅ Environment matches whitelist", fg="green")


def _print_env_source(env_vars: Mapping[str, str]) -> None:
    """Display metadata about the environment origin."""
    pout("\n" + "=" * 60, color="cyan")
    pout("📍 ENVIRONMENT SOURCE", color="cyan", bold=True)
    pout("=" * 60, color="cyan")

    for key in ["FLAVOR_WORKENV", "FLAVOR_COMMAND_NAME", "FLAVOR_ORIGINAL_COMMAND"]:
        if key in env_vars:
            pout(f"  {key.replace('FLAVOR_', '').replace('_', ' ').title()}: {env_vars[key]}")


# 🌶️📦🔚
