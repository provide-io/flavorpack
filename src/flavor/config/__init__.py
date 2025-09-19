"""FlavorPack Configuration System.

This module provides a Foundation-based configuration system for FlavorPack,
replacing manual environment variable handling with typed, validated configuration.
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
    load_config_from_env,
    reset_flavor_config,
    set_flavor_config,
)

__all__ = [
    "BuildConfig",
    "ExecutionConfig",
    "FlavorConfig",
    "MetadataConfig",
    "PathsConfig",
    "RuntimeRuntimeConfig",
    "SecurityConfig",
    "SystemConfig",
    "UVConfig",
    "get_flavor_config",
    "load_config_from_env",
    "reset_flavor_config",
    "set_flavor_config",
]
