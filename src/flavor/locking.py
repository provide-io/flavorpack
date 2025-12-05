#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from provide.foundation.file.directory import ensure_dir
from provide.foundation.file.lock import FileLock


class LockError(Exception):
    """Error during lock operations."""

    pass


class LockManager:
    """Manages file-based locks for concurrent operations."""

    def __init__(self, lock_dir: Path | None = None) -> None:
        self.lock_dir = lock_dir or Path.home() / ".cache" / "flavor" / "locks"
        ensure_dir(self.lock_dir)
        self.held_locks: set[Path] = set()

    @contextmanager
    def lock(self, name: str, timeout: float = 30.0) -> Generator[Path, None, None]:
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

        file_lock = FileLock(lock_file, timeout=timeout)
        try:
            acquired = file_lock.acquire(blocking=True)
            if not acquired:
                raise LockError(f"Timeout acquiring lock: {name}")

            self.held_locks.add(lock_file)
            try:
                yield lock_file
            finally:
                file_lock.release()
                self.held_locks.discard(lock_file)
        except Exception as e:
            if "timeout" in str(e).lower():
                raise LockError(f"Timeout acquiring lock: {name}") from e
            raise

    def cleanup_all(self) -> None:
        """Clean up all held locks (for emergency cleanup)."""
        # Foundation FileLock handles cleanup automatically
        self.held_locks.clear()


# Global default instance
default_lock_manager = LockManager()

# 🌶️📦🔚
