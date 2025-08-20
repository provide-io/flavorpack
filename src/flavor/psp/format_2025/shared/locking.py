"""
File-based locking utilities for PSPF operations.
"""

import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def acquire_lock(lock_name: str, timeout: float = 30.0):
    """Acquire a file-based lock for concurrent operations.
    
    Args:
        lock_name: Name for the lock file (will be sanitized)
        timeout: Maximum time to wait for lock acquisition
        
    Yields:
        Path: Path to the lock file
        
    Raises:
        TimeoutError: If lock cannot be acquired within timeout
    """
    # Sanitize lock name to be filesystem-safe
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in lock_name)
    
    lock_path = Path(tempfile.gettempdir()) / "flavor" / "locks" / f"{safe_name}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    start_time = time.time()
    
    while True:
        try:
            # Try to acquire lock atomically
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            try:
                yield lock_path
            finally:
                lock_path.unlink(missing_ok=True)
            break
        except FileExistsError:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Timeout acquiring lock: {lock_name}")
            time.sleep(0.1)