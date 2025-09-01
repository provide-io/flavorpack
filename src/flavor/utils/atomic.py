"""Atomic file operations utilities."""

import os
import tempfile
from pathlib import Path

from pyvider.telemetry import logger


def atomic_write(path: Path, data: bytes, mode: int | None = None) -> None:
    """Write file atomically using temp file and rename.
    
    Args:
        path: Target file path
        data: Data to write
        mode: Optional file permissions
    """
    # Create temp file in same directory for atomic rename
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    fd, temp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp"
    )
    
    try:
        # Write data to temp file
        os.write(fd, data)
        os.close(fd)
        
        # Set permissions if specified
        if mode is not None:
            os.chmod(temp_path, mode)
        
        # Atomic rename
        os.replace(temp_path, path)
        logger.debug(f"Atomically wrote {len(data)} bytes to {path}")
        
    except Exception:
        # Clean up temp file on error
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def atomic_replace(path: Path, data: bytes) -> None:
    """Replace existing file atomically, preserving permissions.
    
    Args:
        path: Target file path
        data: New data
    """
    path = Path(path)
    
    # Get existing permissions if file exists
    mode = None
    if path.exists():
        try:
            mode = path.stat().st_mode & 0o777
        except OSError:
            pass
    
    atomic_write(path, data, mode)


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8", mode: int | None = None) -> None:
    """Write text file atomically.
    
    Args:
        path: Target file path
        text: Text content
        encoding: Text encoding
        mode: Optional file permissions
    """
    atomic_write(path, text.encode(encoding), mode)


def safe_unlink(path: Path) -> bool:
    """Safely remove a file, ignoring if it doesn't exist.
    
    Args:
        path: File to remove
        
    Returns:
        True if file was removed, False if it didn't exist
    """
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError as e:
        logger.warning(f"Could not remove {path}: {e}")
        return False