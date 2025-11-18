#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""FlavorPack configuration system built on the Provide Foundation config stack.

Provides typed, validated configuration models that replace ad-hoc env handling.
"""

from __future__ import annotations

from flavor.config.config import (
    BuildConfig,
    ExecutionConfig,
    FlavorConfig,
    MetadataConfig,
    PathsConfig,
    RuntimeRuntimeConfig,
    SecurityConfig,
    SystemConfig,
    UVConfig,
)
from flavor.config.manager import (
    get_flavor_config,
    reset_flavor_config,
    set_flavor_config,
)
from flavor.config.runtime import FlavorRuntimeConfig

__all__ = [
    "BuildConfig",
    "ExecutionConfig",
    "FlavorConfig",
    "FlavorRuntimeConfig",
    "MetadataConfig",
    "PathsConfig",
    "RuntimeRuntimeConfig",
    "SecurityConfig",
    "SystemConfig",
    "UVConfig",
    "get_flavor_config",
    "reset_flavor_config",
    "set_flavor_config",
]

# 🌶️📦🔚
