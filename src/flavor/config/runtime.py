#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""FlavorPack runtime configuration for CLI startup."""

from __future__ import annotations

from attrs import define
from provide.foundation.config.base import field
from provide.foundation.config.env import RuntimeConfig

VALID_LOG_LEVELS = {"TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def parse_log_level(value: str) -> str:
    """Validate and normalize log levels."""
    normalized = value.strip().upper()
    if normalized not in VALID_LOG_LEVELS:
        raise ValueError(f"Invalid log level: {value}")
    return normalized


@define
class FlavorRuntimeConfig(RuntimeConfig):
    """FlavorPack runtime configuration for CLI startup."""

    log_level: str = field(
        default="WARNING",
        env_var="FLAVOR_LOG_LEVEL",
        metadata={
            "help": "Log level for FlavorPack operations (TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL)"
        },
    )

    setup_log_level: str = field(
        default="WARNING",
        env_var="FLAVOR_SETUP_LOG_LEVEL",
        converter=parse_log_level,
        metadata={"help": "Log level for Foundation setup messages during initialization"},
    )
