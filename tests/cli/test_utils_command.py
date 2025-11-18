#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Comprehensive tests for the `flavor clean` utility command."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

from click.testing import CliRunner

from flavor.cli import main as cli_main


def setup_helper_dir_mock(mock_path_class: Mock, helper_dir: Mock) -> None:
    """Helper to setup Path.home() / ".cache" / "flavor" / "bin" mock chain."""
    mock_path_class.home.return_value = MagicMock()
    mock_path_class.home.return_value.__truediv__.return_value = MagicMock()
    mock_path_class.home.return_value.__truediv__.return_value.__truediv__.return_value = MagicMock()
    mock_path_class.home.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = helper_dir


class TestCleanCommand:
    """Test suite for 'flavor clean' command."""

    @patch("flavor.cache.CacheManager")
    def test_clean_default_with_cache(self, mock_cache_class: Mock) -> None:
        """Test default clean behavior (workenv only) with cached packages."""
        mock_cache = Mock()
        mock_cache.list_cached.return_value = [
            {"id": "pkg1", "name": "package-1", "size": 1_000_000},
            {"id": "pkg2", "name": "package-2", "size": 2_000_000},
        ]
        mock_cache.get_cache_size.return_value = 3_000_000
        mock_cache.clean.return_value = ["pkg1", "pkg2"]
        mock_cache_class.return_value = mock_cache

        runner = CliRunner()
        result = runner.invoke(cli_main, ["clean", "--yes"])

        assert result.exit_code == 0
        assert "Removed 2 cached packages" in result.output
        assert "Total freed: 2.9 MB" in result.output
        mock_cache.clean.assert_called_once()

    @patch("flavor.cache.CacheManager")
    def test_clean_default_empty_cache(self, mock_cache_class: Mock) -> None:
        """Test default clean with empty cache."""
        mock_cache = Mock()
        mock_cache.list_cached.return_value = []
        mock_cache_class.return_value = mock_cache

        runner = CliRunner()
        result = runner.invoke(cli_main, ["clean", "--yes"])

        assert result.exit_code == 0
        mock_cache.clean.assert_not_called()

    @patch("flavor.cache.CacheManager")
    @patch("click.confirm")
    def test_clean_with_confirmation_prompt(self, mock_confirm: Mock, mock_cache_class: Mock) -> None:
        """Test clean with user confirmation prompt."""
        mock_cache = Mock()
        mock_cache.list_cached.return_value = [{"id": "pkg1", "name": "package-1", "size": 5_000_000}]
        mock_cache.get_cache_size.return_value = 5_000_000
        mock_cache.clean.return_value = ["pkg1"]
        mock_cache_class.return_value = mock_cache

        mock_confirm.return_value = True

        runner = CliRunner()
        result = runner.invoke(cli_main, ["clean"])

        assert result.exit_code == 0
        assert "Removed 1 cached packages" in result.output
        mock_confirm.assert_called_once()
        assert "4.8 MB" in str(mock_confirm.call_args)

    @patch("flavor.cache.CacheManager")
    @patch("click.confirm")
    def test_clean_user_aborts(self, mock_confirm: Mock, mock_cache_class: Mock) -> None:
        """Test clean when user aborts confirmation."""
        mock_cache = Mock()
        mock_cache.list_cached.return_value = [{"id": "pkg1", "name": "package-1", "size": 1_000_000}]
        mock_cache.get_cache_size.return_value = 1_000_000
        mock_cache_class.return_value = mock_cache

        mock_confirm.return_value = False

        runner = CliRunner()
        result = runner.invoke(cli_main, ["clean"])

        assert result.exit_code == 0
        assert "Aborted." in result.output
        mock_cache.clean.assert_not_called()

    @patch("flavor.cache.CacheManager")
    def test_clean_dry_run_default(self, mock_cache_class: Mock) -> None:
        """Test clean --dry-run shows what would be removed."""
        mock_cache = Mock()
        mock_cache.list_cached.return_value = [
            {"id": "pkg1", "name": "package-1", "size": 1_500_000},
            {"id": "pkg2", "name": "package-2", "size": 2_500_000},
        ]
        mock_cache.get_cache_size.return_value = 4_000_000
        mock_cache_class.return_value = mock_cache

        runner = CliRunner()
        result = runner.invoke(cli_main, ["clean", "--dry-run"])

        assert result.exit_code == 0
        assert "DRY RUN - Nothing will be removed" in result.output
        assert "Would remove 2 cached packages" in result.output
        assert "package-1 (1.4 MB)" in result.output
        assert "package-2 (2.4 MB)" in result.output
        mock_cache.clean.assert_not_called()

    @patch("flavor.commands.utils.safe_rmtree")
    @patch("flavor.commands.utils.Path")
    @patch("flavor.cache.CacheManager")
    def test_clean_helpers_flag(
        self, mock_cache_class: Mock, mock_path_class: Mock, mock_rmtree: Mock
    ) -> None:
        """Test clean --helpers flag."""
        # Setup cache mock (should not be called for helpers-only)
        mock_cache = Mock()
        mock_cache.list_cached.return_value = []
        mock_cache_class.return_value = mock_cache

        # Setup Path mock for helper directory
        mock_helper_dir = Mock()
        mock_helper_dir.exists.return_value = True

        # Mock helper files
        mock_file1 = Mock()
        mock_file1.name = "flavor-go-launcher"
        mock_file1.suffix = ""
        mock_file1.stat.return_value.st_size = 3_000_000

        mock_file2 = Mock()
        mock_file2.name = "flavor-rs-builder"
        mock_file2.suffix = ""
        mock_file2.stat.return_value.st_size = 4_000_000

        mock_helper_dir.glob.return_value = [mock_file1, mock_file2]

        setup_helper_dir_mock(mock_path_class, mock_helper_dir)

        runner = CliRunner()
        result = runner.invoke(cli_main, ["clean", "--helpers", "--yes"])

        assert result.exit_code == 0
        assert "Removed 2 helper binaries" in result.output
        mock_rmtree.assert_called_once_with(mock_helper_dir)

    @patch("flavor.commands.utils.Path")
    @patch("flavor.cache.CacheManager")
    def test_clean_helpers_not_exist(self, mock_cache_class: Mock, mock_path_class: Mock) -> None:
        """Test clean --helpers when helper dir doesn't exist."""
        mock_cache = Mock()
        mock_cache.list_cached.return_value = []
        mock_cache_class.return_value = mock_cache

        mock_helper_dir = Mock()
        mock_helper_dir.exists.return_value = False

        setup_helper_dir_mock(mock_path_class, mock_helper_dir)

        runner = CliRunner()
        result = runner.invoke(cli_main, ["clean", "--helpers", "--yes"])

        assert result.exit_code == 0
        # Should complete without error even though no helpers exist

    @patch("flavor.commands.utils.safe_rmtree")
    @patch("flavor.commands.utils.Path")
    @patch("flavor.cache.CacheManager")
    def test_clean_all_flag(self, mock_cache_class: Mock, mock_path_class: Mock, mock_rmtree: Mock) -> None:
        """Test clean --all cleans both workenv and helpers."""
        # Setup cache mock
        mock_cache = Mock()
        mock_cache.list_cached.return_value = [{"id": "pkg1", "name": "package-1", "size": 2_000_000}]
        mock_cache.get_cache_size.return_value = 2_000_000
        mock_cache.clean.return_value = ["pkg1"]
        mock_cache_class.return_value = mock_cache

        # Setup helpers mock
        mock_helper_dir = Mock()
        mock_helper_dir.exists.return_value = True

        mock_file = Mock()
        mock_file.name = "flavor-go-launcher"
        mock_file.suffix = ""
        mock_file.stat.return_value.st_size = 3_000_000

        mock_helper_dir.glob.return_value = [mock_file]

        setup_helper_dir_mock(mock_path_class, mock_helper_dir)

        runner = CliRunner()
        result = runner.invoke(cli_main, ["clean", "--all", "--yes"])

        assert result.exit_code == 0
        assert "Removed 1 cached packages" in result.output
        assert "Removed 1 helper binaries" in result.output
        assert "Total freed: 4.8 MB" in result.output
        mock_cache.clean.assert_called_once()
        mock_rmtree.assert_called_once()

    @patch("flavor.commands.utils.Path")
    @patch("flavor.cache.CacheManager")
    def test_clean_dry_run_helpers(self, mock_cache_class: Mock, mock_path_class: Mock) -> None:
        """Test clean --helpers --dry-run."""
        mock_cache = Mock()
        mock_cache.list_cached.return_value = []
        mock_cache_class.return_value = mock_cache

        mock_helper_dir = Mock()
        mock_helper_dir.exists.return_value = True

        mock_file = Mock()
        mock_file.name = "flavor-rs-builder"
        mock_file.suffix = ""
        mock_file.stat.return_value.st_size = 5_000_000

        mock_helper_dir.glob.return_value = [mock_file]

        setup_helper_dir_mock(mock_path_class, mock_helper_dir)

        runner = CliRunner()
        result = runner.invoke(cli_main, ["clean", "--helpers", "--dry-run"])

        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert "Would remove 1 helper binaries" in result.output
        assert "flavor-rs-builder (4.8 MB)" in result.output

    @patch("flavor.commands.utils.Path")
    @patch("flavor.cache.CacheManager")
    def test_clean_dry_run_all(self, mock_cache_class: Mock, mock_path_class: Mock) -> None:
        """Test clean --all --dry-run."""
        mock_cache = Mock()
        mock_cache.list_cached.return_value = [{"id": "pkg1", "name": "package-1", "size": 1_000_000}]
        mock_cache.get_cache_size.return_value = 1_000_000
        mock_cache_class.return_value = mock_cache

        mock_helper_dir = Mock()
        mock_helper_dir.exists.return_value = True

        mock_file = Mock()
        mock_file.name = "flavor-go-launcher"
        mock_file.suffix = ""
        mock_file.stat.return_value.st_size = 2_000_000

        mock_helper_dir.glob.return_value = [mock_file]

        setup_helper_dir_mock(mock_path_class, mock_helper_dir)

        runner = CliRunner()
        result = runner.invoke(cli_main, ["clean", "--all", "--dry-run"])

        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert "Would remove 1 cached packages" in result.output
        assert "Would remove 1 helper binaries" in result.output

    @patch("flavor.commands.utils.Path")
    @patch("flavor.cache.CacheManager")
    def test_clean_helpers_empty_directory(self, mock_cache_class: Mock, mock_path_class: Mock) -> None:
        """Test clean --helpers when directory exists but is empty."""
        mock_cache = Mock()
        mock_cache.list_cached.return_value = []
        mock_cache_class.return_value = mock_cache

        mock_helper_dir = Mock()
        mock_helper_dir.exists.return_value = True
        mock_helper_dir.glob.return_value = []

        setup_helper_dir_mock(mock_path_class, mock_helper_dir)

        runner = CliRunner()
        result = runner.invoke(cli_main, ["clean", "--helpers", "--yes"])

        assert result.exit_code == 0

    @patch("flavor.commands.utils.Path")
    @patch("flavor.cache.CacheManager")
    @patch("click.confirm")
    def test_clean_helpers_user_aborts(
        self, mock_confirm: Mock, mock_cache_class: Mock, mock_path_class: Mock
    ) -> None:
        """Test clean --helpers when user aborts confirmation."""
        mock_cache = Mock()
        mock_cache.list_cached.return_value = []
        mock_cache_class.return_value = mock_cache

        mock_helper_dir = Mock()
        mock_helper_dir.exists.return_value = True

        mock_file = Mock()
        mock_file.name = "flavor-go-launcher"
        mock_file.suffix = ""
        mock_file.stat.return_value.st_size = 3_000_000

        mock_helper_dir.glob.return_value = [mock_file]

        setup_helper_dir_mock(mock_path_class, mock_helper_dir)

        mock_confirm.return_value = False

        runner = CliRunner()
        result = runner.invoke(cli_main, ["clean", "--helpers"])

        assert result.exit_code == 0
        assert "Aborted." in result.output

    @patch("flavor.commands.utils.Path")
    @patch("flavor.cache.CacheManager")
    def test_clean_excludes_d_files(self, mock_cache_class: Mock, mock_path_class: Mock) -> None:
        """Test that .d files are excluded from helper list."""
        mock_cache = Mock()
        mock_cache.list_cached.return_value = []
        mock_cache_class.return_value = mock_cache

        mock_helper_dir = Mock()
        mock_helper_dir.exists.return_value = True

        # Mock both regular file and .d file
        mock_file = Mock()
        mock_file.name = "flavor-go-launcher"
        mock_file.suffix = ""
        mock_file.stat.return_value.st_size = 3_000_000

        mock_d_file = Mock()
        mock_d_file.name = "flavor-go-launcher.d"
        mock_d_file.suffix = ".d"

        mock_helper_dir.glob.return_value = [mock_file, mock_d_file]

        setup_helper_dir_mock(mock_path_class, mock_helper_dir)

        runner = CliRunner()
        result = runner.invoke(cli_main, ["clean", "--helpers", "--dry-run"])

        assert result.exit_code == 0
        # Should only show 1 file (excluding .d file)
        assert "Would remove 1 helper binaries" in result.output
        assert "flavor-go-launcher.d" not in result.output

    @patch("flavor.cache.CacheManager")
    def test_clean_no_total_when_nothing_freed(self, mock_cache_class: Mock) -> None:
        """Test that total freed message is not shown when nothing is freed."""
        mock_cache = Mock()
        mock_cache.list_cached.return_value = []
        mock_cache_class.return_value = mock_cache

        runner = CliRunner()
        result = runner.invoke(cli_main, ["clean", "--yes"])

        assert result.exit_code == 0
        assert "Total freed" not in result.output

    @patch("flavor.cache.CacheManager")
    def test_clean_cache_with_name_field(self, mock_cache_class: Mock) -> None:
        """Test clean properly uses name field from cached packages."""
        mock_cache = Mock()
        mock_cache.list_cached.return_value = [
            {"id": "pkg-xyz-123", "name": "my-awesome-package", "size": 2_000_000}
        ]
        mock_cache.get_cache_size.return_value = 2_000_000
        mock_cache_class.return_value = mock_cache

        runner = CliRunner()
        result = runner.invoke(cli_main, ["clean", "--dry-run"])

        assert result.exit_code == 0
        assert "my-awesome-package" in result.output

    @patch("flavor.cache.CacheManager")
    def test_clean_cache_without_name_field(self, mock_cache_class: Mock) -> None:
        """Test clean falls back to id when name field is missing."""
        mock_cache = Mock()
        mock_cache.list_cached.return_value = [
            {"id": "pkg-id-only", "size": 1_500_000}  # No name field
        ]
        mock_cache.get_cache_size.return_value = 1_500_000
        mock_cache_class.return_value = mock_cache

        runner = CliRunner()
        result = runner.invoke(cli_main, ["clean", "--dry-run"])

        assert result.exit_code == 0
        assert "pkg-id-only" in result.output

    @patch("flavor.cache.CacheManager")
    def test_clean_cache_clean_returns_empty(self, mock_cache_class: Mock) -> None:
        """Test clean when cache clean operation returns empty list."""
        mock_cache = Mock()
        mock_cache.list_cached.return_value = [{"id": "pkg1", "name": "package-1", "size": 1_000_000}]
        mock_cache.get_cache_size.return_value = 1_000_000
        mock_cache.clean.return_value = []  # Clean fails or returns empty
        mock_cache_class.return_value = mock_cache

        runner = CliRunner()
        result = runner.invoke(cli_main, ["clean", "--yes"])

        assert result.exit_code == 0
        # Should not show "Removed" message or total freed
        assert "Total freed" not in result.output


# 🌶️📦🔚
