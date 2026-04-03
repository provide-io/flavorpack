#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""XDG-compliant config directory resolution for Flavor."""

from __future__ import annotations

from pathlib import Path
import sys

from provide.foundation.utils.environment import get_str

from flavor.config.defaults import ENV_CONFIG_DIR, ENV_TRUSTED_KEYS_DIR
from flavor.console import get_command_logger

log = get_command_logger("config.dirs")


def get_config_dir() -> Path:
    """Get the user-level config directory for Flavor.

    Uses XDG Base Directory specification:
    - FLAVOR_CONFIG_DIR environment variable if set
    - XDG_CONFIG_HOME/flavor if XDG_CONFIG_HOME is set
    - ~/.config/flavor by default
    """
    # Check FLAVOR_CONFIG_DIR override first
    config_dir = get_str(ENV_CONFIG_DIR)
    if config_dir:
        if log.is_trace_enabled():
            log.trace(f"🗂️ Using FLAVOR_CONFIG_DIR: {config_dir}")
        return Path(config_dir)

    # Use XDG_CONFIG_HOME if set (respects XDG Base Directory standard)
    xdg_config = get_str("XDG_CONFIG_HOME")
    if xdg_config:
        result = Path(xdg_config) / "flavor"
        if log.is_trace_enabled():
            log.trace(f"🗂️ Using XDG_CONFIG_HOME: {result}")
        return result

    # Default to ~/.config/flavor
    default = Path.home() / ".config" / "flavor"
    if log.is_trace_enabled():
        log.trace(f"🗂️ Using default config dir: {default}")
    return default


def get_system_config_dir() -> Path:
    """Get the system-level config directory for Flavor.

    - Linux/macOS: /etc/flavor
    - Windows: %PROGRAMDATA%\\flavor
    """
    if sys.platform == "win32":
        programdata = get_str("PROGRAMDATA") or "C:\\ProgramData"
        result = Path(programdata) / "flavor"
        if log.is_trace_enabled():
            log.trace(f"🗂️ Using Windows system config dir: {result}")
        return result

    result = Path("/etc/flavor")
    if log.is_trace_enabled():
        log.trace(f"🗂️ Using system config dir: {result}")
    return result


def get_trusted_keys_dir(*, system: bool = False) -> Path:
    """Get the trusted keys directory for Flavor.

    Args:
        system: If True, return the system-level trusted keys directory.
                If False (default), check FLAVOR_TRUSTED_KEYS_DIR env var first,
                then fall back to get_config_dir() / "trusted-keys".
    """
    if system:
        result = get_system_config_dir() / "trusted-keys"
        if log.is_trace_enabled():
            log.trace(f"🗂️ Using system trusted keys dir: {result}")
        return result

    # Check FLAVOR_TRUSTED_KEYS_DIR override first
    trusted_keys_dir = get_str(ENV_TRUSTED_KEYS_DIR)
    if trusted_keys_dir:
        if log.is_trace_enabled():
            log.trace(f"🗂️ Using FLAVOR_TRUSTED_KEYS_DIR: {trusted_keys_dir}")
        return Path(trusted_keys_dir)

    result = get_config_dir() / "trusted-keys"
    if log.is_trace_enabled():
        log.trace(f"🗂️ Using default trusted keys dir: {result}")
    return result


def get_policy_file(*, system: bool = False) -> Path:
    """Get the policy file path for Flavor.

    Returns the path to policy.json in the appropriate config directory.

    Args:
        system: If True, return the system-level policy file.
                If False (default), return the user-level policy file.
    """
    config_dir = get_system_config_dir() if system else get_config_dir()
    result = config_dir / "policy.json"
    if log.is_trace_enabled():
        log.trace(f"🗂️ Using {'system' if system else 'user'} policy file: {result}")
    return result


# 🌶️📦🔚
