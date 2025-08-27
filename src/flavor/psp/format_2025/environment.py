#!/usr/bin/env python3
"""
Environment variable management for PSPF/2025 packages.

Handles platform-specific environment variables and layered environment processing.
"""

from typing import Any

# Import platform utilities from centralized location
from flavor.utils.platform import (
    get_arch_name,
    get_cpu_type,
    get_os_name,
    get_os_version,
    get_platform_string,
)


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

    # Layer 1: Runtime security
    if runtime_env:
        # Unset variables
        if "unset" in runtime_env:
            for var in runtime_env["unset"]:
                result.pop(var, None)

        # Pass (whitelist) variables
        if "pass" in runtime_env:
            # Create new dict with only whitelisted vars
            passed = {}
            for var in runtime_env["pass"]:
                if var in result:
                    passed[var] = result[var]
            result = passed

        # Map (rename) variables
        if "map" in runtime_env:
            for old_name, new_name in runtime_env["map"].items():
                if old_name in result:
                    result[new_name] = result.pop(old_name)

        # Set variables
        if "set" in runtime_env:
            result.update(runtime_env["set"])

    # Layer 2: Workenv
    if workenv_env:
        result.update(workenv_env)

    # Layer 3: Execution
    if execution_env:
        result.update(execution_env)

    # Layer 4: Platform (automatic, always last)
    set_platform_environment(result)

    return result
