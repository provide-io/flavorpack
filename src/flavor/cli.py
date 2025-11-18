#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""FlavorPack command-line interface entrypoint."""

from __future__ import annotations

import os
import sys

from attrs import evolve
import click
from provide.foundation import CLIContext, TelemetryConfig, get_hub
from provide.foundation.utils import get_version

# Import all commands at module level
from flavor.commands.extract import extract_all_command, extract_command
from flavor.commands.helpers import helper_group
from flavor.commands.inspect import inspect_command
from flavor.commands.keygen import keygen_command
from flavor.commands.package import pack_command
from flavor.commands.utils import clean_command
from flavor.commands.verify import verify_command
from flavor.commands.workenv import workenv_group
from flavor.config import FlavorRuntimeConfig

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

__version__ = get_version("flavorpack", caller_file=__file__)


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
    - FLAVOR_LOG_LEVEL: Set log level for FlavorPack (trace, debug, info, warning, error)
    - FLAVOR_SETUP_LOG_LEVEL: Control Foundation's initialization logs
    - PROVIDE_LOG_LEVEL: Fallback log level if FLAVOR_LOG_LEVEL not set
    - PROVIDE_LOG_FILE: Write logs to file
    """
    ctx.ensure_object(dict)

    # Load FlavorPack configuration from environment
    flavor_config = FlavorRuntimeConfig.from_env()

    # Initialize Foundation with proper configuration
    cli_ctx = CLIContext.from_env()

    # Get base telemetry config from environment
    base_telemetry = TelemetryConfig.from_env()

    # Merge with FlavorPack-specific settings
    telemetry_config = evolve(
        base_telemetry,
        service_name="flavorpack",
        logging=evolve(
            base_telemetry.logging,
            default_level=flavor_config.log_level,  # type: ignore[arg-type]
        ),
    )

    # Initialize Foundation with merged config
    hub = get_hub()
    hub.initialize_foundation(telemetry_config)

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
cli.add_command(helper_group, name="helpers")

main = cli

if __name__ == "__main__":
    cli()

# 🌶️📦🔚
