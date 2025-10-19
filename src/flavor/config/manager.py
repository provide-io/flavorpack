# flavor/config/manager.py
#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""This module provides the configuration management logic for FlavorPack,
including environment variable loading and global configuration management.



    FlavorConfig,
    PathsConfig,
    SecurityConfig,
    SystemConfig,
    UVConfig,
)


def load_config_from_env(config_class: type) -> dict[str, Any]:
    """Load configuration values from environment variables.
