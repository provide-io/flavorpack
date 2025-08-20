#!/usr/bin/env python3
"""
Environment variable management for PSPF/2025 packages.

Handles platform-specific environment variables and layered environment processing.
"""

import platform
from typing import Any

from flavor.utils import get_cpu_type


def get_normalized_os() -> str:
    """Get normalized OS name."""
    os_name = platform.system().lower()
    if os_name == "darwin":
        return "darwin"
    return os_name


def get_normalized_arch() -> str:
    """Get normalized architecture name."""
    arch = platform.machine().lower()
    if arch in ["x86_64", "amd64"]:
        return "amd64"
    elif arch in ["aarch64", "arm64"]:
        return "arm64"
    elif arch in ["i686", "i586", "i486"]:
        return "x86"
    return arch


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
    # Get platform information
    os_name = get_normalized_os()
    arch_name = get_normalized_arch()
    platform_str = f"{os_name}_{arch_name}"

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


def get_os_version() -> str | None:
    """
    Get OS version information.

    Returns:
        OS version string or None if unavailable
    """
    try:
        system = platform.system()

        if system == "Darwin":
            # macOS version
            mac_ver = platform.mac_ver()
            if mac_ver[0]:
                return mac_ver[0]
        elif system == "Linux":
            # Linux kernel version
            release = platform.release()
            if release:
                # Extract major.minor version
                parts = release.split(".")
                if len(parts) >= 2:
                    return f"{parts[0]}.{parts[1]}"
                return release
        elif system == "Windows":
            # Windows version
            version = platform.version()
            if version:
                return version

        # Fallback to platform.release()
        release = platform.release()
        if release:
            return release
    except Exception:
        pass

    return None


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
