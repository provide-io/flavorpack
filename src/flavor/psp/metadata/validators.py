#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Metadata validation functions for PSP packages.

This module contains validation logic for package metadata structures."""

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
    _validate_required_fields(metadata)
    _validate_format_version(metadata)
    _validate_execution_fields(metadata)
    _validate_workenv_section(metadata)
    return True


def _validate_required_fields(metadata: dict[str, Any]) -> None:
    """Validate required metadata fields."""
    if "format" not in metadata:
        raise ValueError("Missing required field: format")


def _validate_format_version(metadata: dict[str, Any]) -> None:
    """Validate format version."""
    if metadata["format"] not in ["PSPF/2025"]:
        raise ValueError(f"Unsupported format: {metadata['format']}")


def _validate_execution_fields(metadata: dict[str, Any]) -> None:
    """Validate execution section for deprecated fields."""
    if "execution" in metadata and "environment" in metadata["execution"]:
        raise ValueError("Use 'env' instead of 'environment' in execution section")


def _validate_workenv_section(metadata: dict[str, Any]) -> None:
    """Validate workenv section including directories and umask."""
    if "workenv" not in metadata:
        return

    workenv = metadata["workenv"]

    if "directories" in workenv:
        _validate_workenv_directories(workenv["directories"])

    if "umask" in workenv:
        _validate_umask(workenv["umask"])


def _validate_workenv_directories(directories: list[dict[str, Any]]) -> None:
    """Validate workenv directories configuration."""
    for dir_info in directories:
        if "path" in dir_info and not dir_info["path"].startswith("{workenv}"):
            raise ValueError(f"Workenv directory path must start with {{workenv}}: {dir_info['path']}")
        if "mode" in dir_info:
            _validate_mode(dir_info["mode"])


def _validate_mode(mode: Any) -> None:
    """Validate file/directory mode format."""
    if not isinstance(mode, str):
        raise ValueError(f"Invalid mode type: {type(mode)}")

    try:
        mode_val = _parse_octal_mode(mode)
        # Check valid range (0-0777)
        if mode_val < 0 or mode_val > 0o777:
            raise ValueError(f"Invalid mode: {mode}")
    except (ValueError, TypeError) as e:
        if "Invalid mode" in str(e):
            raise
        raise ValueError(f"Invalid mode: {mode}") from e


def _parse_octal_mode(mode: str) -> int:
    """Parse mode string as octal value."""
    if mode.startswith("0o"):
        return int(mode[2:], 8)
    elif mode.startswith("0"):
        return int(mode, 8)
    else:
        # Must be digits only for plain octal
        if not mode.isdigit():
            raise ValueError(f"Invalid mode: {mode}")
        return int(mode, 8)


def _validate_umask(umask: Any) -> None:
    """Validate umask value."""
    if not isinstance(umask, str):
        raise ValueError(f"Invalid umask type: {type(umask)}")

    try:
        val = _parse_octal_umask(umask)
        if val < 0 or val > 0o777:
            raise ValueError(f"Invalid umask value: {umask}")
    except ValueError as e:
        raise ValueError(f"Invalid umask: {umask}") from e


def _parse_octal_umask(umask: str) -> int:
    """Parse umask string as octal value."""
    if umask.startswith("0o"):
        return int(umask[2:], 8)
    elif umask.startswith("0"):
        return int(umask, 8)
    else:
        return int(umask, 8)


# 🌶️📦🔚
