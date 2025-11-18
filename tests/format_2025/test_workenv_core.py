#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for psp/format_2025/workenv.py - Core functionality."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from flavor.psp.format_2025.workenv import WorkEnvManager


class TestWorkEnvManagerInit:
    """Test WorkEnvManager initialization."""

    def test_init(self) -> None:
        """Test basic initialization."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        assert manager.reader is mock_reader


class TestSetupWorkenv:
    """Test setup_workenv method."""

    @patch("flavor.psp.format_2025.workenv.ensure_dir")
    def test_setup_workenv_with_valid_cache(self, mock_ensure_dir: Mock, tmp_path: Path) -> None:
        """Test setup with valid cache (no extraction)."""
        mock_reader = Mock()
        metadata = {
            "package": {"name": "testpkg", "version": "1.0.0"},
            "cache_validation": {
                "check_file": "{workenv}/.version",
                "expected_content": "{version}",
            },
        }
        mock_reader.read_metadata.return_value = metadata

        # Create cache validation file
        cache_dir = Path.home() / ".cache" / "flavor" / "workenv" / "testpkg_1.0.0"
        cache_dir.mkdir(parents=True, exist_ok=True)
        version_file = cache_dir / ".version"
        version_file.write_text("1.0.0")

        manager = WorkEnvManager(mock_reader)
        result = manager.setup_workenv(tmp_path / "bundle.psp")

        # Should use cached environment
        assert result == cache_dir
        mock_ensure_dir.assert_called_once()

    @patch("flavor.psp.format_2025.workenv.ensure_dir")
    def test_setup_workenv_with_invalid_cache(self, mock_ensure_dir: Mock, tmp_path: Path) -> None:
        """Test setup with invalid cache (forces extraction)."""
        mock_reader = Mock()
        mock_index = Mock()
        mock_index.slot_count = 2
        mock_reader._index = mock_index

        metadata = {
            "package": {"name": "testpkg2", "version": "2.0.0"},  # Different name/version
            "cache_validation": {
                "check_file": "{workenv}/.version",
                "expected_content": "{version}",
            },
            "slots": [{"id": "runtime"}, {"id": "app"}],
        }
        mock_reader.read_metadata.return_value = metadata

        # Mock extraction
        slot1_path = tmp_path / "runtime"
        slot2_path = tmp_path / "app"
        mock_reader.extract_slot.side_effect = [slot1_path, slot2_path]

        manager = WorkEnvManager(mock_reader)

        # Cache file doesn't exist, so extraction happens
        manager.setup_workenv(tmp_path / "bundle.psp")

        # Should extract both slots
        assert mock_reader.extract_slot.call_count == 2

    @patch("flavor.psp.format_2025.workenv.ensure_dir")
    def test_setup_workenv_with_setup_commands(self, mock_ensure_dir: Mock, tmp_path: Path) -> None:
        """Test setup with setup commands."""
        mock_reader = Mock()
        mock_index = Mock()
        mock_index.slot_count = 1
        mock_reader._index = mock_index

        metadata = {
            "package": {"name": "testpkg", "version": "1.0.0"},
            "slots": [{"id": "runtime"}],
            "setup_commands": [{"type": "write_file", "path": "{workenv}/.initialized", "content": "done"}],
        }
        mock_reader.read_metadata.return_value = metadata

        slot1_path = tmp_path / "runtime"
        mock_reader.extract_slot.return_value = slot1_path

        manager = WorkEnvManager(mock_reader)

        with patch.object(manager, "_run_setup_commands") as mock_run_setup:
            manager.setup_workenv(tmp_path / "bundle.psp")

            # Should run setup commands
            mock_run_setup.assert_called_once()

    @patch("flavor.psp.format_2025.workenv.ensure_dir")
    def test_setup_workenv_with_lifecycle_cleanup(self, mock_ensure_dir: Mock, tmp_path: Path) -> None:
        """Test setup with lifecycle-based cleanup."""
        mock_reader = Mock()
        mock_index = Mock()
        mock_index.slot_count = 2
        mock_reader._index = mock_index

        metadata = {
            "package": {"name": "testpkg", "version": "1.0.0"},
            "slots": [{"id": "init", "lifecycle": "init"}, {"id": "runtime", "lifecycle": "runtime"}],
        }
        mock_reader.read_metadata.return_value = metadata

        slot1_path = tmp_path / "init"
        slot2_path = tmp_path / "runtime"
        mock_reader.extract_slot.side_effect = [slot1_path, slot2_path]

        manager = WorkEnvManager(mock_reader)

        with patch.object(manager, "_cleanup_lifecycle_slots") as mock_cleanup:
            manager.setup_workenv(tmp_path / "bundle.psp")

            # Should cleanup lifecycle slots
            mock_cleanup.assert_called_once()


class TestCheckCacheValidity:
    """Test _check_cache_validity method."""

    def test_check_cache_validity_valid(self, tmp_path: Path) -> None:
        """Test cache validity check with valid cache."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        workenv_dir.mkdir()
        version_file = workenv_dir / ".version"
        version_file.write_text("1.0.0")

        metadata = {
            "cache_validation": {
                "check_file": "{workenv}/.version",
                "expected_content": "{version}",
            }
        }

        result = manager._check_cache_validity(metadata, workenv_dir, "1.0.0")

        assert result is True

    def test_check_cache_validity_mismatch(self, tmp_path: Path) -> None:
        """Test cache validity check with content mismatch."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        workenv_dir.mkdir()
        version_file = workenv_dir / ".version"
        version_file.write_text("2.0.0")  # Wrong version

        metadata = {
            "cache_validation": {
                "check_file": "{workenv}/.version",
                "expected_content": "{version}",
            }
        }

        result = manager._check_cache_validity(metadata, workenv_dir, "1.0.0")

        assert result is False

    def test_check_cache_validity_file_not_found(self, tmp_path: Path) -> None:
        """Test cache validity check when file doesn't exist."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        workenv_dir.mkdir()

        metadata = {
            "cache_validation": {
                "check_file": "{workenv}/.version",
                "expected_content": "{version}",
            }
        }

        result = manager._check_cache_validity(metadata, workenv_dir, "1.0.0")

        assert result is False

    def test_check_cache_validity_no_cache_config(self, tmp_path: Path) -> None:
        """Test cache validity check with no cache_validation config."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        metadata: dict[str, Any] = {}  # No cache_validation

        result = manager._check_cache_validity(metadata, workenv_dir, "1.0.0")

        assert result is False


class TestCleanupLifecycleSlots:
    """Test _cleanup_lifecycle_slots method."""

    @patch("flavor.psp.format_2025.workenv.safe_rmtree")
    def test_cleanup_init_lifecycle_directory(self, mock_rmtree: Mock, tmp_path: Path) -> None:
        """Test cleanup of 'init' lifecycle slot (directory)."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        slot_dir = tmp_path / "init_slot"
        slot_dir.mkdir(parents=True)

        metadata = {"slots": [{"id": "init", "lifecycle": "init"}]}
        extracted_slots = {0: slot_dir}

        manager._cleanup_lifecycle_slots(workenv_dir, metadata, extracted_slots)

        # Should remove directory
        mock_rmtree.assert_called_once_with(slot_dir)

    def test_cleanup_init_lifecycle_file(self, tmp_path: Path) -> None:
        """Test cleanup of 'init' lifecycle slot (file)."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        slot_file = tmp_path / "init_slot.txt"
        slot_file.write_text("init data")

        metadata = {"slots": [{"id": "init", "lifecycle": "init"}]}
        extracted_slots = {0: slot_file}

        manager._cleanup_lifecycle_slots(workenv_dir, metadata, extracted_slots)

        # Should remove file
        assert not slot_file.exists()

    def test_cleanup_temp_lifecycle(self, tmp_path: Path) -> None:
        """Test handling of 'temp' lifecycle slot (not removed immediately)."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        slot_dir = tmp_path / "temp_slot"
        slot_dir.mkdir(parents=True)

        metadata = {"slots": [{"id": "temp", "lifecycle": "temp"}]}
        extracted_slots = {0: slot_dir}

        manager._cleanup_lifecycle_slots(workenv_dir, metadata, extracted_slots)

        # Should NOT remove temp slot immediately
        assert slot_dir.exists()

    def test_cleanup_runtime_lifecycle(self, tmp_path: Path) -> None:
        """Test handling of 'runtime' lifecycle slot (not removed)."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        slot_dir = tmp_path / "runtime_slot"
        slot_dir.mkdir(parents=True)

        metadata = {"slots": [{"id": "runtime", "lifecycle": "runtime"}]}
        extracted_slots = {0: slot_dir}

        manager._cleanup_lifecycle_slots(workenv_dir, metadata, extracted_slots)

        # Should NOT remove runtime slot
        assert slot_dir.exists()

    def test_cleanup_missing_lifecycle_field(self, tmp_path: Path) -> None:
        """Test handling of slot without lifecycle field (defaults to runtime)."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        slot_dir = tmp_path / "slot"
        slot_dir.mkdir(parents=True)

        metadata = {"slots": [{"id": "slot"}]}  # No lifecycle field
        extracted_slots = {0: slot_dir}

        manager._cleanup_lifecycle_slots(workenv_dir, metadata, extracted_slots)

        # Should NOT remove (defaults to runtime)
        assert slot_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# 🌶️📦🔚
