#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for flavor.helpers.binary_loader - Test and helper methods."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from flavor.helpers.binary_loader import BinaryLoader


class TestTestHelpers:
    """Test test_helpers method."""

    @patch("flavor.helpers.binary_loader.run")
    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_test_helpers_all_passed(self, mock_get_platform: Mock, mock_run: Mock, tmp_path: Path) -> None:
        """Test testing helpers when all pass."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()

        # Mock list_helpers to return test data
        launcher_info = Mock()
        launcher_info.name = "go-launcher"
        launcher_info.language = "go"
        launcher_info.path = tmp_path / "launcher"

        builder_info = Mock()
        builder_info.name = "rs-builder"
        builder_info.language = "rust"
        builder_info.path = tmp_path / "builder"
        mock_manager.list_helpers.return_value = {
            "launchers": [launcher_info],
            "builders": [builder_info],
        }

        # Mock successful version check
        mock_run.return_value = Mock(returncode=0, stdout="1.0.0")

        loader = BinaryLoader(mock_manager)
        result = loader.test_helpers()

        assert len(result["passed"]) == 2
        assert len(result["failed"]) == 0
        assert result["passed"][0]["name"] == "go-launcher"
        assert result["passed"][0]["version"] == "1.0.0"

    @patch("flavor.helpers.binary_loader.run")
    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_test_helpers_some_failed(self, mock_get_platform: Mock, mock_run: Mock, tmp_path: Path) -> None:
        """Test testing helpers when some fail."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()

        launcher_info = Mock()
        launcher_info.name = "go-launcher"
        launcher_info.language = "go"
        launcher_info.path = tmp_path / "launcher"

        builder_info = Mock()
        builder_info.name = "rs-builder"
        builder_info.language = "rust"
        builder_info.path = tmp_path / "builder"

        mock_manager.list_helpers.return_value = {
            "launchers": [launcher_info],
            "builders": [builder_info],
        }

        # First call succeeds, second fails
        mock_run.side_effect = [
            Mock(returncode=0, stdout="1.0.0"),
            Mock(returncode=1, stderr="error output"),
        ]

        loader = BinaryLoader(mock_manager)
        result = loader.test_helpers()

        assert len(result["passed"]) == 1
        assert len(result["failed"]) == 1
        assert result["failed"][0]["name"] == "rs-builder"
        assert "Exit code 1" in result["failed"][0]["error"]

    @patch("flavor.helpers.binary_loader.run")
    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_test_helpers_exception(self, mock_get_platform: Mock, mock_run: Mock, tmp_path: Path) -> None:
        """Test testing helpers when exception occurs."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()

        launcher_info = Mock()
        launcher_info.name = "go-launcher"
        launcher_info.language = "go"
        launcher_info.path = tmp_path / "launcher"
        mock_manager.list_helpers.return_value = {"launchers": [launcher_info], "builders": []}

        # Mock exception
        mock_run.side_effect = Exception("Timeout")

        loader = BinaryLoader(mock_manager)
        result = loader.test_helpers()

        assert len(result["passed"]) == 0
        assert len(result["failed"]) == 1
        assert result["failed"][0]["name"] == "go-launcher"
        assert "Timeout" in result["failed"][0]["error"]

    @patch("flavor.helpers.binary_loader.run")
    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_test_helpers_filter_by_language(
        self, mock_get_platform: Mock, mock_run: Mock, tmp_path: Path
    ) -> None:
        """Test testing helpers filtered by language."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()

        go_launcher = Mock()
        go_launcher.name = "go-launcher"
        go_launcher.language = "go"
        go_launcher.path = tmp_path / "go"

        rs_builder = Mock()
        rs_builder.name = "rs-builder"
        rs_builder.language = "rust"
        rs_builder.path = tmp_path / "rs"
        mock_manager.list_helpers.return_value = {
            "launchers": [go_launcher],
            "builders": [rs_builder],
        }

        mock_run.return_value = Mock(returncode=0, stdout="1.0.0")

        loader = BinaryLoader(mock_manager)
        result = loader.test_helpers(language="go")

        assert len(result["passed"]) == 1
        assert result["passed"][0]["name"] == "go-launcher"


class TestHelperMethods:
    """Test helper methods."""

    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_generate_helper_names(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test _generate_helper_names method."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()

        with patch("flavor.helpers.binary_loader.Path") as mock_path_class:
            mock_bin_dir = tmp_path / "bin"
            mock_bin_dir.mkdir()

            mock_path_instance = Mock()
            mock_parent = Mock()
            mock_parent.__truediv__ = lambda self, x: mock_bin_dir if x == "bin" else Mock()
            mock_path_instance.parent = mock_parent
            mock_path_class.return_value = mock_path_instance

            loader = BinaryLoader(mock_manager)

            with (
                patch.object(loader, "_find_versioned_helpers", return_value=["v1.0.0"]),
                patch.object(loader, "_get_package_version_name", return_value="v0.1.0"),
            ):
                result = loader._generate_helper_names("test-helper")

                assert "v1.0.0" in result
                assert "v0.1.0" in result
                assert "test-helper-linux_x86_64" in result
                assert "test-helper" in result

    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_find_versioned_helpers(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test _find_versioned_helpers method."""
        mock_get_platform.return_value = "darwin_arm64"
        mock_manager = Mock()
        loader = BinaryLoader(mock_manager)

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        # Create versioned files
        (bin_dir / "test-1.0.0-darwin_arm64").write_text("v1")
        (bin_dir / "test-2.0.0-darwin_arm64").write_text("v2")
        (bin_dir / "test-3.0.0").write_text("v3")

        result = loader._find_versioned_helpers(bin_dir, "test")

        assert len(result) >= 2
        assert "test-1.0.0-darwin_arm64" in result or "test-2.0.0-darwin_arm64" in result

    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_get_package_version_name_success(self, mock_get_platform: Mock) -> None:
        """Test _get_package_version_name when version is available."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        loader = BinaryLoader(mock_manager)

        # Mock the __version__ in flavor module
        with patch("flavor.__version__", "1.2.3"):
            result = loader._get_package_version_name("test")
            assert result == "test-1.2.3-linux_x86_64"

    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_get_package_version_name_no_version(self, mock_get_platform: Mock) -> None:
        """Test _get_package_version_name when version not available."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        loader = BinaryLoader(mock_manager)

        # Simulate missing version by making the import fail
        # We need to mock the entire flavor module to not have __version__
        import flavor

        original_version = getattr(flavor, "__version__", None)
        try:
            if hasattr(flavor, "__version__"):
                delattr(flavor, "__version__")
            result = loader._get_package_version_name("test")
            assert result is None
        finally:
            if original_version is not None:
                flavor.__version__ = original_version

    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_remove_duplicates(self, mock_get_platform: Mock) -> None:
        """Test _remove_duplicates method."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        loader = BinaryLoader(mock_manager)

        names = ["a", "b", "a", "c", "b", "d"]
        result = loader._remove_duplicates(names)

        assert result == ["a", "b", "c", "d"]
        assert len(result) == 4

    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_search_helper_locations_embedded(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test _search_helper_locations finds embedded helper."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        mock_manager.helpers_bin = tmp_path / "dist_bin"

        loader = BinaryLoader(mock_manager)

        embedded_bin = tmp_path / "embedded" / "bin"
        embedded_bin.mkdir(parents=True)
        helper_file = embedded_bin / "test-helper"
        helper_file.write_text("binary")

        with patch("flavor.helpers.binary_loader.Path") as mock_path_class:
            mock_path_instance = Mock()
            mock_parent = Mock()
            mock_parent.__truediv__ = lambda self, x: embedded_bin if x == "bin" else Mock()
            mock_path_instance.parent = mock_parent
            mock_path_class.return_value = mock_path_instance

            result = loader._search_helper_locations("test-helper")
            assert result == helper_file

    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_search_helper_locations_local(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test _search_helper_locations finds local helper."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()

        local_bin = tmp_path / "local_bin"
        local_bin.mkdir()
        helper_file = local_bin / "test-helper"
        helper_file.write_text("binary")

        mock_manager.helpers_bin = local_bin

        loader = BinaryLoader(mock_manager)

        with patch("flavor.helpers.binary_loader.Path") as mock_path_class:
            # Need to mock two paths that don't exist:
            # 1. parent / "bin" / name (3 levels)
            # 2. parent / "helpers" / platform / name (4 levels)

            # Mock for final file checks - all return False for exists()
            mock_final_file = Mock()
            mock_final_file.exists.return_value = False

            # Mock for platform level (supports / name)
            mock_platform_dir = Mock()
            mock_platform_dir.exists.return_value = False
            mock_platform_dir.__truediv__ = lambda self, x: mock_final_file

            # Mock for intermediate directories (supports / platform or / name)
            mock_bin_dir = Mock()
            mock_bin_dir.exists.return_value = False
            mock_bin_dir.__truediv__ = lambda self, x: mock_final_file

            mock_helpers_dir = Mock()
            mock_helpers_dir.exists.return_value = False
            mock_helpers_dir.__truediv__ = lambda self, x: mock_platform_dir

            # Mock parent supports / "bin" and / "helpers"
            def mock_parent_truediv(_path_obj: Path, path_component: str) -> Path | Mock:
                if path_component == "bin":
                    return mock_bin_dir
                if path_component == "helpers":
                    return mock_helpers_dir
                return Mock()

            mock_parent = Mock()
            mock_parent.__truediv__ = mock_parent_truediv

            mock_path_instance = Mock()
            mock_path_instance.parent = mock_parent
            mock_path_class.return_value = mock_path_instance

            result = loader._search_helper_locations("test-helper")
            assert result == helper_file

    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_search_helper_locations_not_found(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test _search_helper_locations returns None when not found."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        mock_manager.helpers_bin = tmp_path / "nonexistent"

        loader = BinaryLoader(mock_manager)

        with patch("flavor.helpers.binary_loader.Path") as mock_path_class:
            # Need to mock two paths that don't exist:
            # 1. parent / "bin" / name (3 levels)
            # 2. parent / "helpers" / platform / name (4 levels)

            # Mock for final file checks - all return False for exists()
            mock_final_file = Mock()
            mock_final_file.exists.return_value = False

            # Mock for platform level (supports / name)
            mock_platform_dir = Mock()
            mock_platform_dir.exists.return_value = False
            mock_platform_dir.__truediv__ = lambda self, x: mock_final_file

            # Mock for intermediate directories (supports / platform or / name)
            mock_bin_dir = Mock()
            mock_bin_dir.exists.return_value = False
            mock_bin_dir.__truediv__ = lambda self, x: mock_final_file

            mock_helpers_dir = Mock()
            mock_helpers_dir.exists.return_value = False
            mock_helpers_dir.__truediv__ = lambda self, x: mock_platform_dir

            # Mock parent supports / "bin" and / "helpers"
            def mock_parent_truediv(_path_obj: Path, path_component: str) -> Path | Mock:
                if path_component == "bin":
                    return mock_bin_dir
                if path_component == "helpers":
                    return mock_helpers_dir
                return Mock()

            mock_parent = Mock()
            mock_parent.__truediv__ = mock_parent_truediv

            mock_path_instance = Mock()
            mock_path_instance.parent = mock_parent
            mock_path_class.return_value = mock_path_instance

            result = loader._search_helper_locations("nonexistent")
            assert result is None

    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_ensure_executable_not_executable(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test _ensure_executable makes file executable."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        loader = BinaryLoader(mock_manager)

        test_file = tmp_path / "test_binary"
        test_file.write_text("binary")
        test_file.chmod(0o644)  # Not executable

        with patch("flavor.helpers.binary_loader.os.access", return_value=False):
            loader._ensure_executable(test_file)
            # File should now be executable
            assert test_file.stat().st_mode & 0o111  # Check executable bits

    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_ensure_executable_already_executable(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test _ensure_executable does nothing if already executable."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        loader = BinaryLoader(mock_manager)

        test_file = tmp_path / "test_binary"
        test_file.write_text("binary")
        test_file.chmod(0o755)  # Already executable

        with patch("flavor.helpers.binary_loader.os.access", return_value=True):
            # Should not raise exception
            loader._ensure_executable(test_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# 🌶️📦🔚
