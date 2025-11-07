#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Environment variable testing command"""

import os

import click
from provide.foundation.console import perr, pout


@click.command("env")
def env_command() -> None:
    env_vars = dict(os.environ)

    pout("=" * 60, color="cyan")
    pout("=" * 60, color="cyan")
    pout(f"📊 Total variables: {len(env_vars)}", fg="yellow")

    # Categorize variables
    categories = {
        "System": ["PATH", "HOME", "USER", "TERM", "SHELL", "PWD"],
        "Locale": [k for k in env_vars if k.startswith("LANG") or k.startswith("LC_")],
        "Flavor": [k for k in env_vars if k.startswith("FLAVOR_")],
        "Taster": [k for k in env_vars if k.startswith("TASTER_")],
        "Keep": [k for k in env_vars if k.startswith("KEEP_")],
        "Terraform": [k for k in env_vars if k.startswith("TF_")],
        "Go": [k for k in env_vars if k.startswith("GO")],
        "Python": [k for k in env_vars if k.startswith("PYTHON") or k.startswith("PY")],
        "Other": [],
    }

    # Find uncategorized
    categorized = set()
    for cat_vars in categories.values():
        if isinstance(cat_vars, list):
            categorized.update(cat_vars)

    for key in env_vars:
        if key not in categorized:
            categories["Other"].append(key)

    # Display categories
    for category, vars in categories.items():
        if vars:
            for var in sorted(vars)[:5]:
                value = env_vars.get(var, "")
                if len(value) > 50:
                    value = value[:47] + "..."
                pout(f"  {var} = {value}")
            if len(vars) > 5:
                pout(f"  ... and {len(vars) - 5} more", dim=True)

    # Test expected values from runtime.env
    pout("\n" + "=" * 60, color="cyan")
    pout("=" * 60, color="cyan")

    # Check for expected variables set by runtime.env
    expected_vars = {
        "TASTER_MODE": "test",
        "TASTER_VERSION": "1.0.0",
    }

    pout("\n📋 Expected Variables (from runtime.env.set):", fg="green")
    for var, expected in expected_vars.items():
        actual = os.environ.get(var)
        if actual == expected:
            pass
        else:
            pout(f"  ❌ {var} = {actual} (expected: {expected})")

    # Check mapped variables
    pout("\n🔄 Mapped Variables (from runtime.env.map):", fg="yellow")
    mappings = {
        "OLD_VAR": "NEW_VAR",
    }
    for old, new in mappings.items():
        if old in os.environ:
            pout(f"  ⚠️ {old} still exists (should be mapped to {new})")
        if new in os.environ:
            pass

    # Test whitelist mode (unset = ["*"] with pass list)
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

    # Check for unexpected variables (ones that should have been removed)
    unexpected = []
    for key in env_vars:
        # Check if this key matches any allowed pattern
        allowed = False
        for pattern in allowed_patterns:
            if pattern.endswith("*"):
                if key.startswith(pattern[:-1]):
                    allowed = True
                    break
            elif key == pattern:
                allowed = True
                break
        if not allowed and key not in ["NEW_VAR", "TASTER_MODE", "TASTER_VERSION"]:
            unexpected.append(key)

    if unexpected:
        pout(f"\n  ⚠️ Found {len(unexpected)} unexpected variables:", fg="red")
        for var in unexpected[:5]:
            pout(f"    - {var}")
        if len(unexpected) > 5:
            pout(f"    ... and {len(unexpected) - 5} more")
    else:
        pass

    # Show environment source
    pout("\n" + "=" * 60, color="cyan")
    pout("📍 ENVIRONMENT SOURCE", color="cyan", bold=True)
    pout("=" * 60, color="cyan")

    if "FLAVOR_WORKENV" in os.environ:
        pout(f"  Work Environment: {os.environ['FLAVOR_WORKENV']}")
    if "FLAVOR_COMMAND_NAME" in os.environ:
        pout(f"  Command Name: {os.environ['FLAVOR_COMMAND_NAME']}")
    if "FLAVOR_ORIGINAL_COMMAND" in os.environ:
        pout(f"  Original Command: {os.environ['FLAVOR_ORIGINAL_COMMAND']}")


# 🌶️📦🔚
