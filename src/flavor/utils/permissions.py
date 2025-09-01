"""File permission utilities."""

import os
from pathlib import Path

from pyvider.telemetry import logger

from flavor.psp.format_2025.constants import (
    DEFAULT_DIR_PERMS,
    DEFAULT_EXECUTABLE_PERMS,
    DEFAULT_FILE_PERMS,
)


def parse_permissions(perms_str: str | None) -> int:
    """Parse permission string to octal integer.
    
    Args:
        perms_str: Permission string like "0755" or "755"
        
    Returns:
        Permission as integer, or DEFAULT_FILE_PERMS if invalid
    """
    if not perms_str:
        return DEFAULT_FILE_PERMS
        
    try:
        # Remove leading '0' or '0o' if present
        perms_str = perms_str.lstrip("0o")
        return int(perms_str, 8)
    except (ValueError, TypeError):
        logger.warning(f"Invalid permission string: {perms_str}, using default")
        return DEFAULT_FILE_PERMS


def set_file_permissions(path: Path, mode: int) -> None:
    """Set file permissions safely.
    
    Args:
        path: File path
        mode: Unix permission mode
    """
    try:
        os.chmod(path, mode)
        logger.debug(f"Set permissions {oct(mode)} on {path}")
    except OSError as e:
        logger.warning(f"Could not set permissions on {path}: {e}")


def ensure_secure_permissions(path: Path, is_executable: bool = False) -> None:
    """Apply secure default permissions to a file or directory.
    
    Args:
        path: Path to file or directory
        is_executable: Whether file should be executable
    """
    if path.is_dir():
        mode = DEFAULT_DIR_PERMS
    elif is_executable:
        mode = DEFAULT_EXECUTABLE_PERMS
    else:
        mode = DEFAULT_FILE_PERMS
    
    set_file_permissions(path, mode)


def get_permissions(path: Path) -> int:
    """Get current file permissions.
    
    Args:
        path: File path
        
    Returns:
        Permission bits as integer
    """
    try:
        return path.stat().st_mode & 0o777
    except OSError:
        return 0


def format_permissions(mode: int) -> str:
    """Format permission bits as octal string.
    
    Args:
        mode: Permission bits
        
    Returns:
        Formatted string like "0755"
    """
    return f"0{mode:03o}"