#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Comprehensive tests for flavor.locking module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from flavor.locking import LockError, LockManager


class TestLockManager:
    """Test suite for LockManager class."""

    def test_init_default_lock_dir(self) -> None:
        """Test LockManager initialization with default lock directory."""
        manager = LockManager()
        expected_dir = Path.home() / ".cache" / "flavor" / "locks"
        assert manager.lock_dir == expected_dir
        assert manager.held_locks == set()

    def test_init_custom_lock_dir(self, tmp_path: Path) -> None:
        """Test LockManager initialization with custom lock directory."""
        custom_dir = tmp_path / "custom_locks"
        manager = LockManager(lock_dir=custom_dir)
        assert manager.lock_dir == custom_dir

    def test_lock_acquisition_success(self, tmp_path: Path) -> None:
        """Test successful lock acquisition and release."""
        manager = LockManager(lock_dir=tmp_path)

        with manager.lock("test_lock") as lock_file:
            assert lock_file == tmp_path / "test_lock.lock"
            assert lock_file in manager.held_locks

        # After context exit, lock should be released
        assert lock_file not in manager.held_locks

    def test_lock_creates_lock_file_path(self, tmp_path: Path) -> None:
        """Test that lock creates correct lock file path."""
        manager = LockManager(lock_dir=tmp_path)
        lock_name = "my_package"
        expected_path = tmp_path / f"{lock_name}.lock"

        with manager.lock(lock_name) as lock_file:
            assert lock_file == expected_path

    @patch("flavor.locking.FileLock")
    def test_lock_acquisition_with_timeout(self, mock_filelock_class: Mock, tmp_path: Path) -> None:
        """Test lock acquisition respects timeout parameter."""
        manager = LockManager(lock_dir=tmp_path)
        mock_lock = Mock()
        mock_lock.acquire.return_value = True
        mock_filelock_class.return_value = mock_lock

        with manager.lock("test_lock", timeout=10.0):
            pass

        # Verify FileLock was created with correct timeout
        call_args = mock_filelock_class.call_args
        assert call_args[1]["timeout"] == 10.0

    @patch("flavor.locking.FileLock")
    def test_lock_timeout_raises_error(self, mock_filelock_class: Mock, tmp_path: Path) -> None:
        """Test that lock timeout raises LockError."""
        manager = LockManager(lock_dir=tmp_path)
        mock_lock = Mock()
        # Simulate timeout - acquire returns False
        mock_lock.acquire.return_value = False
        mock_filelock_class.return_value = mock_lock

        with pytest.raises(LockError, match="Timeout acquiring lock: test_lock"), manager.lock("test_lock"):
            pass

    @patch("flavor.locking.FileLock")
    def test_lock_exception_with_timeout_keyword(self, mock_filelock_class: Mock, tmp_path: Path) -> None:
        """Test that exceptions containing 'timeout' are converted to LockError."""
        manager = LockManager(lock_dir=tmp_path)
        mock_lock = Mock()
        # Simulate an exception with "timeout" in message
        mock_lock.acquire.side_effect = Exception("Connection timeout occurred")
        mock_filelock_class.return_value = mock_lock

        with pytest.raises(LockError, match="Timeout acquiring lock: test_lock"), manager.lock("test_lock"):
            pass

    @patch("flavor.locking.FileLock")
    def test_lock_exception_without_timeout_propagates(
        self, mock_filelock_class: Mock, tmp_path: Path
    ) -> None:
        """Test that non-timeout exceptions are propagated."""
        manager = LockManager(lock_dir=tmp_path)
        mock_lock = Mock()
        # Simulate a different exception
        mock_lock.acquire.side_effect = RuntimeError("Something else failed")
        mock_filelock_class.return_value = mock_lock

        with pytest.raises(RuntimeError, match="Something else failed"), manager.lock("test_lock"):
            pass

    @patch("flavor.locking.FileLock")
    def test_lock_released_on_exception(self, mock_filelock_class: Mock, tmp_path: Path) -> None:
        """Test that lock is released even if exception occurs in context."""
        manager = LockManager(lock_dir=tmp_path)
        mock_lock = Mock()
        mock_lock.acquire.return_value = True
        mock_filelock_class.return_value = mock_lock

        lock_file = tmp_path / "test_lock.lock"

        try:
            with manager.lock("test_lock"):
                assert lock_file in manager.held_locks
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Lock should be released and removed from held_locks
        assert lock_file not in manager.held_locks
        mock_lock.release.assert_called_once()

    @patch("flavor.locking.FileLock")
    def test_lock_updates_held_locks(self, mock_filelock_class: Mock, tmp_path: Path) -> None:
        """Test that held_locks set is properly maintained."""
        manager = LockManager(lock_dir=tmp_path)
        mock_lock = Mock()
        mock_lock.acquire.return_value = True
        mock_filelock_class.return_value = mock_lock

        lock_file_1 = tmp_path / "lock1.lock"
        lock_file_2 = tmp_path / "lock2.lock"

        assert len(manager.held_locks) == 0

        with manager.lock("lock1"):
            assert lock_file_1 in manager.held_locks
            assert len(manager.held_locks) == 1

            with manager.lock("lock2"):
                assert lock_file_1 in manager.held_locks
                assert lock_file_2 in manager.held_locks
                assert len(manager.held_locks) == 2

            # lock2 released
            assert lock_file_2 not in manager.held_locks
            assert len(manager.held_locks) == 1

        # All locks released
        assert len(manager.held_locks) == 0

    def test_cleanup_all(self, tmp_path: Path) -> None:
        """Test cleanup_all method clears held_locks."""
        manager = LockManager(lock_dir=tmp_path)

        # Manually add some locks to held_locks (simulating held state)
        manager.held_locks.add(tmp_path / "lock1.lock")
        manager.held_locks.add(tmp_path / "lock2.lock")
        assert len(manager.held_locks) == 2

        manager.cleanup_all()

        assert len(manager.held_locks) == 0

    @patch("flavor.locking.FileLock")
    def test_multiple_lock_managers_independent(self, mock_filelock_class: Mock, tmp_path: Path) -> None:
        """Test that multiple LockManager instances are independent."""
        mock_lock = Mock()
        mock_lock.acquire.return_value = True
        mock_filelock_class.return_value = mock_lock

        manager1 = LockManager(lock_dir=tmp_path / "locks1")
        manager2 = LockManager(lock_dir=tmp_path / "locks2")

        lock_file_1 = tmp_path / "locks1" / "test.lock"
        lock_file_2 = tmp_path / "locks2" / "test.lock"

        with manager1.lock("test"):
            assert lock_file_1 in manager1.held_locks
            assert lock_file_1 not in manager2.held_locks

            with manager2.lock("test"):
                assert lock_file_2 in manager2.held_locks
                assert lock_file_2 not in manager1.held_locks

    def test_lock_with_special_characters_in_name(self, tmp_path: Path) -> None:
        """Test lock names with special characters are handled correctly."""
        manager = LockManager(lock_dir=tmp_path)
        lock_name = "package-name_v1.0.0"
        expected_file = tmp_path / f"{lock_name}.lock"

        with manager.lock(lock_name) as lock_file:
            assert lock_file == expected_file


class TestDefaultLockManager:
    """Test the default global lock manager instance."""

    def test_default_lock_manager_exists(self) -> None:
        """Test that default_lock_manager is available."""
        from flavor.locking import default_lock_manager

        assert default_lock_manager is not None
        assert isinstance(default_lock_manager, LockManager)

    def test_default_lock_manager_has_default_path(self) -> None:
        """Test that default manager uses default lock directory."""
        from flavor.locking import default_lock_manager

        expected_dir = Path.home() / ".cache" / "flavor" / "locks"
        assert default_lock_manager.lock_dir == expected_dir


# 🌶️📦🔚
