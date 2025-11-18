#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Centralized console output utilities for Flavor CLI.

Provides Unicode-safe wrappers around Foundation's console helpers that align with
the DAS (Duration/Action/Status) event system.
"""

from __future__ import annotations

from typing import Any

from provide.foundation.console import perr, pout
from provide.foundation.logger import get_logger

__all__ = [
    "echo",
    "echo_error",
    "get_command_logger",
]


def echo(message: str, **kwargs: Any) -> None:
    """
    Output a message to stdout with automatic Unicode handling.

    Uses Foundation's pout() which handles Unicode and terminal
    compatibility automatically.

    Args:
        message: Message to output
        **kwargs: Additional arguments (currently unused, for compatibility)
    """
    pout(message)


def echo_error(message: str, **kwargs: Any) -> None:
    """
    Output an error message to stderr with automatic Unicode handling.

    Uses Foundation's perr() which handles Unicode and terminal
    compatibility automatically.

    Args:
        message: Error message to output
        **kwargs: Additional arguments (currently unused, for compatibility)
    """
    perr(message)


def get_command_logger(command_name: str) -> Any:
    """
    Get a structured logger for a command.

    The logger uses Foundation's DAS (Duration/Action/Status) event system
    which automatically prefixes logs with appropriate emojis based on the
    event type and context.

    Args:
        command_name: Name of the command (e.g., 'pack', 'verify')

    Returns:
        Configured structlog logger with DAS emoji prefixing

    Example:
        log = get_command_logger("pack")
        log.debug("Starting packaging process", manifest=manifest_path)
        log.info("Package built successfully", output=output_path)
        log.error("Packaging failed", error=str(e))
    """
    return get_logger(f"flavor.commands.{command_name}")


# 🌶️📦🔚
