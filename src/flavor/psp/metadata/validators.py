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
    _validate_required_fields(metadata)
    _validate_format_version(metadata)
    _validate_execution_fields(metadata)
    _validate_workenv_section(metadata)
    return True
