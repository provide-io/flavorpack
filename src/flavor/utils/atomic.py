"""Atomic file operations utilities.

This module now wraps provide.foundation.file for backward compatibility.
All new code should import directly from provide.foundation.file.
"""

from pathlib import Path

from provide.foundation.file import (
    atomic_write as _atomic_write,
    atomic_replace as _atomic_replace,
    atomic_write_text as _atomic_write_text,
    safe_delete as _safe_delete,
)


def atomic_write(path: Path, data: bytes, mode: int | None = None) -> None:
    """Write file atomically using temp file and rename.
    
    Args:
        path: Target file path
        data: Data to write
        mode: Optional file permissions
    """
    _atomic_write(path, data, mode=mode)


def atomic_replace(path: Path, data: bytes) -> None:
    """Replace existing file atomically, preserving permissions.
    
    Args:
        path: Target file path
        data: New data
    """
    _atomic_replace(path, data)


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8", mode: int | None = None) -> None:
    """Write text file atomically.
    
    Args:
        path: Target file path
        text: Text content
        encoding: Text encoding
        mode: Optional file permissions
    """
    _atomic_write_text(path, text, encoding=encoding, mode=mode)


def safe_unlink(path: Path) -> bool:
    """Safely remove a file, ignoring if it doesn't exist.
    
    Args:
        path: File to remove
        
    Returns:
        True if file was removed, False if it didn't exist
    """
    return _safe_delete(path, missing_ok=True)