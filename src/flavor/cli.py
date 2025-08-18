#!/usr/bin/env python3
#
# flavor/cli.py
#
"The `flavor` command-line interface."

import importlib.metadata

import click

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
        logging=LoggingConfig(default_level=telemetry_log_level, console_formatter="key_value"),
    )
    setup_telemetry(config)


# Import and register all commands
from flavor.commands.helpers import helper_group
from flavor.commands.inspect import inspect_command
from flavor.commands.keygen import keygen_command
from flavor.commands.package import package_command
from flavor.commands.utils import analyze_deps_command, clean_command
from flavor.commands.verify import verify_command
from flavor.commands.workenv import workenv_group

# Register simple commands
cli.add_command(keygen_command, name="keygen")
cli.add_command(package_command, name="package")
cli.add_command(verify_command, name="verify")
cli.add_command(inspect_command, name="inspect")
cli.add_command(clean_command, name="clean")
cli.add_command(analyze_deps_command, name="analyze-deps")

# Register command groups
cli.add_command(workenv_group, name="workenv")
cli.add_command(helper_group, name="helpers")

# Keep main for backwards compatibility
main = cli

if __name__ == "__main__":
    cli()