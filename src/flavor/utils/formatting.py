#!/usr/bin/env python3
#
# flavor/utils/formatting.py
#
"""Formatting utilities for the flavor CLI - thin wrapper around foundation."""

from provide.foundation.utils.formatting import format_size

# Re-export for compatibility
__all__ = ["format_size"]
