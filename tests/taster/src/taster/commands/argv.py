"""Test argv[0] and command information"""

import os
from pathlib import Path
import sys

import click


@click.command("argv")
def argv_command() -> None:
    """🎯 Test argv[0] and command information"""
    click.secho("=" * 60, fg="cyan")
    click.secho("🎯 ARGV[0] AND COMMAND TEST", fg="cyan", bold=True)
    click.secho("=" * 60, fg="cyan")

    # Display all argv values
    click.secho("\n📋 Command Line Arguments:", fg="green")
    for i, arg in enumerate(sys.argv):
        if i == 0:
            click.echo(f"  argv[0]: {arg} (program name)")
        else:
            click.echo(f"  argv[{i}]: {arg}")

    # Check environment variables
    click.secho("\n🔧 Environment Variables:", fg="yellow")
    env_vars = {
        "FLAVOR_COMMAND_NAME": "Command name override",
        "FLAVOR_ORIGINAL_COMMAND": "Original command path",
        "FLAVOR_WORKENV": "Work environment path",
    }

    for var, desc in env_vars.items():
        value = os.environ.get(var)
        if value:
            click.echo(f"  {var}: {value}")
        else:
            click.echo(f"  {var}: <not set> ({desc})")

    # Test argv[0] behavior
    click.secho("\n🧪 argv[0] Test Results:", fg="magenta")

    Path(sys.argv[0]).name
    expected_names = ["taster.psp", "taster", "test.psp", "dist/taster.psp"]

    if any(expected in sys.argv[0] for expected in expected_names):
        click.secho(f"  ✅ argv[0] shows flavor binary name: {sys.argv[0]}", fg="green")
    else:
        click.secho(f"  ⚠️ argv[0] might not be set correctly: {sys.argv[0]}", fg="yellow")

    # Check launcher type
    click.secho("\n🚀 Launcher Detection:", fg="blue")

    # Rust launcher sets argv[0] properly
    # Go launcher cannot set argv[0] and uses FLAVOR_COMMAND_NAME
    if "FLAVOR_COMMAND_NAME" in os.environ and os.environ["FLAVOR_COMMAND_NAME"] != sys.argv[0]:
        click.echo("  Launcher: Likely Go (using FLAVOR_COMMAND_NAME fallback)")
        click.echo(f"    - argv[0]: {sys.argv[0]}")
        click.echo(f"    - FLAVOR_COMMAND_NAME: {os.environ['FLAVOR_COMMAND_NAME']}")
    else:
        click.echo("  Launcher: Likely Rust (argv[0] set properly)")
        click.echo(f"    - argv[0]: {sys.argv[0]}")

    # Process information
    click.secho("\n📊 Process Information:", fg="cyan")
    click.echo(f"  PID: {os.getpid()}")
    click.echo(f"  PPID: {os.getppid()}")
    click.echo(f"  Working Directory: {Path.cwd()}")

    # Python interpreter info
    click.secho("\n🐍 Python Information:", fg="yellow")
    click.echo(f"  Executable: {sys.executable}")
    click.echo(f"  Version: {sys.version.split()[0]}")
    click.echo(f"  Platform: {sys.platform}")
