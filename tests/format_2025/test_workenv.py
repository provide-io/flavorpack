# tests/format_2025/test_workenv.py
#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for psp/format_2025/workenv.py - Work Environment Management."""

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


class TestRunSetupCommands:
    """Test _run_setup_commands method."""

    def test_run_setup_commands_write_file(self, tmp_path: Path) -> None:
        """Test running write_file setup command."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        workenv_dir.mkdir()

        metadata = {"package": {"name": "testpkg", "version": "1.0.0"}}
        setup_commands = [
            {"type": "write_file", "path": "{workenv}/.initialized", "content": "version: {version}"}
        ]

        with patch.object(manager, "_run_write_file_command") as mock_write:
            manager._run_setup_commands(setup_commands, workenv_dir, metadata)

            mock_write.assert_called_once()

    @patch("flavor.psp.format_2025.workenv.run")
    def test_run_setup_commands_execute(self, mock_run: Mock, tmp_path: Path) -> None:
        """Test running execute setup command."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        workenv_dir.mkdir()

        metadata = {"package": {"name": "testpkg", "version": "1.0.0"}}
        setup_commands = [{"type": "execute", "command": "echo test"}]

        with patch.object(manager, "_run_execute_command") as mock_execute:
            manager._run_setup_commands(setup_commands, workenv_dir, metadata)

            mock_execute.assert_called_once()

    def test_run_setup_commands_enumerate_execute(self, tmp_path: Path) -> None:
        """Test running enumerate_and_execute setup command."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        workenv_dir.mkdir()

        metadata = {"package": {"name": "testpkg", "version": "1.0.0"}}
        setup_commands = [{"type": "enumerate_and_execute", "pattern": "*.sh", "command": "chmod +x {file}"}]

        with patch.object(manager, "_run_enumerate_execute_command") as mock_enum:
            manager._run_setup_commands(setup_commands, workenv_dir, metadata)

            mock_enum.assert_called_once()

    def test_run_setup_commands_unknown_type(self, tmp_path: Path) -> None:
        """Test handling of unknown setup command type."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        workenv_dir.mkdir()

        metadata = {"package": {"name": "testpkg", "version": "1.0.0"}}
        setup_commands = [{"type": "unknown_type"}]

        # Should log warning but not crash
        manager._run_setup_commands(setup_commands, workenv_dir, metadata)

    def test_run_setup_commands_string_not_supported(self, tmp_path: Path) -> None:
        """Test handling of string setup commands (not supported)."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        workenv_dir.mkdir()

        metadata = {"package": {"name": "testpkg", "version": "1.0.0"}}
        setup_commands = ["echo test"]  # String command

        # Should log warning but not crash
        manager._run_setup_commands(setup_commands, workenv_dir, metadata)


class TestRunWriteFileCommand:
    """Test _run_write_file_command method."""

    @patch("flavor.psp.format_2025.workenv.atomic_write_text")
    @patch("flavor.psp.format_2025.workenv.ensure_parent_dir")
    def test_write_file_command_basic(
        self, mock_ensure_parent: Mock, mock_atomic_write: Mock, tmp_path: Path
    ) -> None:
        """Test basic file writing."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        metadata = {"package": {"name": "testpkg", "version": "1.0.0"}}

        cmd = {"path": "{workenv}/.initialized", "content": "version: {version}"}

        manager._run_write_file_command(cmd, workenv_dir, metadata)

        expected_path = workenv_dir / ".initialized"
        mock_ensure_parent.assert_called_once_with(expected_path)
        mock_atomic_write.assert_called_once_with(expected_path, "version: 1.0.0")

    @patch("flavor.psp.format_2025.workenv.atomic_write_text")
    @patch("flavor.psp.format_2025.workenv.ensure_parent_dir")
    def test_write_file_command_to_directory(
        self, mock_ensure_parent: Mock, mock_atomic_write: Mock, tmp_path: Path
    ) -> None:
        """Test writing file when path is a directory."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        target_dir = tmp_path / "target"
        target_dir.mkdir(parents=True)

        metadata = {"package": {"name": "testpkg", "version": "1.0.0"}}
        cmd = {"path": str(target_dir), "content": "test content"}

        manager._run_write_file_command(cmd, workenv_dir, metadata)

        # Should write to .extracted file inside directory
        expected_path = target_dir / ".extracted"
        mock_atomic_write.assert_called_once_with(expected_path, "test content")


class TestRunExecuteCommand:
    """Test _run_execute_command method."""

    @patch("flavor.psp.format_2025.workenv.run")
    def test_execute_command_success(self, mock_run: Mock, tmp_path: Path) -> None:
        """Test successful command execution."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        metadata = {"package": {"name": "testpkg", "version": "1.0.0"}}

        cmd = {"command": "echo test"}

        manager._run_execute_command(cmd, workenv_dir, metadata)

        mock_run.assert_called_once_with(
            ["echo", "test"],
            cwd=workenv_dir,
            capture_output=True,
            check=True,
        )

    @patch("flavor.psp.format_2025.workenv.run")
    def test_execute_command_failure(self, mock_run: Mock, tmp_path: Path) -> None:
        """Test command execution failure."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        metadata = {"package": {"name": "testpkg", "version": "1.0.0"}}

        cmd = {"command": "false"}

        mock_run.side_effect = Exception("Command failed")

        with pytest.raises(RuntimeError, match="Setup command failed"):
            manager._run_execute_command(cmd, workenv_dir, metadata)

    @patch("flavor.psp.format_2025.workenv.run")
    def test_execute_command_with_substitutions(self, mock_run: Mock, tmp_path: Path) -> None:
        """Test command with placeholder substitutions."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        metadata = {"package": {"name": "testpkg", "version": "1.0.0"}}

        cmd = {"command": "echo {workenv} {version}"}

        manager._run_execute_command(cmd, workenv_dir, metadata)

        mock_run.assert_called_once()
        assert mock_run.call_args[0][0][1] == str(workenv_dir)
        assert mock_run.call_args[0][0][2] == "1.0.0"


class TestRunEnumerateExecuteCommand:
    """Test _run_enumerate_execute_command method."""

    @patch("flavor.psp.format_2025.workenv.run")
    def test_enumerate_execute_basic(self, mock_run: Mock, tmp_path: Path) -> None:
        """Test basic enumerate and execute."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        workenv_dir.mkdir()

        # Create test files
        file1 = workenv_dir / "test1.sh"
        file2 = workenv_dir / "test2.sh"
        file1.write_text("#!/bin/bash")
        file2.write_text("#!/bin/bash")

        cmd = {"pattern": "*.sh", "command": "chmod +x {file}"}

        manager._run_enumerate_execute_command(cmd, workenv_dir)

        # Should execute for both files
        assert mock_run.call_count == 2

    @patch("flavor.psp.format_2025.workenv.run")
    def test_enumerate_execute_no_matches(self, mock_run: Mock, tmp_path: Path) -> None:
        """Test enumerate with no matching files."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        workenv_dir.mkdir()

        cmd = {"pattern": "*.nonexistent", "command": "echo {file}"}

        manager._run_enumerate_execute_command(cmd, workenv_dir)

        # Should not execute any commands
        mock_run.assert_not_called()

    @patch("flavor.psp.format_2025.workenv.run")
    def test_enumerate_execute_command_failure(self, mock_run: Mock, tmp_path: Path) -> None:
        """Test enumerate execute with command failure."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        workenv_dir.mkdir()

        file1 = workenv_dir / "test.sh"
        file1.write_text("#!/bin/bash")

        cmd = {"pattern": "*.sh", "command": "false"}

        mock_run.side_effect = Exception("Command failed")

        # Should continue despite error (doesn't raise)
        manager._run_enumerate_execute_command(cmd, workenv_dir)

        mock_run.assert_called_once()


class TestSubstitutePlaceholders:
    """Test _substitute_placeholders method."""

    def test_substitute_placeholders_all(self, tmp_path: Path) -> None:
        """Test substitution of all placeholder types."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        metadata = {"package": {"name": "testpkg", "version": "1.0.0"}}

        text = "Path: {workenv}, Name: {package_name}, Version: {version}"

        result = manager._substitute_placeholders(text, workenv_dir, metadata)

        expected = f"Path: {workenv_dir}, Name: testpkg, Version: 1.0.0"
        assert result == expected

    def test_substitute_placeholders_partial(self, tmp_path: Path) -> None:
        """Test substitution with only some placeholders."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        metadata = {"package": {"name": "testpkg", "version": "1.0.0"}}

        text = "Version: {version}"

        result = manager._substitute_placeholders(text, workenv_dir, metadata)

        assert result == "Version: 1.0.0"


class TestSubstituteSlotReferences:
    """Test substitute_slot_references method."""

    def test_substitute_slot_references_basic(self, tmp_path: Path) -> None:
        """Test basic slot reference substitution."""
        mock_reader = Mock()
        metadata = {
            "package": {"name": "testpkg", "version": "1.0.0"},
            "slots": [{"id": "runtime"}, {"id": "app"}],
        }
        mock_reader.read_metadata.return_value = metadata

        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        command = "python {slot:0}/bin/python {slot:1}/app.py"

        result = manager.substitute_slot_references(command, workenv_dir)

        expected_slot0 = workenv_dir / "runtime"
        expected_slot1 = workenv_dir / "app"
        expected = f"python {expected_slot0}/bin/python {expected_slot1}/app.py"

        assert result == expected

    def test_substitute_slot_references_default_names(self, tmp_path: Path) -> None:
        """Test slot reference substitution with default slot names."""
        mock_reader = Mock()
        metadata = {
            "package": {"name": "testpkg", "version": "1.0.0"},
            "slots": [{}, {}],  # No id field
        }
        mock_reader.read_metadata.return_value = metadata

        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        command = "Use {slot:0} and {slot:1}"

        result = manager.substitute_slot_references(command, workenv_dir)

        expected_slot0 = workenv_dir / "slot_0"
        expected_slot1 = workenv_dir / "slot_1"
        expected = f"Use {expected_slot0} and {expected_slot1}"

        assert result == expected

    def test_substitute_slot_references_no_slots(self, tmp_path: Path) -> None:
        """Test slot reference substitution with no slots."""
        mock_reader = Mock()
        metadata = {"package": {"name": "testpkg", "version": "1.0.0"}}
        mock_reader.read_metadata.return_value = metadata

        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        command = "echo test"

        result = manager.substitute_slot_references(command, workenv_dir)

        assert result == "echo test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
