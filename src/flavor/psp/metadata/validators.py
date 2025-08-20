#!/usr/bin/env python3
"""
Metadata validation functions for PSP packages.

This module contains validation logic for package metadata structures.
"""

from typing import Any


def _parse_octal_value(value: str, field_name: str) -> int:
    """
    Parse an octal string value.

    Args:
        value: The octal string to parse
        field_name: Name of the field for error messages

    Returns:
        Parsed octal value as integer

    Raises:
        ValueError: If value is invalid
    """
    if not isinstance(value, str):
        raise ValueError(f"Invalid {field_name} type: {type(value)}")

    try:
        # Try to parse as octal
        if value.startswith("0o"):
            octal_val = int(value[2:], 8)
        elif value.startswith("0"):
            octal_val = int(value, 8)
        else:
            # Must be digits only for plain octal
            if not value.isdigit():
                raise ValueError(f"Invalid {field_name}: {value}")
            octal_val = int(value, 8)

        # Check valid range (0-0777)
        if octal_val < 0 or octal_val > 0o777:
            raise ValueError(f"Invalid {field_name} value: {value}")

        return octal_val
    except ValueError as e:
        if f"Invalid {field_name}" in str(e):
            raise
        raise ValueError(f"Invalid {field_name}: {value}") from e


def _validate_format(metadata: dict[str, Any]) -> None:
    """
    Validate format field and check for deprecated fields.

    Args:
        metadata: The metadata dictionary to validate

    Raises:
        ValueError: If format is invalid or deprecated fields are used
    """
    # Check required fields
    if "format" not in metadata:
        raise ValueError("Missing required field: format")

    # Check format version
    if metadata["format"] not in ["PSPF/2025"]:
        raise ValueError(f"Unsupported format: {metadata['format']}")

    # Check for old field names
    if "execution" in metadata and "environment" in metadata["execution"]:
        raise ValueError("Use 'env' instead of 'environment' in execution section")


def _validate_mode(mode: str) -> None:
    """
    Validate a directory mode value.

    Args:
        mode: The mode string to validate

    Raises:
        ValueError: If mode is invalid
    """
    _parse_octal_value(mode, "mode")


def _validate_workenv_directories(metadata: dict[str, Any]) -> None:
    """
    Validate workenv directories configuration.

    Args:
        metadata: The metadata dictionary to validate

    Raises:
        ValueError: If directories configuration is invalid
    """
    if "workenv" not in metadata or "directories" not in metadata["workenv"]:
        return

    dirs = metadata["workenv"]["directories"]
    for dir_info in dirs:
        # Validate path
        if "path" in dir_info:
            if not dir_info["path"].startswith("{workenv}"):
                raise ValueError(
                    f"Workenv directory path must start with {{workenv}}: {dir_info['path']}"
                )

        # Validate mode if present
        if "mode" in dir_info:
            _validate_mode(dir_info["mode"])


def _validate_umask(metadata: dict[str, Any]) -> None:
    """
    Validate umask configuration.

    Args:
        metadata: The metadata dictionary to validate

    Raises:
        ValueError: If umask is invalid
    """
    if "workenv" not in metadata or "umask" not in metadata["workenv"]:
        return

    umask = metadata["workenv"]["umask"]
    _parse_octal_value(umask, "umask")


def validate_metadata(metadata: dict[str, Any]) -> bool:
    """
    Validate a complete metadata structure.

    Args:
        metadata: The metadata dictionary to validate

    Returns:
        True if valid

    Raises:
        ValueError: If metadata is invalid
    """
    # Validate format and check for deprecated fields
    _validate_format(metadata)

    # Validate workenv directories
    _validate_workenv_directories(metadata)

    # Validate umask if present
    _validate_umask(metadata)

    return True
