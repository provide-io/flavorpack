#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Comprehensive tests for flavor.commands.helpers list/build paths."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner

from flavor.cli import main as cli_main
from flavor.helpers.manager import HelperInfo


class TestHelperList:
    """Test suite for 'flavor helpers list' command."""

    @patch("flavor.helpers.manager.HelperManager")
    def test_list_empty(self, mock_manager_class: Mock) -> None:
        """Test list command with no helpers."""
        mock_manager = Mock()
        mock_manager.list_helpers.return_value = {"launchers": [], "builders": []}
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "list"])

        assert result.exit_code == 0
        assert "No helpers found" in result.output
        assert "flavor helpers build" in result.output

    @patch("flavor.helpers.manager.HelperManager")
    @patch("flavor.commands.helpers.run")
    def test_list_with_launchers_only(self, mock_run: Mock, mock_manager_class: Mock, tmp_path: Path) -> None:
        """Test list command with launchers only."""
        mock_manager = Mock()
        launcher_path = tmp_path / "flavor-go-launcher-darwin_arm64"
        launcher_info = HelperInfo(
            name="flavor-go-launcher-darwin_arm64",
            path=launcher_path,
            type="launcher",
            language="go",
            size=2_000_000,  # 2MB
            checksum="abc123",
            version="1.0.0",
        )
        mock_manager.list_helpers.return_value = {"launchers": [launcher_info], "builders": []}
        mock_manager_class.return_value = mock_manager

        # Mock version detection
        mock_run.return_value = Mock(returncode=0, stdout="flavor-go-launcher 1.0.0\n")

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "list"])

        assert result.exit_code == 0
        assert "Available Flavor Helpers" in result.output
        assert "Launchers:" in result.output
        assert "flavor-go-launcher-darwin_arm64" in result.output
        assert "(go," in result.output
        assert "1.9 MB)" in result.output  # ~2MB rounded

    @patch("flavor.helpers.manager.HelperManager")
    @patch("flavor.commands.helpers.run")
    def test_list_with_builders_only(self, mock_run: Mock, mock_manager_class: Mock, tmp_path: Path) -> None:
        """Test list command with builders only."""
        mock_manager = Mock()
        builder_path = tmp_path / "flavor-rs-builder-linux_x86_64"
        builder_info = HelperInfo(
            name="flavor-rs-builder-linux_x86_64",
            path=builder_path,
            type="builder",
            language="rust",
            size=3_500_000,  # 3.5MB
            checksum="def456",
        )
        mock_manager.list_helpers.return_value = {"launchers": [], "builders": [builder_info]}
        mock_manager_class.return_value = mock_manager

        # Mock version detection failure
        mock_run.return_value = Mock(returncode=1, stdout="")

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "list"])

        assert result.exit_code == 0
        assert "Builders:" in result.output
        assert "flavor-rs-builder-linux_x86_64" in result.output
        assert "(rust," in result.output
        assert "3.3 MB)" in result.output
        assert "unknown" in result.output  # Version detection failed

    @patch("flavor.helpers.manager.HelperManager")
    @patch("flavor.commands.helpers.run")
    def test_list_with_both_types(self, mock_run: Mock, mock_manager_class: Mock, tmp_path: Path) -> None:
        """Test list command with both launchers and builders."""
        mock_manager = Mock()
        launcher_path = tmp_path / "launcher"
        builder_path = tmp_path / "builder"
        launcher_info = HelperInfo(
            name="launcher", path=launcher_path, type="launcher", language="go", size=2_000_000
        )
        builder_info = HelperInfo(
            name="builder", path=builder_path, type="builder", language="rust", size=3_000_000
        )
        mock_manager.list_helpers.return_value = {
            "launchers": [launcher_info],
            "builders": [builder_info],
        }
        mock_manager_class.return_value = mock_manager

        mock_run.return_value = Mock(returncode=0, stdout="version 1.0.0\n")

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "list"])

        assert result.exit_code == 0
        assert "Launchers:" in result.output
        assert "Builders:" in result.output
        assert "launcher" in result.output
        assert "builder" in result.output

    @patch("flavor.helpers.manager.HelperManager")
    @patch("flavor.commands.helpers.run")
    def test_list_verbose_mode(self, mock_run: Mock, mock_manager_class: Mock, tmp_path: Path) -> None:
        """Test list command with verbose flag shows checksums and source."""
        mock_manager = Mock()
        launcher_path = tmp_path / "launcher"
        source_path = tmp_path / "src"
        launcher_info = HelperInfo(
            name="launcher",
            path=launcher_path,
            type="launcher",
            language="go",
            size=2_000_000,
            checksum="abc123def456",
            version="1.0.0",
            built_from=source_path,
        )
        mock_manager.list_helpers.return_value = {"launchers": [launcher_info], "builders": []}
        mock_manager_class.return_value = mock_manager

        mock_run.return_value = Mock(returncode=0, stdout="1.0.0\n")

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "list", "--verbose"])

        assert result.exit_code == 0
        assert "SHA256: abc123def456" in result.output
        assert f"Source: {source_path}" in result.output

    @patch("flavor.helpers.manager.HelperManager")
    @patch("flavor.commands.helpers.run")
    def test_list_multiple_launchers_sorted(
        self, mock_run: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test list command sorts helpers by name."""
        mock_manager = Mock()
        launcher_z = HelperInfo(
            name="z-launcher", path=tmp_path / "z", type="launcher", language="go", size=1_000_000
        )
        launcher_a = HelperInfo(
            name="a-launcher", path=tmp_path / "a", type="launcher", language="rust", size=1_000_000
        )
        mock_manager.list_helpers.return_value = {
            "launchers": [launcher_z, launcher_a],  # Unsorted
            "builders": [],
        }
        mock_manager_class.return_value = mock_manager

        mock_run.return_value = Mock(returncode=0, stdout="1.0.0\n")

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "list"])

        assert result.exit_code == 0
        # Check that a-launcher appears before z-launcher in output
        a_pos = result.output.find("a-launcher")
        z_pos = result.output.find("z-launcher")
        assert a_pos < z_pos

    @patch("flavor.helpers.manager.HelperManager")
    @patch("flavor.commands.helpers.run")
    def test_list_version_timeout(self, mock_run: Mock, mock_manager_class: Mock, tmp_path: Path) -> None:
        """Test list command handles version detection timeout gracefully."""
        mock_manager = Mock()
        launcher_info = HelperInfo(
            name="launcher", path=tmp_path / "launcher", type="launcher", language="go", size=1_000_000
        )
        mock_manager.list_helpers.return_value = {"launchers": [launcher_info], "builders": []}
        mock_manager_class.return_value = mock_manager

        # Simulate timeout
        mock_run.side_effect = Exception("Timeout")

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "list"])

        assert result.exit_code == 0
        assert "unknown" in result.output  # Falls back to unknown version

    @patch("flavor.helpers.manager.HelperManager")
    @patch("flavor.commands.helpers.run")
    def test_list_version_empty_output(self, mock_run: Mock, mock_manager_class: Mock, tmp_path: Path) -> None:
        """Test list command handles empty version output."""
        mock_manager = Mock()
        launcher_info = HelperInfo(
            name="launcher", path=tmp_path / "launcher", type="launcher", language="go", size=1_000_000
        )
        mock_manager.list_helpers.return_value = {"launchers": [launcher_info], "builders": []}
        mock_manager_class.return_value = mock_manager

        # Simulate successful run but empty output
        mock_run.return_value = Mock(returncode=0, stdout="")

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "list"])

        assert result.exit_code == 0
        assert "unknown" in result.output  # Falls back to unknown version

    @patch("flavor.helpers.manager.HelperManager")
    @patch("flavor.commands.helpers.run")
    def test_list_multiple_builders_sorted(
        self, mock_run: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test list command with multiple builders shows newlines between entries."""
        mock_manager = Mock()
        builder_a = HelperInfo(
            name="a-builder", path=tmp_path / "a", type="builder", language="rust", size=1_000_000
        )
        builder_z = HelperInfo(
            name="z-builder", path=tmp_path / "z", type="builder", language="rust", size=1_000_000
        )
        mock_manager.list_helpers.return_value = {
            "launchers": [],
            "builders": [builder_z, builder_a],  # Unsorted
        }
        mock_manager_class.return_value = mock_manager

        mock_run.return_value = Mock(returncode=0, stdout="1.0.0\n")

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "list"])

        assert result.exit_code == 0
        # Check that a-builder appears before z-builder
        a_pos = result.output.find("a-builder")
        z_pos = result.output.find("z-builder")
        assert a_pos < z_pos

    @patch("flavor.helpers.manager.HelperManager")
    @patch("flavor.commands.helpers.run")
    def test_list_verbose_mode_builders(
        self, mock_run: Mock, mock_manager_class: Mock, tmp_path: Path
    ) -> None:
        """Test list verbose mode shows builder source paths."""
        mock_manager = Mock()
        builder_path = tmp_path / "builder"
        source_path = tmp_path / "src"
        builder_info = HelperInfo(
            name="builder",
            path=builder_path,
            type="builder",
            language="rust",
            size=3_000_000,
            checksum="def456",
            version="2.0.0",
            built_from=source_path,
        )
        mock_manager.list_helpers.return_value = {"launchers": [], "builders": [builder_info]}
        mock_manager_class.return_value = mock_manager

        mock_run.return_value = Mock(returncode=0, stdout="2.0.0\n")

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "list", "--verbose"])

        assert result.exit_code == 0
        assert f"Source: {source_path}" in result.output


class TestHelperBuild:
    """Test suite for 'flavor helpers build' command."""

    @patch("flavor.helpers.manager.HelperManager")
    def test_build_all_success(self, mock_manager_class: Mock, tmp_path: Path) -> None:
        """Test build command with all languages (default)."""
        mock_manager = Mock()
        built_paths = [tmp_path / "launcher.bin", tmp_path / "builder.bin"]
        for path in built_paths:
            path.write_text("binary")
        mock_manager.build_helpers.return_value = built_paths
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "build"])

        assert result.exit_code == 0
        assert "Building all helpers" in result.output
        assert "Built 2 helper(s)" in result.output
        assert "launcher.bin" in result.output
        assert "builder.bin" in result.output
        mock_manager.build_helpers.assert_called_once_with(language=None, force=False)

    @patch("flavor.helpers.manager.HelperManager")
    def test_build_go_only(self, mock_manager_class: Mock, tmp_path: Path) -> None:
        """Test build command with Go language only."""
        mock_manager = Mock()
        built_path = tmp_path / "go-launcher.bin"
        built_path.write_text("go binary")
        mock_manager.build_helpers.return_value = [built_path]
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "build", "--lang", "go"])

        assert result.exit_code == 0
        assert "Building go helpers" in result.output
        assert "Built 1 helper(s)" in result.output
        mock_manager.build_helpers.assert_called_once_with(language="go", force=False)

    @patch("flavor.helpers.manager.HelperManager")
    def test_build_rust_only(self, mock_manager_class: Mock, tmp_path: Path) -> None:
        """Test build command with Rust language only."""
        mock_manager = Mock()
        built_path = tmp_path / "rust-builder.bin"
        built_path.write_text("rust binary")
        mock_manager.build_helpers.return_value = [built_path]
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "build", "--lang", "rust"])

        assert result.exit_code == 0
        assert "Building rust helpers" in result.output
        mock_manager.build_helpers.assert_called_once_with(language="rust", force=False)

    @patch("flavor.helpers.manager.HelperManager")
    def test_build_with_force_flag(self, mock_manager_class: Mock, tmp_path: Path) -> None:
        """Test build command with force flag."""
        mock_manager = Mock()
        built_path = tmp_path / "launcher.bin"
        built_path.write_text("binary")
        mock_manager.build_helpers.return_value = [built_path]
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "build", "--force"])

        assert result.exit_code == 0
        mock_manager.build_helpers.assert_called_once_with(language=None, force=True)

    @patch("flavor.helpers.manager.HelperManager")
    def test_build_no_helpers_built(self, mock_manager_class: Mock) -> None:
        """Test build command when no helpers are built."""
        mock_manager = Mock()
        mock_manager.build_helpers.return_value = []
        mock_manager_class.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(cli_main, ["helpers", "build"])

        assert result.exit_code == 0
        assert "No helpers were built" in result.output
        assert "Make sure you have the required compilers installed" in result.output
        assert "go version" in result.output
        assert "cargo --version" in result.output


# 🌶️📦🔚
