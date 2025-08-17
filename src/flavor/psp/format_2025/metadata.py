#!/usr/bin/env python3
"""
PSPF/2025 metadata validation.

This module provides backward compatibility by importing from the new
metadata module structure.
"""

from flavor.psp.metadata.formats.pspf_2025 import validate_metadata

__all__ = ["validate_metadata"]