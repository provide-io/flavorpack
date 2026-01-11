#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Start interactive Python shell"""

import code
import os
import sys

import click
from provide.foundation.console import pout


@click.command("shell")
def shell_command() -> None:
    """🐚 Start interactive Python shell"""
    pout("=" * 60, color="cyan")
    pout("🐚 INTERACTIVE PYTHON SHELL", color="cyan", bold=True)
    pout("=" * 60, color="cyan")

    # Prepare namespace
    namespace = {
        "os": os,
        "sys": sys,
        "Path": __import__("pathlib").Path,
        "click": click,
    }

    # Try to import flavor if available
    try:
        import flavor

        namespace["flavor"] = flavor
    except ImportError:
        pout("⚠️ Flavor module not available")

    # Display available objects
    pout("\nAvailable objects:", color="green")
    for name in sorted(namespace.keys()):
        if not name.startswith("_"):
            pout(f"  • {name}")

    pout("\nEnvironment:", color="yellow")
    pout(f"  • Python: {sys.version.split()[0]}")
    pout(f"  • Platform: {sys.platform}")
    if "FLAVOR_WORKENV" in os.environ:
        pout(f"  • Workenv: {os.environ['FLAVOR_WORKENV']}")

    pout("\nType 'exit()' or Ctrl-D to exit the shell.\n")

    # Start interactive shell
    code.interact(local=namespace, banner="")


# 🌶️📦🔚
