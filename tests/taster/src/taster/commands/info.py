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


@click.command("info")
def info_command() -> None:
    """ℹ️ Display package and system information"""
    click.secho("=" * 60, fg="cyan")
    click.secho("ℹ️ PACKAGE AND SYSTEM INFORMATION", fg="cyan", bold=True)
    click.secho("=" * 60, fg="cyan")

    # Package information
    click.echo("  Name: taster")
    click.echo("  Version: 1.0.0")
    click.echo("  Purpose: Test package for flavor functionality")

    # System information
    click.secho("\n💻 System Information:", fg="yellow")
    click.echo(f"  Platform: {platform.platform()}")
    click.echo(f"  Machine: {platform.machine()}")
    click.echo(f"  Processor: {platform.processor() or 'N/A'}")
    click.echo(f"  Python: {platform.python_version()}")

    # Process information
    click.echo(f"  PID: {os.getpid()}")
    click.echo(f"  Working Directory: {Path.cwd()}")
    click.echo(f"  Executable: {sys.executable}")

    # Flavor information
    click.secho("\n🚀 Flavor Information:", fg="magenta")
    if "FLAVOR_WORKENV" in os.environ:
        click.echo(f"  Work Environment: {os.environ['FLAVOR_WORKENV']}")
    else:
        click.echo("  Work Environment: <not set>")

    if "FLAVOR_COMMAND_NAME" in os.environ:
        click.echo(f"  Command Name: {os.environ['FLAVOR_COMMAND_NAME']}")

    # Check for flavor module
    try:
        import flavor

        click.echo("  Flavor Module: Available")
        if hasattr(flavor, "__version__"):
            click.echo(f"  Flavor Version: {flavor.__version__}")
    except ImportError:
        click.echo("  Flavor Module: Not available (running standalone)")

    # Environment summary
    env_count = len(os.environ)
    flavor_vars = [k for k in os.environ if k.startswith("FLAVOR_")]
    taster_vars = [k for k in os.environ if k.startswith("TASTER_")]

    click.echo(f"  Total Variables: {env_count}")
    click.echo(f"  Flavor Variables: {len(flavor_vars)}")
    click.echo(f"  Taster Variables: {len(taster_vars)}")

# 🌶️📦🔚
