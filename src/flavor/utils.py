"""Utility functions for flavor."""

import platform


def get_platform_string() -> str:
    """Get normalized platform string in format 'os_arch'.
    
    Returns:
        str: Platform string like 'darwin_arm64' or 'linux_amd64'
    """
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    # Normalize architecture names
    arch_map = {
        "x86_64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",      # Already normalized
        "amd64": "amd64",      # Already normalized
    }
    
    machine = arch_map.get(machine, machine)
    
    return f"{system}_{machine}"