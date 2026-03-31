#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Centralized FLAVOR_* environment variable name constants.

All FLAVOR_* env var names must be referenced via these constants,
never as inline strings scattered throughout the codebase.
"""

# Paths / directories
CACHE_DIR = "FLAVOR_CACHE"  # Override cache directory
CONFIG_DIR = "FLAVOR_CONFIG_DIR"  # Override config directory
TRUSTED_KEYS_DIR = "FLAVOR_TRUSTED_KEYS_DIR"  # Override trusted keys directory

# Build tooling
BUILDER_BIN = "FLAVOR_BUILDER_BIN"  # Override builder binary path
LAUNCHER_BIN = "FLAVOR_LAUNCHER_BIN"  # Override launcher binary path

# Build behavior
WORKENV_BASE = "FLAVOR_WORKENV_BASE"  # Base directory for {workenv} resolution
WHEEL_CACHE = "FLAVOR_WHEEL_CACHE"  # Pre-built wheels directory (offline mode)
INCLUDE_BUILD_HOST = "FLAVOR_INCLUDE_BUILD_HOST"  # Include build host metadata (set to "1")

# 🌶️📦🔚
