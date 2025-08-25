#!/usr/bin/env python3
#
# flavor/cli.py
#
"The `flavor` command-line interface."

import importlib.metadata
import os
import sys

import click

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

# Import all commands at module level
from flavor.commands.ingredients import ingredient_group
from flavor.commands.inspect import inspect_command
from flavor.commands.keygen import keygen_command
from flavor.commands.package import pack_command
from flavor.commands.utils import analyze_deps_command, clean_command
from flavor.commands.verify import verify_command
from flavor.commands.workenv import workenv_group

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
@click.option(
    "--log-level",
    type=click.Choice(
        ["trace", "debug", "info", "warning", "error"],
        case_sensitive=False,
    ),
    default="info",
    help="Set logging level (default: info).",
)
@click.pass_context
def cli(ctx: click.Context, log_level: str) -> None:
    """PSPF (Progressive Secure Package Format) Build Tool."""
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = log_level

    from pyvider.telemetry import LoggingConfig, TelemetryConfig, setup_telemetry

    telemetry_log_level = log_level.upper()

    config = TelemetryConfig(
        service_name="flavor",
        logging=LoggingConfig(
            default_level=telemetry_log_level, console_formatter="key_value"
        ),
    )
    setup_telemetry(config)


# Register simple commands
cli.add_command(keygen_command, name="keygen")
cli.add_command(pack_command, name="pack")
cli.add_command(verify_command, name="verify")
cli.add_command(inspect_command, name="inspect")
cli.add_command(clean_command, name="clean")
cli.add_command(analyze_deps_command, name="analyze-deps")

# Register command groups
cli.add_command(workenv_group, name="workenv")
cli.add_command(ingredient_group, name="ingredients")

# Keep main for backwards compatibility
main = cli

if __name__ == "__main__":
    cli()
