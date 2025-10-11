"""Disk space and filesystem utilities.

DEPRECATED: This module is a compatibility shim. Import directly from:
    from provide.foundation.file import (
        check_disk_space,
        get_available_space,
        get_disk_usage,
        format_bytes,
    )
"""

from pathlib import Path

from provide.foundation.file import (
    check_disk_space as _check_disk_space,
    ensure_dir,
    get_available_space as _get_available_space,
)


def check_disk_space(path: Path, required_bytes: int) -> None:
    """Check if there's enough disk space available.

    Args:
        path: Directory path to check (or parent if it doesn't exist)
        required_bytes: Number of bytes required

    Raises:
        OSError: If insufficient disk space is available

    Note:
        This wraps foundation's check_disk_space with raise_on_insufficient=True
        to maintain backward compatibility with flavorpack's original API.
    """
    # Foundation's version has raise_on_insufficient parameter,
    # flavorpack's original always raises
    _check_disk_space(path, required_bytes, raise_on_insufficient=True)


def get_available_space(path: Path) -> int | None:
    """Get available disk space in bytes.

    Args:
        path: Directory path to check

    Returns:
        Available bytes or None if unable to determine
    """
    return _get_available_space(path)


def ensure_directory(path: Path, mode: int = 0o700) -> None:
    """Create directory with specified permissions if it doesn't exist.

    Args:
        path: Directory path to create
        mode: Unix file permissions (default: user-only)
    """
    # Use foundation's ensure_dir which does the same thing
    ensure_dir(path, mode=mode)


__all__ = [
    "check_disk_space",
    "ensure_directory",
    "get_available_space",
]
