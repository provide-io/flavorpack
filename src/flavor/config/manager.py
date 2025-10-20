# flavor/config/manager.py
#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""FlavorPack Configuration Manager.

This module provides the configuration management logic for FlavorPack,
including environment variable loading and global configuration management.
"""

from __future__ import annotations

import os
from typing import Any

from attrs import fields

from flavor.config.config import (
    FlavorConfig,
    PathsConfig,
    SecurityConfig,
    SystemConfig,
    UVConfig,
)


def load_config_from_env(config_class: type) -> dict[str, Any]:
    """Load configuration values from environment variables.

    Args:
        config_class: The configuration class to load environment variables for

    Returns:
        Dict of field names to environment variable values
    """
    kwargs = {}

    for field in fields(config_class):
        env_var = field.metadata.get("env_var")
        if env_var and env_var in os.environ:
            kwargs[field.name] = os.environ[env_var]

    return kwargs


class FlavorConfigManager:
    """Manager for FlavorPack configuration."""

    def __init__(self) -> None:
        """Initialize the configuration manager."""
        self._config: FlavorConfig | None = None

    def get_config(self) -> FlavorConfig:
        """Get the current FlavorConfig instance.

        Returns:
            The loaded FlavorConfig instance

        Raises:
            RuntimeError: If configuration hasn't been loaded
        """
        if self._config is None:
            raise RuntimeError(
                "Configuration not loaded. Call load_config() or set_flavor_config() first"
            )
        return self._config

    def load_config(self, config: FlavorConfig) -> None:
        """Load a FlavorConfig instance.

        Args:
            config: The configuration to load
        """
        self._config = config

    def reset_config(self) -> None:
        """Reset the configuration."""
        self._config = None


# Global configuration manager instance
_config_manager = FlavorConfigManager()


def get_flavor_config() -> FlavorConfig:
    """Get the global FlavorConfig instance.

    Returns:
        The current FlavorConfig

    Raises:
        RuntimeError: If configuration hasn't been loaded
    """
    return _config_manager.get_config()


def set_flavor_config(config: FlavorConfig) -> None:
    """Set the global FlavorConfig instance.

    Args:
        config: The configuration to set globally
    """
    _config_manager.load_config(config)


def reset_flavor_config() -> None:
    """Reset the global FlavorConfig instance."""
    _config_manager.reset_config()


# 🌶️📦📄🪄
