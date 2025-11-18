#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Environment variable management for PSPF/2025 packages.

Handles platform-specific environment variables and layered environment processing."""

from __future__ import annotations

from collections.abc import Callable
import fnmatch
from typing import Any

# Import from provide.foundation
from provide.foundation import get_logger
from provide.foundation.platform import (
    get_arch_name,
    get_cpu_type,
    get_os_name,
    get_os_version,
    get_platform_string,
)

plog = get_logger()


def process_runtime_env(env_map: dict[str, str], runtime_env: dict[str, Any]) -> None:
    """
    Process runtime environment configuration for PSPF/2025 packages.

    This function modifies the environment map in-place, applying runtime
    environment operations in a specific order to ensure correct behavior.
    This implementation aligns with the Rust and Go implementations for
    cross-language consistency in the PSPF/2025 format.

    Operations are processed in this order:
    1. Analyze pass patterns - Build list of variables to preserve
    2. unset - Remove specified variables (skipping those marked to preserve)
    3. map - Rename variables (old_name -> new_name)
    4. set - Set specific values (override or add new)
    5. pass verification - Check that required variables/patterns exist

    Pattern matching supports:
    - Exact matches: "PATH" matches only PATH
    - Glob patterns: "PYTHON_*" matches PYTHON_HOME, PYTHON_PATH, etc.
    - Wildcard: "*" matches all variables

    Args:
        env_map: Mutable environment variables dictionary to process.
                 This dict is modified in-place.
        runtime_env: Runtime environment configuration containing:
            - pass: List of patterns for variables to preserve/require
            - unset: List of patterns for variables to remove
            - map: Dict of old_name -> new_name mappings
            - set: Dict of variable -> value assignments

    Example:
        >>> env = {"FOO": "bar", "BAZ": "qux", "TEMP": "123"}
        >>> runtime = {
        ...     "pass": ["FOO", "BA*"],
        ...     "unset": ["TEMP"],
        ...     "map": {"FOO": "NEW_FOO"},
        ...     "set": {"CUSTOM": "value"}
        ... }
        >>> process_runtime_env(env, runtime)
        >>> # Result: {"NEW_FOO": "bar", "BAZ": "qux", "CUSTOM": "value"}

    Note:
        This function is called during package execution to prepare the
        environment for the packaged application. It ensures consistent
        environment handling across different platforms and launchers.
    """

    pass_patterns = runtime_env.get("pass", [])
    should_preserve = _create_preserve_checker(pass_patterns)

    _process_unset_operations(env_map, runtime_env, should_preserve)
    _process_map_operations(env_map, runtime_env, should_preserve)
    _process_set_operations(env_map, runtime_env)
    _verify_pass_requirements(pass_patterns, env_map)


def _create_preserve_checker(pass_patterns: list[str]) -> Callable[[str], bool]:
    """Create a function to check if a variable should be preserved."""

    def should_preserve(key: str) -> bool:
        """Check if a key matches any pass pattern."""
        for pattern in pass_patterns:
            # Exact match
            if pattern == key:
                return True
            # Glob pattern match
            if ("*" in pattern or "?" in pattern) and fnmatch.fnmatch(key, pattern):
                return True
        return False

    return should_preserve


def _process_unset_operations(
    env_map: dict[str, str], runtime_env: dict[str, Any], should_preserve: Callable[[str], bool]
) -> None:
    """Process unset operations first (highest priority)."""
    if not runtime_env.get("unset"):
        return

    unset_patterns = runtime_env["unset"]
    plog.debug(f"🗑️ Processing {len(unset_patterns)} unset patterns")

    for pattern in unset_patterns:
        if pattern == "*":
            _unset_all_except_preserved(env_map, should_preserve)
        elif "*" in pattern or "?" in pattern:
            _unset_glob_pattern(env_map, pattern, should_preserve)
        else:
            _unset_exact_match(env_map, pattern, should_preserve)


def _unset_all_except_preserved(env_map: dict[str, str], should_preserve: Callable[[str], bool]) -> None:
    """Unset all variables except those marked to preserve."""
    keys_to_remove = [k for k in env_map if not should_preserve(k)]
    for key in keys_to_remove:
        del env_map[key]
        plog.trace(f"  🗑️ Unset: {key}")


def _unset_glob_pattern(env_map: dict[str, str], pattern: str, should_preserve: Callable[[str], bool]) -> None:
    """Unset variables matching glob pattern."""
    keys_to_remove = [k for k in env_map if fnmatch.fnmatch(k, pattern) and not should_preserve(k)]
    for key in keys_to_remove:
        del env_map[key]
        plog.trace(f"  🗑️ Unset (glob): {key}")


def _unset_exact_match(env_map: dict[str, str], pattern: str, should_preserve: Callable[[str], bool]) -> None:
    """Unset variable with exact match."""
    if pattern in env_map and not should_preserve(pattern):
        del env_map[pattern]
        plog.debug(f"🗑️ Unset: {pattern}")


def _process_map_operations(
    env_map: dict[str, str], runtime_env: dict[str, Any], should_preserve: Callable[[str], bool]
) -> None:
    """Process map operations (variable renaming)."""
    if not runtime_env.get("map"):
        return

    map_ops = runtime_env["map"]
    plog.debug(f"🔄 Processing {len(map_ops)} map operations")

    for old_key, new_key in map_ops.items():
        if old_key in env_map and not should_preserve(old_key):
            env_map[new_key] = env_map.pop(old_key)
            plog.debug(f"🔄 Mapped: {old_key} -> {new_key}")


def _process_set_operations(env_map: dict[str, str], runtime_env: dict[str, Any]) -> None:
    """Process set operations (add/override variables)."""
    if not runtime_env.get("set"):
        return

    set_ops = runtime_env["set"]
    plog.debug(f"📝 Processing {len(set_ops)} set operations")

    for key, value in set_ops.items():
        env_map[key] = value
        plog.debug(f"📝 Set: {key} = '{value}'")


def _verify_pass_requirements(pass_patterns: list[str], env_map: dict[str, str]) -> None:
    """Verify all required pass patterns are satisfied."""
    if not pass_patterns:
        return

    missing = []
    for pattern in pass_patterns:
        # Only check exact matches for requirements
        if "*" not in pattern and "?" not in pattern and pattern not in env_map:
            missing.append(pattern)

    if missing:
        plog.warning(f"⚠️ Required environment variables not found: {', '.join(missing)}")


def set_platform_environment(env: dict[str, str]) -> None:
    """
    Set platform-specific environment variables.

    These variables are always set and cannot be overridden by user configuration.

    Variables set:
    - FLAVOR_OS: Operating system (darwin, linux, windows)
    - FLAVOR_ARCH: Architecture (amd64, arm64, x86, i386)
    - FLAVOR_PLATFORM: Combined OS_arch string
    - FLAVOR_OS_VERSION: OS version (if available)
    - FLAVOR_CPU_TYPE: CPU type/family (if available)

    Args:
        env: Environment dictionary to update
    """
    # Get platform information from centralized utilities
    os_name = get_os_name()
    arch_name = get_arch_name()
    platform_str = get_platform_string()

    # Set required platform variables (override any existing values)
    env["FLAVOR_OS"] = os_name
    env["FLAVOR_ARCH"] = arch_name
    env["FLAVOR_PLATFORM"] = platform_str

    # Try to get OS version
    os_version = get_os_version()
    if os_version:
        env["FLAVOR_OS_VERSION"] = os_version

    # Try to get CPU type
    cpu_type = get_cpu_type()
    if cpu_type:
        env["FLAVOR_CPU_TYPE"] = cpu_type


def apply_environment_layers(
    base_env: dict[str, str],
    runtime_env: dict[str, Any] | None = None,
    workenv_env: dict[str, str] | None = None,
    execution_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """
    Apply environment variable layers in order.

    Layers (applied in order):
    1. Runtime security layer (unset, pass, map, set operations)
    2. Workenv layer (workenv-specific paths)
    3. Execution layer (application-specific settings)
    4. Platform layer (automatic, highest priority)

    Args:
        base_env: Base environment variables
        runtime_env: Runtime security operations
        workenv_env: Workenv-specific variables
        execution_env: Execution-specific variables

    Returns:
        Final environment dictionary
    """
    result = base_env.copy()

    # Layer 1: Runtime security - use dedicated processor matching Rust/Go
    if runtime_env:
        process_runtime_env(result, runtime_env)

    # Layer 2: Workenv
    if workenv_env:
        result.update(workenv_env)

    # Layer 3: Execution
    if execution_env:
        result.update(execution_env)

    # Layer 4: Platform (automatic, always last)
    set_platform_environment(result)

    return result


# 🌶️📦🔚
