"""Platform detection and system information utilities using foundation."""

# Import from provide.foundation for platform detection
from provide.foundation.platform import (
    get_arch_name,
    get_cpu_type, 
    get_os_name,
    get_os_version,
    get_platform_string,
    normalize_platform_components,
)

# Re-export foundation platform functions
__all__ = [
    "get_arch_name",
    "get_cpu_type",
    "get_os_name",
    "get_os_version", 
    "get_platform_string",
    "normalize_platform_components",
]
