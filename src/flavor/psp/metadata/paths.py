#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Path validation and normalization for PSPF metadata.

Ensures all paths in metadata use the {workenv} placeholder for portability.
This makes it clear to developers that paths are relative to the work environment."""

import os
from pathlib import Path
from typing import Any

from provide.foundation.file.directory import ensure_dir
from provide.foundation.platform import get_arch_name, get_os_name


def validate_metadata_path(path: str) -> str:
    """
    Ensure a path in metadata starts with {workenv}.

    This function normalizes paths to always use the {workenv} placeholder,
    making it clear that paths are relative to the work environment directory.

    Args:
        path: The path to validate

    Returns:
        Path starting with {workenv}

    Examples:
        >>> validate_metadata_path("/usr/bin/python")
        "{workenv}/bin/python"
        >>> validate_metadata_path("bin/python")
        "{workenv}/bin/python"
        >>> validate_metadata_path("{workenv}/bin/python")
        "{workenv}/bin/python"
    """
    if not path:
        return path

    # Special case for placeholders that aren't paths
    if path.startswith("{") and path.endswith("}") and "/" not in path:
        # This is a placeholder like "{version}" or "{package_name}"
        return path

    # Absolute paths should be kept as-is (new design: "/" means absolute path)
    if path.startswith("/"):
        return path

    # If path doesn't start with {workenv}, add it
    if not path.startswith("{workenv}"):
        # Handle some special cases
        if path.startswith("workenv/"):
            # Replace literal "workenv/" with "{workenv}/"
            path = "{workenv}/" + path[8:]
        elif path == "." or path == "./":
            # Current directory is workenv root
            path = "{workenv}"
        elif path.startswith("./"):
            # Relative to workenv root
            path = "{workenv}/" + path[2:]
        else:
            # Standard case - prepend {workenv}/
            path = f"{{workenv}}/{path}"

    # Clean up any double slashes
    while "//" in path:
        path = path.replace("//", "/")

    # Ensure {workenv} doesn't end with a slash unless it's the whole path
    if path == "{workenv}/":
        path = "{workenv}"

    return path


def validate_metadata_dict(metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively validate all paths in a metadata dictionary.

    This function walks through the metadata structure and ensures all
    path-like values use the {workenv} placeholder.

    Args:
        metadata: The metadata dictionary to validate

    Returns:
        Metadata with all paths validated
    """
    # Keys that typically contain file paths
    PATH_KEYS = {
        "command",
        "check_file",
        "path",
        "source",
        "target",
        "destination",
        "executable",
        "script",
    }

    # Keys that contain path patterns or templates
    PATTERN_KEYS = {"pattern", "enumerate"}

    result: dict[str, Any] = {}

    for key, value in metadata.items():
        if key == "workenv" and isinstance(value, dict):
            # Special case: workenv section needs special handling
            # - directories: paths are relative to workenv (no {workenv} prefix)
            # - env: values should have {workenv} placeholders
            workenv_result = {}
            if "directories" in value:
                # Keep directory paths as-is (they're relative)
                workenv_result["directories"] = value["directories"]
            if "env" in value:
                # Validate env values to ensure they use {workenv}
                workenv_result["env"] = validate_metadata_dict(value["env"])
            result[key] = workenv_result
        elif key in PATH_KEYS and isinstance(value, str):
            # This is a path field - validate it
            validated_path = validate_metadata_path(value)
            result[key] = validated_path
        elif key in PATTERN_KEYS and isinstance(value, dict) and "path" in value:
            # Special case for enumerate patterns
            result[key] = {**value, "path": validate_metadata_path(value["path"])}
        elif isinstance(value, dict):
            # Recurse into nested dictionaries
            result[key] = validate_metadata_dict(value)
        elif isinstance(value, list):
            # Handle lists (may contain dicts or strings)
            validated_list = validate_metadata_list(value, key in PATH_KEYS)
            result[key] = validated_list
        else:
            # Keep as-is
            result[key] = value

    return result


def validate_metadata_list(items: list[Any], is_path_list: bool = False) -> list[Any]:
    """
    Validate items in a list, handling both dict and string items.

    Args:
        items: The list to validate
        is_path_list: If True, treat string items as paths

    Returns:
        List with validated items
    """
    result: list[Any] = []

    for item in items:
        if isinstance(item, dict):
            # Recurse into dictionaries
            result.append(validate_metadata_dict(item))
        elif isinstance(item, str) and is_path_list:
            # This is a path string
            result.append(validate_metadata_path(item))
        else:
            # Keep as-is
            result.append(item)

    return result


def expand_workenv_path(path: str, workenv_dir: str) -> str:
    """
    Expand a {workenv} path to an actual filesystem path.

    This is used at runtime to convert metadata paths to real paths.

    Args:
        path: Path containing {workenv} placeholder
        workenv_dir: Actual workenv directory path

    Returns:
        Expanded path

    Examples:
        >>> expand_workenv_path("{workenv}/bin/python", "/tmp/pspf/work123")
        "/tmp/pspf/work123/bin/python"
    """
    if "{workenv}" in path:
        return path.replace("{workenv}", workenv_dir)
    return path


def make_relative_to_workenv(absolute_path: str, workenv_dir: str) -> str:
    """
    Convert an absolute path to a {workenv}-relative path.

    This is useful when capturing paths during build time.

    Args:
        absolute_path: The absolute path to convert
        workenv_dir: The workenv directory path

    Returns:
        Path with {workenv} placeholder

    Examples:
        >>> make_relative_to_workenv("/tmp/build/bin/python", "/tmp/build")
        "{workenv}/bin/python"
    """
    # Normalize paths
    absolute_path = os.path.normpath(absolute_path)
    workenv_dir = os.path.normpath(workenv_dir)

    # Check if path is under workenv
    if absolute_path.startswith(workenv_dir):
        # Get relative path
        relpath = os.path.relpath(absolute_path, workenv_dir)
        if relpath == ".":
            return "{workenv}"
        return f"{{workenv}}/{relpath}"

    # Path is not under workenv - just return with {workenv} prefix
    # This shouldn't normally happen but handle gracefully
    return validate_metadata_path(absolute_path)


def substitute_placeholders(path: str, workenv_path: Path) -> str:
    """
    Substitute placeholders in a path string.

    Supported placeholders:
    - {workenv}: Work environment directory
    - {os}: Operating system (darwin, linux, windows)
    - {arch}: Architecture (amd64, arm64, x86, i386)
    - {platform}: Combined OS_arch string

    Args:
        path: Path string with placeholders
        workenv_path: Path to workenv directory

    Returns:
        Path with placeholders substituted
    """
    if not path:
        return path

    # Get platform values
    os_name = get_os_name()
    arch_name = get_arch_name()
    platform_str = f"{os_name}_{arch_name}"

    # Substitute placeholders
    result = path
    if "{workenv}" in result:
        result = result.replace("{workenv}", str(workenv_path))
    if "{os}" in result:
        result = result.replace("{os}", os_name)
    if "{arch}" in result:
        result = result.replace("{arch}", arch_name)
    if "{platform}" in result:
        result = result.replace("{platform}", platform_str)

    return result


def validate_workenv_paths(directories: list[dict[str, str]]) -> bool:
    """
    Validate that all workenv directory paths start with {workenv}.

    Args:
        directories: List of directory configurations

    Returns:
        True if valid

    Raises:
        ValueError: If any path doesn't start with {workenv}
    """
    for dir_info in directories:
        path = dir_info.get("path", "")
        if not path.startswith("{workenv}"):
            raise ValueError(f"Workenv directory path must start with {{workenv}}: {path}")
    return True


def parse_mode(mode_str: str) -> int:
    """
    Parse a mode string into an integer.

    Args:
        mode_str: Mode as string (e.g., "0755", "755", "0o755")

    Returns:
        Mode as integer

    Raises:
        ValueError: If mode is invalid
    """
    if not mode_str:
        return 0o755  # Default

    # Remove any "0o" prefix
    if mode_str.startswith("0o"):
        mode_str = mode_str[2:]

    # Try to parse as octal
    try:
        mode = int(mode_str, 8)

        # Validate range
        if mode < 0 or mode > 0o777:
            raise ValueError(f"Invalid mode value: {mode_str}")

        return mode
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid mode: {mode_str}") from e


def apply_umask(umask_value: int) -> None:
    """
    Apply a umask value to the process.

    Args:
        umask_value: Umask value to apply
    """
    os.umask(umask_value)


def create_workenv_directories(
    directories: list[dict[str, str]], workenv: Path, umask: str | None = None
) -> None:
    """
    Create workenv directories with specified permissions.

    Args:
        directories: List of directory configurations
        workenv: Path to workenv root
        umask: Optional umask to apply
    """
    # Apply umask if specified
    old_umask = None
    if umask:
        old_umask = os.umask(parse_mode(umask))

    try:
        for dir_info in directories:
            path_str = dir_info.get("path", "")
            mode_str = dir_info.get("mode", "")

            # Substitute placeholders
            full_path = substitute_placeholders(path_str, workenv)
            dir_path = Path(full_path)

            # Create directory
            ensure_dir(dir_path)

            # Set permissions if specified
            if mode_str:
                mode = parse_mode(mode_str)
                dir_path.chmod(mode)
            elif not dir_path.exists():
                # Apply default permissions for new directories
                # Default is 0777 & ~umask
                default_mode = 0o777 & ~parse_mode(umask) if umask else 0o700  # Default to owner-only
                dir_path.chmod(default_mode)
    finally:
        # Restore original umask
        if old_umask is not None:
            os.umask(old_umask)


# 🌶️📦🔚
