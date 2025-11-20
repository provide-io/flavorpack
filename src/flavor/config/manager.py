#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""FlavorPack configuration manager for env loading and global access."""

from __future__ import annotations

from flavor.config.config import (
    FlavorConfig,
    PathsConfig,
    SecurityConfig,
    SystemConfig,
    UVConfig,
)


class FlavorConfigManager:
    """Manager for FlavorPack configuration."""

    def __init__(self) -> None:
        """Initialize the configuration manager."""
        self._config: FlavorConfig | None = None

    def get_config(self) -> FlavorConfig:
        """Get the current FlavorConfig instance.

        This creates a configuration instance that loads from environment variables
        using Foundation's config system.

        Returns:
            FlavorConfig: The current configuration instance
        """
        if self._config is None:
            self._config = self._create_default_config()
        return self._config

    def set_config(self, config: FlavorConfig | None) -> None:
        """Set the FlavorConfig instance.

        Args:
            config: The FlavorConfig instance to use, or None to reset
        """
        self._config = config

    def reset_config(self) -> None:
        """Reset the configuration to force reload from environment."""
        self._config = None

    def _create_default_config(self) -> FlavorConfig:
        """Create a default configuration loading from environment variables."""
        # Load system config from environment variables using Foundation's from_env()
        system_config = SystemConfig(
            security=SecurityConfig.from_env(),
            paths=PathsConfig.from_env(),
            uv=UVConfig.from_env(),
        )

        # Create minimal config for environment-only usage
        return FlavorConfig(
            name="flavor",  # Default name
            version="0.0.0",  # Default version
            entry_point="flavor.cli:main",  # Default entry point
            system=system_config,
        )


# Global configuration manager instance
_config_manager = FlavorConfigManager()


def get_flavor_config() -> FlavorConfig:
    """Get the global FlavorConfig instance.

    Returns:
        FlavorConfig: The global configuration instance
    """
    return _config_manager.get_config()


def set_flavor_config(config: FlavorConfig | None) -> None:
    """Set the global FlavorConfig instance.

    Args:
        config: The FlavorConfig instance to use globally, or None to reset
    """
    _config_manager.set_config(config)


def reset_flavor_config() -> None:
    """Reset the global configuration to force reload from environment."""
    _config_manager.reset_config()


# 🌶️📦🔚
