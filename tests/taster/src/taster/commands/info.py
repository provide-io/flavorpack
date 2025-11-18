#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Display package and system information"""

import os
from pathlib import Path
import platform
import sys

import click
from provide.foundation.console import pout


@click.command("info")
def info_command() -> None:
    """Display package and system information."""
    pout("=" * 60, color="cyan")
    pout("INFO: PACKAGE AND SYSTEM INFORMATION", color="cyan", bold=True)
    pout("=" * 60, color="cyan")

    # Package information
    pout("  Name: taster")
    pout("  Version: 1.0.0")
    pout("  Purpose: Test package for flavor functionality")

    # System information
    pout("\n💻 System Information:", color="yellow")
    pout(f"  Platform: {platform.platform()}")
    pout(f"  Machine: {platform.machine()}")
    pout(f"  Processor: {platform.processor() or 'N/A'}")
    pout(f"  Python: {platform.python_version()}")

    # Process information
    pout(f"  PID: {os.getpid()}")
    pout(f"  Working Directory: {Path.cwd()}")
    pout(f"  Executable: {sys.executable}")

    # Flavor information
    pout("\n🚀 Flavor Information:", color="magenta")
    if "FLAVOR_WORKENV" in os.environ:
        pout(f"  Work Environment: {os.environ['FLAVOR_WORKENV']}")
    else:
        pout("  Work Environment: <not set>")

    if "FLAVOR_COMMAND_NAME" in os.environ:
        pout(f"  Command Name: {os.environ['FLAVOR_COMMAND_NAME']}")

    # Check for flavor module
    try:
        import flavor

        pout("  Flavor Module: Available")
        if hasattr(flavor, "__version__"):
            pout(f"  Flavor Version: {flavor.__version__}")
    except ImportError:
        pout("  Flavor Module: Not available (running standalone)")

    # Environment summary
    env_count = len(os.environ)
    flavor_vars = [k for k in os.environ if k.startswith("FLAVOR_")]
    taster_vars = [k for k in os.environ if k.startswith("TASTER_")]

    pout(f"  Total Variables: {env_count}")
    pout(f"  Flavor Variables: {len(flavor_vars)}")
    pout(f"  Taster Variables: {len(taster_vars)}")


# 🌶️📦🔚
