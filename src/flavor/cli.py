#!/usr/bin/env python3
#
# flavor/cli.py
#
"The `flavor` command-line interface."

from __future__ import annotations

import importlib.metadata
import os
import sys

import click
from provide.foundation import CLIContext

# Import all commands at module level
from flavor.commands.extract import extract_all_command, extract_command
from flavor.commands.ingredients import ingredient_group
from flavor.commands.inspect import inspect_command
from flavor.commands.keygen import keygen_command
from flavor.commands.package import pack_command
from flavor.commands.utils import clean_command
from flavor.commands.verify import verify_command
from flavor.commands.workenv import workenv_group

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

try:
    __version__ = importlib.metadata.version("flavor")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0-dev"


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.version_option(
    __version__,
    "-V",
    "--version",
    prog_name="flavor",
    message="%(prog)s version %(version)s",
)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """PSPF (Progressive Secure Package Format) Build Tool.

    Configure logging via environment variables:
    - FOUNDATION_LOG_LEVEL: Set log level (trace, debug, info, warning, error)
    - FOUNDATION_LOG_FILE: Write logs to file
    - FOUNDATION_SETUP_LOG_LEVEL: Control Foundation's initialization logs
    """
    ctx.ensure_object(dict)

    # Skip Foundation setup when running under pytest to avoid conflicts
    if "pytest" not in sys.modules:
        # Initialize Foundation with CLIContext from environment
        cli_ctx = CLIContext.from_env()
        ctx.obj["cli_context"] = cli_ctx
        ctx.obj["log"] = cli_ctx.logger


# Register simple commands
cli.add_command(keygen_command, name="keygen")
cli.add_command(pack_command, name="pack")
cli.add_command(verify_command, name="verify")
cli.add_command(inspect_command, name="inspect")
cli.add_command(extract_command, name="extract")
cli.add_command(extract_all_command, name="extract-all")
cli.add_command(clean_command, name="clean")

# Register command groups
cli.add_command(workenv_group, name="workenv")
cli.add_command(ingredient_group, name="ingredients")

main = cli

if __name__ == "__main__":
    cli()
