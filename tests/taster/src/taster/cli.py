#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Taster CLI - Minimal entry point that loads commands from modules."""

from __future__ import annotations

import os
from pathlib import Path
import sys

# Set up Windows Unicode support early
if sys.platform == "win32":
    # Ensure UTF-8 encoding for Windows console
    if not os.environ.get("PYTHONIOENCODING"):
        os.environ["PYTHONIOENCODING"] = "utf-8"
    if not os.environ.get("PYTHONUTF8"):
        os.environ["PYTHONUTF8"] = "1"
    # Try to enable ANSI escape sequences on Windows
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass  # Ignore if we can't enable ANSI

# Override sys.argv[0] if FLAVOR_COMMAND_NAME is set
if "FLAVOR_COMMAND_NAME" in os.environ:
    sys.argv[0] = os.environ["FLAVOR_COMMAND_NAME"]

import click

# Import all commands from modules
from taster.commands import (
    argv_command,
    echo_command,
    env_command,
    features_command,
    info_command,
    metadata_command,
    shell_command,
    signals_command,
    test_command,
    verify_command,
)
from taster.commands.cache import cache
from taster.commands.exec_test import exec_test_command
from taster.commands.exit import exit_command
from taster.commands.file import file_command
from taster.commands.launcher_test import launcher_test_command
from taster.commands.mmap import mmap_command
from taster.commands.package import package_command
from taster.commands.pipe import pipe_command
from taster.commands.slot_test import slot_test_command


def get_program_name() -> str:
    """Get the program name from environment or sys.argv"""
    if "FLAVOR_COMMAND_NAME" in os.environ:
        return os.environ["FLAVOR_COMMAND_NAME"]
    return Path(sys.argv[0]).name


# Set up Click with the proper program name
prog_name = get_program_name()


@click.group(
    context_settings=dict(
        help_option_names=["-h", "--help"],
    ),
    invoke_without_command=False,
)
@click.version_option("1.0.0", prog_name=prog_name)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """🍯 Taster - Test package for flavor functionality"""
    # Override the program name in the context
    ctx.info_name = prog_name


# Add all commands to the CLI group
cli.add_command(env_command)
cli.add_command(argv_command)
cli.add_command(echo_command)
cli.add_command(info_command)
cli.add_command(features_command)
cli.add_command(metadata_command)
cli.add_command(shell_command)
cli.add_command(signals_command)
cli.add_command(test_command)
cli.add_command(verify_command)
cli.add_command(package_command)
cli.add_command(pipe_command)
cli.add_command(mmap_command)
cli.add_command(cache)
cli.add_command(exec_test_command)
cli.add_command(exit_command)
cli.add_command(file_command)
cli.add_command(launcher_test_command)
cli.add_command(slot_test_command)


def main() -> None:
    """Entry point for the taster command."""
    cli()


if __name__ == "__main__":
    main()

# 🌶️📦🔚
