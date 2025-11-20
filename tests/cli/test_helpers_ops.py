#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Comprehensive tests for helper CLI operations (clean/build/etc.)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner

from flavor.cli import main as cli_main
from flavor.helpers.manager import HelperInfo


class TestHelperClean:
    """Test suite for 'flavor helpers clean' command."""

    @patch("flavor.helpers.manager.HelperManager")
    @patch("click.confirm")
    def test_clean_all_with_confirmation(
        self, mock_confirm: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test clean command with user confirmation."""
        mock_confirm.return_value = True
        mock_manager = Mock()
        removed_paths = [tmp_path / "launcher.bin", tmp_path / "builder.bin"]
        mock_manager.clean_helpers.return_value = removed_paths
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "clean"])

        assert result.exit_code == 0
        assert "Removed 2 helper(s)" in result.output
        assert "launcher.bin" in result.output
        assert "builder.bin" in result.output
        mock_confirm.assert_called_once_with("Remove all helper binaries?")
        mock_manager.clean_helpers.assert_called_once_with(language=None)

    @patch("flavor.helpers.manager.HelperManager")
    @patch("click.confirm")
    def test_clean_user_aborts(self, mock_confirm: Mock, mock_manager_class: Mock) -> None:
        """Test clean command when user aborts confirmation."""
        mock_confirm.return_value = False
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "clean"])

        assert result.exit_code == 0
        assert "Aborted." in result.output
        mock_manager.clean_helpers.assert_not_called()

    @patch("flavor.helpers.manager.HelperManager")
    def test_clean_with_yes_flag(self, mock_manager_class: Mock, tmp_path: Path) -> None:
        """Test clean command with --yes flag skips confirmation."""
        mock_manager = Mock()
        removed_path = tmp_path / "launcher.bin"
        mock_manager.clean_helpers.return_value = [removed_path]
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "clean", "--yes"])

        assert result.exit_code == 0
        assert "Removed 1 helper(s)" in result.output
        mock_manager.clean_helpers.assert_called_once_with(language=None)

    @patch("flavor.helpers.manager.HelperManager")
    def test_clean_go_only(self, mock_manager_class: Mock, tmp_path: Path) -> None:
        """Test clean command with Go language only."""
        mock_manager = Mock()
        removed_path = tmp_path / "go-launcher.bin"
        mock_manager.clean_helpers.return_value = [removed_path]
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "clean", "--lang", "go", "--yes"])

        assert result.exit_code == 0
        mock_manager.clean_helpers.assert_called_once_with(language="go")

    @patch("flavor.helpers.manager.HelperManager")
    def test_clean_rust_only(self, mock_manager_class: Mock, tmp_path: Path) -> None:
        """Test clean command with Rust language only."""
        mock_manager = Mock()
        removed_path = tmp_path / "rust-builder.bin"
        mock_manager.clean_helpers.return_value = [removed_path]
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "clean", "--lang", "rust", "--yes"])

        assert result.exit_code == 0
        mock_manager.clean_helpers.assert_called_once_with(language="rust")

    @patch("flavor.helpers.manager.HelperManager")
    def test_clean_nothing_to_remove(self, mock_manager_class: Mock) -> None:
        """Test clean command when no helpers exist."""
        mock_manager = Mock()
        mock_manager.clean_helpers.return_value = []
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "clean", "--yes"])

        assert result.exit_code == 0
        assert "No helpers to remove" in result.output


class TestHelperInfo:
    """Test suite for 'flavor helpers info' command."""

    @patch("flavor.helpers.manager.HelperManager")
    def test_info_helper_found_executable(self, mock_manager_class: Mock, tmp_path: Path) -> None:
        """Test info command for found helper that is executable."""
        mock_manager = Mock()
        launcher_path = tmp_path / "launcher.bin"
        launcher_path.write_text("binary")
        launcher_path.chmod(0o755)  # Make executable
        source_path = tmp_path / "src"
        source_path.mkdir()

        info = HelperInfo(
            name="launcher.bin",
            path=launcher_path,
            type="launcher",
            language="go",
            size=2_000_000,
            version="1.0.0",
            checksum="abc123",
            built_from=source_path,
        )
        mock_manager.get_helper_info.return_value = info
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "info", "launcher.bin"])

        assert result.exit_code == 0
        assert "Helper Information: launcher.bin" in result.output
        assert "Type: launcher" in result.output
        assert "Language: go" in result.output
        assert f"Path: {launcher_path}" in result.output
        assert "Size: 1.9 MB" in result.output
        assert "Version: 1.0.0" in result.output
        assert "Checksum: abc123" in result.output
        assert f"Source: {source_path}" in result.output
        assert "Source directory exists" in result.output

    @patch("flavor.helpers.manager.HelperManager")
    def test_info_helper_not_found(self, mock_manager_class: Mock) -> None:
        """Test info command for helper that doesn't exist."""
        mock_manager = Mock()
        mock_manager.get_helper_info.return_value = None
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "info", "nonexistent"])

        assert result.exit_code == 0
        assert "Helper 'nonexistent' not found" in result.output

    @patch("flavor.helpers.manager.HelperManager")
    def test_info_helper_not_executable(self, mock_manager_class: Mock, tmp_path: Path) -> None:
        """Test info command for helper that is not executable."""
        mock_manager = Mock()
        launcher_path = tmp_path / "launcher.bin"
        launcher_path.write_text("binary")
        launcher_path.chmod(0o644)  # Not executable

        info = HelperInfo(
            name="launcher.bin",
            path=launcher_path,
            type="launcher",
            language="go",
            size=1_000_000,
        )
        mock_manager.get_helper_info.return_value = info
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "info", "launcher.bin"])

        assert result.exit_code == 0
        assert "Status: ❌ Not executable" in result.output

    @patch("flavor.helpers.manager.HelperManager")
    def test_info_helper_file_not_found(self, mock_manager_class: Mock, tmp_path: Path) -> None:
        """Test info command when helper path doesn't exist."""
        mock_manager = Mock()
        launcher_path = tmp_path / "nonexistent.bin"

        info = HelperInfo(
            name="launcher.bin",
            path=launcher_path,
            type="launcher",
            language="go",
            size=1_000_000,
        )
        mock_manager.get_helper_info.return_value = info
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "info", "launcher.bin"])

        assert result.exit_code == 0
        assert "Status: ❌ File not found" in result.output

    @patch("flavor.helpers.manager.HelperManager")
    def test_info_helper_source_not_found(self, mock_manager_class: Mock, tmp_path: Path) -> None:
        """Test info command when source directory doesn't exist."""
        mock_manager = Mock()
        launcher_path = tmp_path / "launcher.bin"
        launcher_path.write_text("binary")
        launcher_path.chmod(0o755)
        source_path = tmp_path / "missing_src"

        info = HelperInfo(
            name="launcher.bin",
            path=launcher_path,
            type="launcher",
            language="go",
            size=1_000_000,
            built_from=source_path,
        )
        mock_manager.get_helper_info.return_value = info
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "info", "launcher.bin"])

        assert result.exit_code == 0
        assert "Source directory not found" in result.output

    @patch("flavor.helpers.manager.HelperManager")
    def test_info_helper_minimal_fields(self, mock_manager_class: Mock, tmp_path: Path) -> None:
        """Test info command with minimal helper fields."""
        mock_manager = Mock()
        launcher_path = tmp_path / "launcher.bin"
        launcher_path.write_text("binary")

        info = HelperInfo(
            name="launcher.bin",
            path=launcher_path,
            type="launcher",
            language="go",
            size=1_000_000,
            # No version, checksum, or built_from
        )
        mock_manager.get_helper_info.return_value = info
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "info", "launcher.bin"])

        assert result.exit_code == 0
        assert "Type: launcher" in result.output
        assert "Language: go" in result.output
        # Should not crash on missing optional fields


class TestHelperTest:
    """Test suite for 'flavor helpers test' command."""

    @patch("flavor.helpers.manager.HelperManager")
    def test_test_all_passed(self, mock_manager_class: Mock) -> None:
        """Test test command when all tests pass."""
        mock_manager = Mock()
        mock_manager.test_helpers.return_value = {
            "passed": ["launcher-go", "builder-rust"],
            "failed": [],
            "skipped": [],
        }
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "test"])

        assert result.exit_code == 0
        assert "Testing all helpers" in result.output
        assert "Passed: 2" in result.output
        assert "launcher-go" in result.output
        assert "builder-rust" in result.output
        assert "All tests passed" in result.output
        mock_manager.test_helpers.assert_called_once_with(language=None)

    @patch("flavor.helpers.manager.HelperManager")
    def test_test_some_failed(self, mock_manager_class: Mock) -> None:
        """Test test command when some tests fail."""
        mock_manager = Mock()
        mock_manager.test_helpers.return_value = {
            "passed": ["launcher-go"],
            "failed": [{"name": "builder-rust", "error": "Exit code 1", "stderr": "Error output"}],
            "skipped": [],
        }
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "test"])

        assert result.exit_code == 1  # click.Abort() causes exit code 1
        assert "Passed: 1" in result.output
        assert "Failed: 1" in result.output
        assert "builder-rust: Exit code 1" in result.output
        assert "Error output" in result.output
        assert "Some tests failed" in result.output

    @patch("flavor.helpers.manager.HelperManager")
    def test_test_some_skipped(self, mock_manager_class: Mock) -> None:
        """Test test command when some tests are skipped."""
        mock_manager = Mock()
        mock_manager.test_helpers.return_value = {
            "passed": ["launcher-go"],
            "failed": [],
            "skipped": ["builder-missing"],
        }
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "test"])

        assert result.exit_code == 0
        assert "Passed: 1" in result.output
        assert "Skipped: 1" in result.output
        assert "builder-missing" in result.output
        assert "All tests passed" in result.output

    @patch("flavor.helpers.manager.HelperManager")
    def test_test_no_tests_run(self, mock_manager_class: Mock) -> None:
        """Test test command when no tests are run."""
        mock_manager = Mock()
        mock_manager.test_helpers.return_value = {"passed": [], "failed": [], "skipped": []}
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "test"])

        assert result.exit_code == 0
        assert "No tests were run" in result.output

    @patch("flavor.helpers.manager.HelperManager")
    def test_test_go_only(self, mock_manager_class: Mock) -> None:
        """Test test command with Go language only."""
        mock_manager = Mock()
        mock_manager.test_helpers.return_value = {
            "passed": ["launcher-go"],
            "failed": [],
            "skipped": [],
        }
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "test", "--lang", "go"])

        assert result.exit_code == 0
        assert "Testing go helpers" in result.output
        mock_manager.test_helpers.assert_called_once_with(language="go")

    @patch("flavor.helpers.manager.HelperManager")
    def test_test_rust_only(self, mock_manager_class: Mock) -> None:
        """Test test command with Rust language only."""
        mock_manager = Mock()
        mock_manager.test_helpers.return_value = {
            "passed": ["builder-rust"],
            "failed": [],
            "skipped": [],
        }
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "test", "--lang", "rust"])

        assert result.exit_code == 0
        assert "Testing rust helpers" in result.output
        mock_manager.test_helpers.assert_called_once_with(language="rust")

    @patch("flavor.helpers.manager.HelperManager")
    def test_test_failed_without_stderr(self, mock_manager_class: Mock) -> None:
        """Test test command when failure has no stderr."""
        mock_manager = Mock()
        mock_manager.test_helpers.return_value = {
            "passed": [],
            "failed": [{"name": "builder-rust", "error": "Exit code 1"}],
            "skipped": [],
        }
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "test"])

        assert result.exit_code == 1
        assert "builder-rust: Exit code 1" in result.output
        assert "Some tests failed" in result.output


# 🌶️📦🔚
