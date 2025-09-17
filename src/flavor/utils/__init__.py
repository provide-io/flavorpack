"""Utility functions for flavor."""

# Re-export platform utilities (from foundation directly)
from __future__ import annotations

from provide.foundation.platform import (
    get_arch_name,
    get_cpu_type,
    get_os_name,
    get_os_version,
    get_platform_string,
    normalize_platform_components,
)

# Subprocess utilities removed - use provide.foundation.process directly
# Re-export XOR utilities
from flavor.utils.xor import (
    XOR_KEY,
    xor_decode,
    xor_encode,
)

__all__ = [
    # Subprocess utilities removed - use provide.foundation.process directly
    # XOR utilities
    "XOR_KEY",
    "get_arch_name",
    "get_cpu_type",
    # Platform utilities
    "get_os_name",
    "get_os_version",
    "get_platform_string",
    "normalize_platform_components",
    "xor_decode",
    "xor_encode",
]
