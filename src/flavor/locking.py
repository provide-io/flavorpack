"""File-based locking mechanism for Flavor."""

from contextlib import contextmanager, suppress
import json
import logging
import os
from pathlib import Path
import tempfile
import time

import psutil

logger = logging.getLogger(__name__)


class LockError(Exception):
    """Error during lock operations."""

    pass


class LockManager:
    """Manages file-based locks for concurrent operations."""

    def __init__(self, lock_dir: Path | None = None) -> None:
        self.lock_dir = lock_dir or Path(tempfile.gettempdir()) / "flavor" / "locks"
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        self.held_locks = set()

    @contextmanager
    def lock(self, name: str, timeout: float = 30.0):
        """
        Acquire a named lock.

        Args:
            name: Lock name
            timeout: Maximum time to wait for lock

        Yields:
            Lock file path

        Raises:
            LockError: When unable to acquire lock
        """
        lock_file = self.lock_dir / f"{name}.lock"
        start_time = time.time()

        while True:
            try:
                # Try to acquire lock
                if self._try_acquire(lock_file):
                    self.held_locks.add(lock_file)
                    try:
                        yield lock_file
                    finally:
                        self._release(lock_file)
                        self.held_locks.discard(lock_file)
                    break

                # Check timeout
                if time.time() - start_time > timeout:
                    raise LockError(f"Timeout acquiring lock: {name}")

                # Check for stale lock
                if self._is_stale(lock_file):
                    logger.warning(f"Removing stale lock: {lock_file}")
                    lock_file.unlink()
                    continue

                # Wait before retry
                time.sleep(0.1)

            except Exception as e:
                if not isinstance(e, LockError):
                    logger.error(f"Error acquiring lock: {e}")
                raise

    def _try_acquire(self, lock_file: Path) -> bool:
        """Try to acquire a lock file."""
        try:
            # Atomic creation with O_EXCL
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        except FileExistsError:
            return False

    def _release(self, lock_file: Path) -> None:
        """Release a lock file."""
        with suppress(FileNotFoundError):
            # Already released
            lock_file.unlink()

    def _is_stale(self, lock_file: Path) -> bool:
        """Check if a lock is stale (process no longer exists)."""
        try:
            with lock_file.open() as f:
                pid = int(f.read().strip())

            # Check if process exists
            if psutil.pid_exists(pid):
                try:
                    proc = psutil.Process(pid)
                    # Additional check: is it a flavor process?
                    return "flavor" not in proc.name().lower()
                except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                    return False
            return True

        except (OSError, json.JSONDecodeError, KeyError):
            return True  # Can't read lock file, assume stale

    def cleanup_all(self) -> None:
        """Clean up all held locks (for emergency cleanup)."""
        for lock_file in self.held_locks.copy():
            self._release(lock_file)
            self.held_locks.discard(lock_file)


# Global default instance
default_lock_manager = LockManager()
