#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Start interactive Python shell"""

import code
import os
import sys

import click


@click.command("shell")
def shell_command() -> None:
    """🐚 Start interactive Python shell"""
    click.secho("=" * 60, fg="cyan")
    click.secho("🐚 INTERACTIVE PYTHON SHELL", fg="cyan", bold=True)
    click.secho("=" * 60, fg="cyan")

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
        click.echo("⚠️ Flavor module not available")

    # Display available objects
    click.secho("\nAvailable objects:", fg="green")
    for name in sorted(namespace.keys()):
        if not name.startswith("_"):
            click.echo(f"  • {name}")

    click.secho("\nEnvironment:", fg="yellow")
    click.echo(f"  • Python: {sys.version.split()[0]}")
    click.echo(f"  • Platform: {sys.platform}")
    if "FLAVOR_WORKENV" in os.environ:
        click.echo(f"  • Workenv: {os.environ['FLAVOR_WORKENV']}")

    click.echo("\nType 'exit()' or Ctrl-D to exit the shell.\n")

    # Start interactive shell
    code.interact(local=namespace, banner="")


# 🌶️📦🔚
