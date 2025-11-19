#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test argv[0] and command information."""

import os
from pathlib import Path
import sys

import click
from provide.foundation.console import pout


@click.command("argv")
def argv_command() -> None:
    """🎯 Test argv[0] and command information"""
    pout("=" * 60, color="cyan")
    pout("🎯 ARGV[0] AND COMMAND TEST", color="cyan", bold=True)
    pout("=" * 60, color="cyan")

    # Display all argv values
    pout("\n📋 Command Line Arguments:", color="green")
    for i, arg in enumerate(sys.argv):
        if i == 0:
            pout(f"  argv[0]: {arg} (program name)")
        else:
            pout(f"  argv[{i}]: {arg}")

    # Check environment variables
    env_vars = {
        "FLAVOR_COMMAND_NAME": "Command name override",
        "FLAVOR_ORIGINAL_COMMAND": "Original command path",
        "FLAVOR_WORKENV": "Work environment path",
    }

    for var, desc in env_vars.items():
        value = os.environ.get(var)
        if value:
            pout(f"  {var}: {value}")
        else:
            pout(f"  {var}: <not set> ({desc})")

    # Test argv[0] behavior

    _program_name = Path(sys.argv[0]).name
    expected_names = ["taster.psp", "taster", "test.psp", "dist/taster.psp"]

    if any(expected in sys.argv[0] for expected in expected_names):
        pass
    else:
        pout(f"  ⚠️ argv[0] might not be set correctly: {sys.argv[0]}", color="yellow")

    # Check launcher type
    pout("\n🚀 Launcher Detection:", color="blue")

    # Rust launcher sets argv[0] properly
    # Go launcher cannot set argv[0] and uses FLAVOR_COMMAND_NAME
    if "FLAVOR_COMMAND_NAME" in os.environ and os.environ["FLAVOR_COMMAND_NAME"] != sys.argv[0]:
        pout("  Launcher: Likely Go (using FLAVOR_COMMAND_NAME fallback)")
        pout(f"    - argv[0]: {sys.argv[0]}")
        pout(f"    - FLAVOR_COMMAND_NAME: {os.environ['FLAVOR_COMMAND_NAME']}")
    else:
        pout("  Launcher: Likely Rust (argv[0] set properly)")
        pout(f"    - argv[0]: {sys.argv[0]}")

    # Process information
    pout("\n📊 Process Information:", color="cyan")
    pout(f"  PID: {os.getpid()}")
    pout(f"  PPID: {os.getppid()}")
    pout(f"  Working Directory: {Path.cwd()}")

    # Python interpreter info
    pout(f"  Executable: {sys.executable}")
    pout(f"  Version: {sys.version.split()[0]}")
    pout(f"  Platform: {sys.platform}")


# 🌶️📦🔚
