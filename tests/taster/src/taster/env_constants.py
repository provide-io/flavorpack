#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Centralized FLAVOR_* environment variable name constants for taster.

Re-exports shared constants from flavor.config.defaults and defines
runtime constants that are injected by Go/Rust launchers.
"""

# Shared with Go/Rust — defined in the published flavorpack wheel
from flavor.config.defaults import (
    ENV_CACHE_COMPAT,
    ENV_LOG_LEVEL,
    ENV_WORKENV,
)

# Runtime env vars injected by Go/Rust launchers into child process.
# These are defined here (not imported from flavor.config.defaults) because
# the published flavorpack wheel may not include them yet.
ENV_COMMAND_NAME = "FLAVOR_COMMAND_NAME"
ENV_ORIGINAL_COMMAND = "FLAVOR_ORIGINAL_COMMAND"
ENV_EXEC_MODE = "FLAVOR_EXEC_MODE"
ENV_LAUNCHER_CLI = "FLAVOR_LAUNCHER_CLI"

# Re-export everything for single-import convenience
__all__ = [
    "ENV_CACHE_COMPAT",
    "ENV_COMMAND_NAME",
    "ENV_EXEC_MODE",
    "ENV_LAUNCHER_CLI",
    "ENV_LOG_LEVEL",
    "ENV_ORIGINAL_COMMAND",
    "ENV_WORKENV",
]
