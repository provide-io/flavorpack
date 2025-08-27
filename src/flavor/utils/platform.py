"""Platform detection and system information utilities."""

import platform
import re


def get_os_name() -> str:
    """Get normalized OS name.

    Returns:
        str: Normalized OS name (darwin, linux, windows)
    """
    os_name = platform.system().lower()
    if os_name in ("darwin", "macos"):
        return "darwin"
    return os_name


def get_arch_name() -> str:
    """Get normalized architecture name.

    Returns:
        str: Normalized architecture (amd64, arm64, x86, i386)
    """
    arch = platform.machine().lower()
    # Normalize common architectures
    if arch in ["x86_64", "amd64"]:
        return "amd64"
    elif arch in ["aarch64", "arm64"]:
        return "arm64"
    elif arch in ["i686", "i586", "i486"]:
        return "x86"
    return arch


def get_platform_string() -> str:
    """Get normalized platform string in format 'os_arch'.

    Returns:
        str: Platform string like 'darwin_arm64' or 'linux_amd64'
    """
    return f"{get_os_name()}_{get_arch_name()}"


def get_os_version() -> str | None:
    """Get OS version information.

    Returns:
        str | None: OS version string or None if unavailable
    """
    try:
        system = platform.system()

        if system == "Darwin":
            # macOS version
            mac_ver = platform.mac_ver()
            if mac_ver[0]:
                return mac_ver[0]
        elif system == "Linux":
            # Linux kernel version
            release = platform.release()
            if release:
                # Extract major.minor version
                parts = release.split(".")
                if len(parts) >= 2:
                    return f"{parts[0]}.{parts[1]}"
                return release
        elif system == "Windows":
            # Windows version
            version = platform.version()
            if version:
                return version

        # Fallback to platform.release()
        release = platform.release()
        if release:
            return release
    except Exception:
        pass

    return None


def get_cpu_type() -> str | None:
    """Get CPU type/family information.

    Returns:
        str | None: CPU type string or None if unavailable
    """
    try:
        processor = platform.processor()
        if processor:
            # Clean up common processor strings
            if "Intel" in processor:
                # Extract Intel CPU model
                if "Core" in processor:
                    match = re.search(r"Core\(TM\)\s+(\w+)", processor)
                    if match:
                        return f"Intel Core {match.group(1)}"
                return "Intel"
            elif "AMD" in processor:
                # Extract AMD CPU model
                if "Ryzen" in processor:
                    match = re.search(r"Ryzen\s+(\d+\s+\w+)", processor)
                    if match:
                        return f"AMD Ryzen {match.group(1)}"
                return "AMD"
            elif "Apple" in processor or "M1" in processor or "M2" in processor:
                # Apple Silicon
                match = re.search(r"(M\d+\w*)", processor)
                if match:
                    return f"Apple {match.group(1)}"
                return "Apple Silicon"
            elif processor:
                # Return cleaned processor string
                return processor.strip()
    except Exception:
        pass

    return None


def normalize_platform_components(os_name: str, arch_name: str) -> tuple[str, str]:
    """Normalize OS and architecture names to standard format.
    
    Args:
        os_name: Operating system name
        arch_name: Architecture name
        
    Returns:
        tuple: (normalized_os, normalized_arch)
    """
    # Normalize OS names
    os_map = {
        "linux": "linux",
        "darwin": "darwin",
        "macos": "darwin",
        "windows": "windows",
        "win32": "windows",
    }
    
    # Normalize architecture names
    arch_map = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
        "i686": "x86",
        "i586": "x86",
        "i486": "x86",
        "i386": "i386",
    }
    
    normalized_os = os_map.get(os_name.lower(), os_name.lower())
    normalized_arch = arch_map.get(arch_name.lower(), arch_name.lower())
    
    return normalized_os, normalized_arch


__all__ = [
    "get_os_name",
    "get_arch_name", 
    "get_platform_string",
    "get_os_version",
    "get_cpu_type",
    "normalize_platform_components",
]