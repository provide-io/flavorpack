#!/usr/bin/env python3
#
# flavor/cli.py
#
"The `flavor` command-line interface."

from __future__ import annotations

import importlib.metadata
import logging
import os
from pathlib import Path
import sys

import click
from provide.foundation import LoggingConfig, TelemetryConfig, get_hub
from provide.foundation.logger import get_logger

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
from flavor.commands.extract import extract_all_command, extract_command
from flavor.commands.ingredients import ingredient_group
from flavor.commands.inspect import inspect_command
from flavor.commands.keygen import keygen_command
from flavor.commands.package import pack_command
from flavor.commands.utils import clean_command
from flavor.commands.verify import verify_command
from flavor.commands.workenv import workenv_group

try:
    __version__ = importlib.metadata.version("flavor")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0-dev"

log = get_logger(__name__)


def _initialize_foundation(log_level: str, log_file: Path | None = None) -> None:
    """Initialize Foundation logging and telemetry.

    Configures provide-foundation with service name, log level, and optional file output.
    Uses Foundation's public API to properly override auto-initialization.

    Args:
        log_level: Log level string (trace, debug, info, warning, error)
        log_file: Optional path to log file
    """
    try:
        # Map log level string to logging constant
        level_upper = log_level.upper()
        if level_upper == "TRACE":
            from provide.foundation.logger.trace import TRACE_LEVEL_NUM

            level = TRACE_LEVEL_NUM
            level_name = "TRACE"
        else:
            level = getattr(logging, level_upper, logging.INFO)
            level_name = logging.getLevelName(level)

        # Load base config from environment (preserves OpenObserve/OTLP auto-configuration)
        from attrs import evolve

        base_config = TelemetryConfig.from_env()

        # Override service_name and logging settings for flavorpack
        config = evolve(
            base_config,
            service_name="flavor",  # Set service name for OpenObserve/OTLP telemetry
            logging=LoggingConfig(
                console_formatter="key_value",  # Use Foundation's default formatter
                default_level=level_name,
                das_emoji_prefix_enabled=True,  # Enable DAS emoji prefixes
                logger_name_emoji_prefix_enabled=False,  # Keep output clean
            ),
        )

        # Initialize Foundation with explicit config
        # This overrides any auto-initialization that may have occurred
        hub = get_hub()
        hub.initialize_foundation(config)

        # Add file handler if specified
        if log_file:
            file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
            file_handler.setLevel(level)

            # Use simple format for file logs
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(formatter)
            logging.getLogger().addHandler(file_handler)

        log.debug(
            "🔧 Foundation initialized",
            service="flavor",
            log_level=level_name,
            log_file=str(log_file) if log_file else None,
        )

    except Exception as e:
        # Fallback to basic logging if Foundation setup fails
        logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)s: %(message)s",
            force=True,
        )
        print(f"⚠️  Failed to initialize Foundation logging: {e}")


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
@click.option(
    "--log-file",
    type=click.Path(path_type=Path),
    default=None,
    help="Write logs to file in addition to console.",
)
@click.pass_context
def cli(ctx: click.Context, log_level: str, log_file: Path | None) -> None:
    """PSPF (Progressive Secure Package Format) Build Tool."""
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = log_level
    ctx.obj["log_file"] = log_file

    # Skip Foundation setup when running under pytest to avoid conflicts
    if "pytest" not in sys.modules:
        _initialize_foundation(log_level, log_file)


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
