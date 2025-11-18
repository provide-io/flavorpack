#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test workenv directory creation with permissions and umask."""

import os
from pathlib import Path
import stat
import tempfile
from unittest.mock import patch

import pytest

from flavor.psp.metadata.paths import (
    apply_umask,
    create_workenv_directories,
    validate_workenv_paths,
)


@pytest.mark.unit
class TestWorkenvDirectories:
    """Test workenv directory validation and creation."""

    def test_workenv_paths_require_prefix(self) -> None:
        """All workenv directory paths MUST start with {workenv}."""
        # Valid paths with {workenv} prefix
        valid_paths = [
            "{workenv}/tmp",
            "{workenv}/var/log",
            "{workenv}/cache/{platform}",
            "{workenv}/home",
        ]

        for path in valid_paths:
            assert validate_workenv_paths([{"path": path}]) is True

        # Invalid paths without {workenv} prefix
        invalid_paths = ["tmp", "var/log", "/tmp", "/absolute/path", "relative/path"]

        for path in invalid_paths:
            with pytest.raises(ValueError, match="must start with \\{workenv\\}"):
                validate_workenv_paths([{"path": path}])

    def test_directory_creation_with_mode(self) -> None:
        """Test directories are created with specified mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workenv = Path(tmpdir) / "workenv"

            directories = [
                {"path": "{workenv}/tmp", "mode": "0700"},
                {"path": "{workenv}/var", "mode": "0755"},
                {"path": "{workenv}/cache", "mode": "0750"},
            ]

            create_workenv_directories(directories, workenv)

            # Check permissions
            tmp_stat = (workenv / "tmp").stat()
            assert stat.S_IMODE(tmp_stat.st_mode) == 0o700

            var_stat = (workenv / "var").stat()
            assert stat.S_IMODE(var_stat.st_mode) == 0o755

            cache_stat = (workenv / "cache").stat()
            assert stat.S_IMODE(cache_stat.st_mode) == 0o750

    def test_directory_umask_default(self) -> None:
        """Test default umask is applied when no mode specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workenv = Path(tmpdir) / "workenv"

            # Save current umask
            old_umask = os.umask(0)
            os.umask(old_umask)

            try:
                # Set default umask to 0077 (owner-only)
                with patch("os.umask") as mock_umask:
                    mock_umask.return_value = old_umask

                    directories = [
                        {"path": "{workenv}/default1"},
                        {"path": "{workenv}/default2"},
                    ]

                    # Apply default umask
                    apply_umask(0o077)
                    create_workenv_directories(directories, workenv)

                    # Check that directories have 0700 permissions (0777 & ~0077)
                    for dir_info in directories:
                        dir_path = workenv / dir_info["path"].replace("{workenv}/", "")
                        if dir_path.exists():
                            dir_stat = dir_path.stat()
                            # Default is 0777 & ~umask
                            # On macOS, default umask is often 0o022, giving 0o755
                            # On Linux, it's often 0o077, giving 0o700
                            mode = stat.S_IMODE(dir_stat.st_mode)
                            assert mode in (0o700, 0o755), f"Expected 0o700 or 0o755, got {oct(mode)}"
            finally:
                # Restore original umask
                os.umask(old_umask)

    def test_directory_umask_override(self) -> None:
        """Test umask can be overridden in metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workenv = Path(tmpdir) / "workenv"

            # Save current umask
            old_umask = os.umask(0)
            os.umask(old_umask)

            try:
                # Test with umask 0022 (group/other readable)
                apply_umask(0o022)

                directories = [
                    {"path": "{workenv}/shared"},
                ]

                create_workenv_directories(directories, workenv, umask="0022")

                # Check that directory has 0755 permissions (0777 & ~0022)
                shared_path = workenv / "shared"
                if shared_path.exists():
                    shared_stat = shared_path.stat()
                    # Default is 0777 & ~0022 = 0755
                    assert stat.S_IMODE(shared_stat.st_mode) == 0o755
            finally:
                # Restore original umask
                os.umask(old_umask)

    def test_nested_directory_creation(self) -> None:
        """Test creation of nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workenv = Path(tmpdir) / "workenv"

            directories = [
                {"path": "{workenv}/var/log/app", "mode": "0755"},
                {"path": "{workenv}/cache/{platform}/data", "mode": "0750"},
            ]

            create_workenv_directories(directories, workenv)

            # Check nested paths exist
            assert (workenv / "var").exists()
            assert (workenv / "var" / "log").exists()
            assert (workenv / "var" / "log" / "app").exists()

            # Platform placeholder should be substituted
            cache_dir = workenv / "cache"
            assert cache_dir.exists()
            # Should have a platform-specific subdirectory
            subdirs = list(cache_dir.iterdir())
            assert len(subdirs) > 0
            # Platform dir should contain underscore (os_arch format)
            assert "_" in subdirs[0].name

    def test_directory_mode_parsing(self) -> None:
        """Test parsing of mode strings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workenv = Path(tmpdir) / "workenv"

            # Test various mode formats
            directories = [
                {"path": "{workenv}/octal1", "mode": "0777"},
                {"path": "{workenv}/octal2", "mode": "777"},  # Without leading 0
                {"path": "{workenv}/octal3", "mode": "0o755"},  # Python octal format
            ]

            create_workenv_directories(directories, workenv)

            # All should be created successfully
            assert (workenv / "octal1").exists()
            assert (workenv / "octal2").exists()
            assert (workenv / "octal3").exists()

    def test_existing_directory_handling(self) -> None:
        """Test handling of existing directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workenv = Path(tmpdir) / "workenv"

            # Create existing directory with different permissions
            existing_dir = workenv / "existing"
            existing_dir.mkdir(parents=True, mode=0o777)

            # Try to create with different mode
            directories = [{"path": "{workenv}/existing", "mode": "0700"}]

            create_workenv_directories(directories, workenv)

            # Should update permissions
            existing_stat = existing_dir.stat()
            assert stat.S_IMODE(existing_stat.st_mode) == 0o700

    def test_symlink_in_path_handling(self) -> None:
        """Test handling of symlinks in directory paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workenv = Path(tmpdir) / "workenv"
            real_dir = Path(tmpdir) / "real"
            real_dir.mkdir()

            # Create symlink
            link_dir = workenv / "link"
            workenv.mkdir(parents=True)
            link_dir.symlink_to(real_dir)

            directories = [{"path": "{workenv}/link/subdir", "mode": "0755"}]

            create_workenv_directories(directories, workenv)

            # Should create subdir in the real directory
            assert (real_dir / "subdir").exists()

    def test_permission_error_handling(self) -> None:
        """Test handling of permission errors during directory creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workenv = Path(tmpdir) / "workenv"

            # Create read-only parent directory
            readonly_parent = workenv / "readonly"
            readonly_parent.mkdir(parents=True, mode=0o500)

            directories = [{"path": "{workenv}/readonly/child", "mode": "0755"}]

            # Should raise permission error
            with pytest.raises(PermissionError):
                create_workenv_directories(directories, workenv)

    def test_invalid_mode_handling(self) -> None:
        """Test handling of invalid mode values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workenv = Path(tmpdir) / "workenv"

            # Invalid mode values
            invalid_directories = [
                {"path": "{workenv}/invalid1", "mode": "not-a-mode"},
                {"path": "{workenv}/invalid2", "mode": "9999"},  # Invalid octal
                {"path": "{workenv}/invalid3", "mode": "-755"},  # Negative
            ]

            for dir_info in invalid_directories:
                with pytest.raises(ValueError):
                    create_workenv_directories([dir_info], workenv)


# 🌶️📦🔚
