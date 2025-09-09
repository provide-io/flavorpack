"""Utility functions for flavor."""

# Re-export platform utilities (from foundation directly)
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
    # Platform utilities
    "get_os_name",
    "get_arch_name",
    "get_platform_string",
    "get_os_version",
    "get_cpu_type",
    "normalize_platform_components",
    # Subprocess utilities removed - use provide.foundation.process directly
    # XOR utilities
    "XOR_KEY",
    "xor_encode",
    "xor_decode",
]
