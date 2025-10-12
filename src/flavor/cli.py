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
from typing import cast

# Set Foundation setup log level BEFORE importing Foundation
# This prevents auto-initialization from emitting debug/trace logs
# Uses FOUNDATION_LOG_LEVEL if set, otherwise uses ERROR to suppress setup noise
if "FOUNDATION_SETUP_LOG_LEVEL" not in os.environ:
    foundation_level = os.environ.get(
        "FOUNDATION_LOG_LEVEL", os.environ.get("PROVIDE_LOG_LEVEL", "ERROR")
    )
    os.environ["FOUNDATION_SETUP_LOG_LEVEL"] = foundation_level

import click
from provide.foundation import LoggingConfig, TelemetryConfig, get_hub
from provide.foundation.logger import get_logger
from provide.foundation.logger.types import LogLevelStr
from structlog.typing import FilteringBoundLogger as StructLogger

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

# Logger is created AFTER Foundation initialization to ensure correct service_name
# See _initialize_foundation() for logger creation


def _initialize_foundation(
    log_level: str | None, log_file: Path | None = None
) -> StructLogger:
    """Initialize Foundation logging and telemetry.

    Configures provide-foundation with service name, log level, and optional file output.
    Uses Foundation's public API to properly override auto-initialization.

    IMPORTANT: Creates logger AFTER Foundation init to ensure service_name="flavor"
    is properly set in OpenTelemetry/OTLP resources.

    Args:
        log_level: Log level string (trace, debug, info, warning, error) or None to use env
        log_file: Optional path to log file

    Returns:
        Configured logger with correct service_name
    """
    try:
        # Load base config from environment (preserves OpenObserve/OTLP auto-configuration)
        from attrs import evolve

        base_config = TelemetryConfig.from_env()

        # Determine effective log level (CLI override or from environment)
        if log_level is not None:
            # Map log level string to logging constant
            level_upper = log_level.upper()
            if level_upper == "TRACE":
                from provide.foundation.logger.trace import TRACE_LEVEL_NUM

                level = TRACE_LEVEL_NUM
                level_name = "TRACE"
            else:
                level = getattr(logging, level_upper, logging.INFO)
                level_name = logging.getLevelName(level)

            # Cast to LogLevelStr for type safety
            log_level_typed = cast(LogLevelStr, level_name)

            # Override service_name and logging settings for flavorpack
            config = evolve(
                base_config,
                service_name="flavor",  # Set service name for OpenObserve/OTLP telemetry
                logging=LoggingConfig(
                    console_formatter="key_value",  # Use Foundation's default formatter
                    default_level=log_level_typed,
                    foundation_setup_log_level=log_level_typed,  # Control Foundation init logs
                    das_emoji_prefix_enabled=True,  # Enable DAS emoji prefixes
                    logger_name_emoji_prefix_enabled=False,  # Keep output clean
                ),
            )
        else:
            # No CLI override - use environment config but set service_name and formatter
            config = evolve(
                base_config,
                service_name="flavor",  # Set service name for OpenObserve/OTLP telemetry
                logging=evolve(
                    base_config.logging,
                    console_formatter="key_value",  # Use Foundation's default formatter
                    foundation_setup_log_level=base_config.logging.default_level,  # Match setup to default
                    das_emoji_prefix_enabled=True,  # Enable DAS emoji prefixes
                    logger_name_emoji_prefix_enabled=False,  # Keep output clean
                ),
            )
            level_name = base_config.logging.default_level
            level_upper = level_name.upper()
            if level_upper == "TRACE":
                from provide.foundation.logger.trace import TRACE_LEVEL_NUM

                level = TRACE_LEVEL_NUM
            else:
                level = getattr(logging, level_upper, logging.INFO)

        # Initialize Foundation with explicit config
        # This overrides any auto-initialization that may have occurred
        hub = get_hub()
        hub.initialize_foundation(config)

        # Create logger AFTER Foundation initialization
        # This ensures service_name="flavor" is properly set in OTLP resources
        log = get_logger(__name__)

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

        log.info(
            "🔧 Foundation explicitly re-initialized",
            service="flavor",
            log_level=level_name,
            log_file=str(log_file) if log_file else None,
        )

        return log

    except Exception as e:
        # Fallback to basic logging if Foundation setup fails
        logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)s: %(message)s",
            force=True,
        )
        print(f"⚠️  Failed to initialize Foundation logging: {e}")
        # Return a basic logger as fallback
        return get_logger(__name__)


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
    default=None,
    help="Set logging level (default: from FOUNDATION_LOG_LEVEL env or info).",
)
@click.option(
    "--log-file",
    type=click.Path(),
    default=None,
    help="Write logs to file in addition to console.",
)
@click.pass_context
def cli(ctx: click.Context, log_level: str | None, log_file: str | None) -> None:
    """PSPF (Progressive Secure Package Format) Build Tool."""
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = log_level
    ctx.obj["log_file"] = log_file

    # Skip Foundation setup when running under pytest to avoid conflicts
    if "pytest" not in sys.modules:
        log_file_path = Path(log_file) if log_file else None
        log = _initialize_foundation(log_level, log_file_path)
        ctx.obj["log"] = log  # Store logger in context for subcommands


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
