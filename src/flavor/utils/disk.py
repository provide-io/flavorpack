"""Disk space and filesystem utilities."""

import os
from pathlib import Path

from pyvider.telemetry import logger


def check_disk_space(path: Path, required_bytes: int) -> None:
    """Check if there's enough disk space available.
    
    Args:
        path: Directory path to check (or parent if it doesn't exist)
        required_bytes: Number of bytes required
        
    Raises:
        OSError: If insufficient disk space is available
    """
    try:
        # Use parent directory if path doesn't exist yet
        check_path = path if path.exists() else path.parent
        
        # Get available disk space using os.statvfs (Unix-like systems)
        stat_result = os.statvfs(check_path)
        available = stat_result.f_bavail * stat_result.f_frsize
        
        # Convert to GB for human-readable logging
        required_gb = required_bytes / (1024 * 1024 * 1024)
        available_gb = available / (1024 * 1024 * 1024)
        
        logger.debug(f"💾 Disk space check: need {required_gb:.2f} GB, have {available_gb:.2f} GB")
        
        if available < required_bytes:
            logger.error(f"❌ Insufficient disk space: need {required_gb:.2f} GB, have {available_gb:.2f} GB")
            raise OSError(f"Insufficient disk space: need {required_gb:.2f} GB, have {available_gb:.2f} GB")
            
    except (AttributeError, OSError) as e:
        # statvfs not available on Windows or check failed
        logger.warning(f"⚠️ Could not check disk space: {e}")
        # Don't fail if we can't check (matches Go/Rust behavior)


def get_available_space(path: Path) -> int | None:
    """Get available disk space in bytes.
    
    Args:
        path: Directory path to check
        
    Returns:
        Available bytes or None if unable to determine
    """
    try:
        check_path = path if path.exists() else path.parent
        stat_result = os.statvfs(check_path)
        return stat_result.f_bavail * stat_result.f_frsize
    except (AttributeError, OSError):
        return None


def ensure_directory(path: Path, mode: int = 0o700) -> None:
    """Create directory with specified permissions if it doesn't exist.
    
    Args:
        path: Directory path to create
        mode: Unix file permissions (default: user-only)
    """
    path.mkdir(parents=True, exist_ok=True, mode=mode)