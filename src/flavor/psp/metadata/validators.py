#!/usr/bin/env python3
"""
Metadata validation functions for PSP packages.

This module contains validation logic for package metadata structures.
"""

from typing import Any


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
    # Check required fields
    if "format" not in metadata:
        raise ValueError("Missing required field: format")

    # Check format version
    if metadata["format"] not in ["PSPF/2025"]:
        raise ValueError(f"Unsupported format: {metadata['format']}")

    # Check for old field names
    if "execution" in metadata and "environment" in metadata["execution"]:
        raise ValueError("Use 'env' instead of 'environment' in execution section")

    # Validate workenv directories
    if "workenv" in metadata and "directories" in metadata["workenv"]:
        dirs = metadata["workenv"]["directories"]
        for dir_info in dirs:
            if "path" in dir_info:
                if not dir_info["path"].startswith("{workenv}"):
                    raise ValueError(
                        f"Workenv directory path must start with {{workenv}}: {dir_info['path']}"
                    )
            if "mode" in dir_info:
                # Validate mode format
                mode = dir_info["mode"]
                if not isinstance(mode, str):
                    raise ValueError(f"Invalid mode type: {type(mode)}")
                try:
                    # Try to parse as octal
                    if mode.startswith("0o"):
                        mode_val = int(mode[2:], 8)
                    elif mode.startswith("0"):
                        mode_val = int(mode, 8)
                    else:
                        # Must be digits only for plain octal
                        if not mode.isdigit():
                            raise ValueError(f"Invalid mode: {mode}")
                        mode_val = int(mode, 8)
                    # Check valid range (0-0777)
                    if mode_val < 0 or mode_val > 0o777:
                        raise ValueError(f"Invalid mode: {mode}")
                except (ValueError, TypeError) as e:
                    if "Invalid mode" in str(e):
                        raise
                    raise ValueError(f"Invalid mode: {mode}") from e

    # Validate umask if present
    if "workenv" in metadata and "umask" in metadata["workenv"]:
        umask = metadata["workenv"]["umask"]
        if not isinstance(umask, str):
            raise ValueError(f"Invalid umask type: {type(umask)}")
        try:
            # Try to parse as octal
            if umask.startswith("0o"):
                val = int(umask[2:], 8)
            elif umask.startswith("0"):
                val = int(umask, 8)
            else:
                val = int(umask, 8)
            if val < 0 or val > 0o777:
                raise ValueError(f"Invalid umask value: {umask}")
        except ValueError as e:
            raise ValueError(f"Invalid umask: {umask}") from e

    return True
