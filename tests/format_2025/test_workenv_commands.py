#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for psp/format_2025/workenv.py - Setup commands and substitutions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from flavor.psp.format_2025.workenv import WorkEnvManager


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
        env = {"PATH": "/bin"}  # Test environment

        cmd = {"command": "echo test"}

        manager._run_execute_command(cmd, workenv_dir, metadata, env)

        mock_run.assert_called_once_with(
            ["echo", "test"],
            cwd=workenv_dir,
            capture_output=True,
            check=True,
            env=env,
        )

    @patch("flavor.psp.format_2025.workenv.run")
    def test_execute_command_failure(self, mock_run: Mock, tmp_path: Path) -> None:
        """Test command execution failure."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        metadata = {"package": {"name": "testpkg", "version": "1.0.0"}}
        env = {"PATH": "/bin"}  # Test environment

        cmd = {"command": "false"}

        mock_run.side_effect = Exception("Command failed")

        with pytest.raises(RuntimeError, match="Setup command failed"):
            manager._run_execute_command(cmd, workenv_dir, metadata, env)

    @patch("flavor.psp.format_2025.workenv.run")
    def test_execute_command_with_substitutions(self, mock_run: Mock, tmp_path: Path) -> None:
        """Test command with placeholder substitutions."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        metadata = {"package": {"name": "testpkg", "version": "1.0.0"}}
        env = {"PATH": "/bin"}  # Test environment

        cmd = {"command": "echo {workenv} {version}"}

        manager._run_execute_command(cmd, workenv_dir, metadata, env)

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
        env = {"PATH": "/bin"}  # Test environment

        cmd = {"pattern": "*.sh", "command": "chmod +x {file}"}

        manager._run_enumerate_execute_command(cmd, workenv_dir, env)

        # Should execute for both files
        assert mock_run.call_count == 2

    @patch("flavor.psp.format_2025.workenv.run")
    def test_enumerate_execute_no_matches(self, mock_run: Mock, tmp_path: Path) -> None:
        """Test enumerate with no matching files."""
        mock_reader = Mock()
        manager = WorkEnvManager(mock_reader)

        workenv_dir = tmp_path / "workenv"
        workenv_dir.mkdir()
        env = {"PATH": "/bin"}  # Test environment

        cmd = {"pattern": "*.nonexistent", "command": "echo {file}"}

        manager._run_enumerate_execute_command(cmd, workenv_dir, env)

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
        env = {"PATH": "/bin"}  # Test environment

        cmd = {"pattern": "*.sh", "command": "false"}

        mock_run.side_effect = Exception("Command failed")

        # Should continue despite error (doesn't raise)
        manager._run_enumerate_execute_command(cmd, workenv_dir, env)

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

# 🌶️📦🔚
