# tests/ingredients/test_binary_loader.py
#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Comprehensive tests for flavor.ingredients.binary_loader module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from flavor.ingredients.binary_loader import BinaryLoader


class TestBinaryLoaderInit:
    """Test BinaryLoader initialization."""

    def test_init(self) -> None:
        """Test BinaryLoader initialization."""
        mock_manager = Mock()
        loader = BinaryLoader(mock_manager)
        assert loader.manager is mock_manager

    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_current_platform_property(self, mock_get_platform: Mock) -> None:
        """Test current_platform property."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        loader = BinaryLoader(mock_manager)
        assert loader.current_platform == "linux_x86_64"


class TestGetIngredient:
    """Test get_ingredient method."""

    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_get_ingredient_found_embedded(
        self, mock_get_platform: Mock, tmp_path: Path
    ) -> None:
        """Test get_ingredient finds embedded ingredient."""
        mock_get_platform.return_value = "darwin_arm64"
        mock_manager = Mock()
        mock_manager.ingredients_bin = tmp_path / "dist_bin"

        # Create embedded bin directory
        embedded_bin = tmp_path / "embedded_bin"
        embedded_bin.mkdir()
        ingredient_file = embedded_bin / "flavor-go-launcher-darwin_arm64"
        ingredient_file.write_text("binary")
        ingredient_file.chmod(0o755)

        with patch("flavor.ingredients.binary_loader.Path") as mock_path_class:
            # Mock Path(__file__).parent to return our tmp_path
            mock_path_class.__file__ = str(tmp_path / "binary_loader.py")
            mock_path_instance = Mock()
            mock_path_instance.parent = tmp_path
            mock_path_instance.parent.__truediv__ = lambda self, x: embedded_bin if x == "bin" else Mock()
            mock_path_class.return_value = mock_path_instance

            loader = BinaryLoader(mock_manager)
            # Mock the _search_ingredient_locations to return our file
            with patch.object(loader, "_search_ingredient_locations", return_value=ingredient_file):
                result = loader.get_ingredient("flavor-go-launcher")
                assert result == ingredient_file

    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_get_ingredient_not_found(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test get_ingredient raises FileNotFoundError when not found."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        mock_manager.ingredients_bin = tmp_path / "bin"

        loader = BinaryLoader(mock_manager)
        # Mock _search_ingredient_locations to return None (not found)
        with patch.object(loader, "_search_ingredient_locations", return_value=None):
            with pytest.raises(FileNotFoundError, match="Ingredient 'test-ingredient' not found"):
                loader.get_ingredient("test-ingredient")


class TestBuildIngredients:
    """Test build_ingredients methods."""

    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_build_ingredients_all(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test building all ingredients (go and rust)."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        mock_manager.go_src_dir = tmp_path / "go_src"
        mock_manager.rust_src_dir = tmp_path / "rust_src"
        mock_manager.ingredients_bin = tmp_path / "bin"

        loader = BinaryLoader(mock_manager)

        go_binaries = [tmp_path / "go-launcher", tmp_path / "go-builder"]
        rust_binaries = [tmp_path / "rs-launcher", tmp_path / "rs-builder"]

        with patch.object(loader, "_build_go_ingredients", return_value=go_binaries):
            with patch.object(loader, "_build_rust_ingredients", return_value=rust_binaries):
                result = loader.build_ingredients(language=None, force=False)

                assert len(result) == 4
                assert go_binaries[0] in result
                assert rust_binaries[0] in result

    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_build_ingredients_go_only(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test building go ingredients only."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        loader = BinaryLoader(mock_manager)

        go_binaries = [tmp_path / "go-launcher"]

        with patch.object(loader, "_build_go_ingredients", return_value=go_binaries) as mock_go:
            with patch.object(loader, "_build_rust_ingredients") as mock_rust:
                result = loader.build_ingredients(language="go", force=True)

                mock_go.assert_called_once_with(True)
                mock_rust.assert_not_called()
                assert result == go_binaries

    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_build_ingredients_rust_only(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test building rust ingredients only."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        loader = BinaryLoader(mock_manager)

        rust_binaries = [tmp_path / "rs-builder"]

        with patch.object(loader, "_build_go_ingredients") as mock_go:
            with patch.object(loader, "_build_rust_ingredients", return_value=rust_binaries) as mock_rust:
                result = loader.build_ingredients(language="rust", force=False)

                mock_go.assert_not_called()
                mock_rust.assert_called_once_with(False)
                assert result == rust_binaries


class TestBuildGoIngredients:
    """Test _build_go_ingredients method."""

    @patch("flavor.ingredients.binary_loader.ensure_dir")
    @patch("flavor.ingredients.binary_loader.run")
    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_build_go_ingredients_source_not_found(
        self, mock_get_platform: Mock, mock_run: Mock, mock_ensure_dir: Mock, tmp_path: Path
    ) -> None:
        """Test building go ingredients when source directory doesn't exist."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        mock_go_src = Mock()
        mock_go_src.exists.return_value = False
        mock_manager.go_src_dir = mock_go_src

        loader = BinaryLoader(mock_manager)
        result = loader._build_go_ingredients(force=False)

        assert result == []
        mock_run.assert_not_called()

    @patch("flavor.ingredients.binary_loader.ensure_dir")
    @patch("flavor.ingredients.binary_loader.run")
    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_build_go_ingredients_already_exists_no_force(
        self, mock_get_platform: Mock, mock_run: Mock, mock_ensure_dir: Mock, tmp_path: Path
    ) -> None:
        """Test building go ingredients when binaries exist and force=False."""
        mock_get_platform.return_value = "darwin_arm64"
        mock_manager = Mock()
        mock_go_src = Mock()
        mock_go_src.exists.return_value = True
        mock_manager.go_src_dir = mock_go_src
        mock_manager.ingredients_bin = tmp_path / "bin"

        # Create existing binaries
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        launcher = bin_dir / "flavor-go-launcher-darwin_arm64"
        builder = bin_dir / "flavor-go-builder-darwin_arm64"
        launcher.write_text("existing")
        builder.write_text("existing")

        # Mock Path operations for the binary paths
        mock_manager.ingredients_bin.__truediv__ = lambda self, x: bin_dir / x

        loader = BinaryLoader(mock_manager)
        result = loader._build_go_ingredients(force=False)

        # Should return existing binaries without building
        assert len(result) == 2
        mock_run.assert_not_called()

    @patch("flavor.ingredients.binary_loader.ensure_dir")
    @patch("flavor.ingredients.binary_loader.run")
    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_build_go_ingredients_success(
        self, mock_get_platform: Mock, mock_run: Mock, mock_ensure_dir: Mock, tmp_path: Path
    ) -> None:
        """Test successful go ingredients build."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        mock_go_src = Mock()
        mock_go_src.exists.return_value = True
        mock_manager.go_src_dir = mock_go_src
        mock_manager.ingredients_bin = tmp_path / "bin"

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        # Mock successful build
        mock_run.return_value = Mock(returncode=0)

        # Setup Path mocking
        def mock_truediv(name: str) -> Path:
            p = bin_dir / name
            # Create the file when accessed
            if not p.exists():
                p.write_text("binary")
            return p

        mock_manager.ingredients_bin.__truediv__ = mock_truediv

        loader = BinaryLoader(mock_manager)
        result = loader._build_go_ingredients(force=True)

        assert len(result) == 2
        assert mock_run.call_count == 2

    @patch("flavor.ingredients.binary_loader.ensure_dir")
    @patch("flavor.ingredients.binary_loader.run")
    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_build_go_ingredients_build_failure(
        self, mock_get_platform: Mock, mock_run: Mock, mock_ensure_dir: Mock, tmp_path: Path
    ) -> None:
        """Test go ingredients build failure."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        mock_go_src = Mock()
        mock_go_src.exists.return_value = True
        mock_manager.go_src_dir = mock_go_src
        mock_manager.ingredients_bin = tmp_path / "bin"

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        # Mock failed build
        mock_run.return_value = Mock(returncode=1, stderr="build error")

        mock_manager.ingredients_bin.__truediv__ = lambda name: bin_dir / name

        loader = BinaryLoader(mock_manager)
        result = loader._build_go_ingredients(force=True)

        assert result == []


class TestBuildRustIngredients:
    """Test _build_rust_ingredients method."""

    @patch("flavor.ingredients.binary_loader.ensure_dir")
    @patch("flavor.ingredients.binary_loader.run")
    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_build_rust_ingredients_source_not_found(
        self, mock_get_platform: Mock, mock_run: Mock, mock_ensure_dir: Mock, tmp_path: Path
    ) -> None:
        """Test building rust ingredients when source directory doesn't exist."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        mock_rust_src = Mock()
        mock_rust_src.exists.return_value = False
        mock_manager.rust_src_dir = mock_rust_src

        loader = BinaryLoader(mock_manager)
        result = loader._build_rust_ingredients(force=False)

        assert result == []
        mock_run.assert_not_called()

    @patch("flavor.ingredients.binary_loader.ensure_dir")
    @patch("flavor.ingredients.binary_loader.safe_copy")
    @patch("flavor.ingredients.binary_loader.run")
    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_build_rust_ingredients_success(
        self,
        mock_get_platform: Mock,
        mock_run: Mock,
        mock_safe_copy: Mock,
        mock_ensure_dir: Mock,
        tmp_path: Path,
    ) -> None:
        """Test successful rust ingredients build."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        mock_rust_src = tmp_path / "rust_src"
        mock_rust_src.mkdir()
        mock_manager.rust_src_dir = mock_rust_src
        mock_manager.ingredients_bin = tmp_path / "bin"

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        # Create target/release directory
        target_dir = tmp_path / "rust_src" / "target" / "release"
        target_dir.mkdir(parents=True)
        (target_dir / "flavor-rs-launcher").write_text("binary")
        (target_dir / "flavor-rs-builder").write_text("binary")

        # Mock successful build
        mock_run.return_value = Mock(returncode=0)

        def mock_truediv(name: str) -> Path:
            p = bin_dir / name
            if not p.exists():
                p.write_text("binary")
            return p

        mock_manager.ingredients_bin.__truediv__ = mock_truediv

        loader = BinaryLoader(mock_manager)
        result = loader._build_rust_ingredients(force=True)

        assert len(result) == 2
        assert mock_run.call_count == 2
        assert mock_safe_copy.call_count == 2

    @patch("flavor.ingredients.binary_loader.ensure_dir")
    @patch("flavor.ingredients.binary_loader.run")
    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_build_rust_ingredients_built_but_not_found(
        self, mock_get_platform: Mock, mock_run: Mock, mock_ensure_dir: Mock, tmp_path: Path
    ) -> None:
        """Test rust build succeeds but binary not found in target/release."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        mock_rust_src = tmp_path / "rust_src"
        mock_rust_src.mkdir()
        mock_manager.rust_src_dir = mock_rust_src
        mock_manager.ingredients_bin = tmp_path / "bin"

        # Create rust_src but not the target/release binaries
        # Mock successful build but file doesn't exist
        mock_run.return_value = Mock(returncode=0)

        loader = BinaryLoader(mock_manager)
        result = loader._build_rust_ingredients(force=True)

        assert result == []


class TestCleanIngredients:
    """Test clean_ingredients method."""

    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_clean_ingredients_dir_not_exist(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test clean when ingredients bin doesn't exist."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        mock_bin = Mock()
        mock_bin.exists.return_value = False
        mock_manager.ingredients_bin = mock_bin

        loader = BinaryLoader(mock_manager)
        result = loader.clean_ingredients()

        assert result == []

    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_clean_ingredients_all(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test cleaning all ingredients."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        # Create some ingredient files
        go_launcher = bin_dir / "flavor-go-launcher"
        rs_builder = bin_dir / "flavor-rs-builder"
        other_file = bin_dir / "other.txt"
        go_launcher.write_text("binary")
        rs_builder.write_text("binary")
        other_file.write_text("text")

        mock_manager.ingredients_bin = bin_dir

        loader = BinaryLoader(mock_manager)
        result = loader.clean_ingredients(language=None)

        assert len(result) == 2
        assert go_launcher in result
        assert rs_builder in result

    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_clean_ingredients_go_only(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test cleaning go ingredients only."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        go_launcher = bin_dir / "flavor-go-launcher"
        go_launcher.write_text("binary")

        mock_manager.ingredients_bin = bin_dir

        loader = BinaryLoader(mock_manager)
        result = loader.clean_ingredients(language="go")

        assert len(result) == 1
        assert go_launcher in result

    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_clean_ingredients_rust_only(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test cleaning rust ingredients only."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        rs_builder = bin_dir / "flavor-rs-builder"
        rs_builder.write_text("binary")

        mock_manager.ingredients_bin = bin_dir

        loader = BinaryLoader(mock_manager)
        result = loader.clean_ingredients(language="rust")

        assert len(result) == 1
        assert rs_builder in result


class TestTestIngredients:
    """Test test_ingredients method."""

    @patch("flavor.ingredients.binary_loader.run")
    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_test_ingredients_all_passed(
        self, mock_get_platform: Mock, mock_run: Mock, tmp_path: Path
    ) -> None:
        """Test testing ingredients when all pass."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()

        # Mock list_ingredients to return test data
        launcher_info = Mock()
        launcher_info.name = "go-launcher"
        launcher_info.language = "go"
        launcher_info.path = tmp_path / "launcher"

        builder_info = Mock()
        builder_info.name = "rs-builder"
        builder_info.language = "rust"
        builder_info.path = tmp_path / "builder"
        mock_manager.list_ingredients.return_value = {
            "launchers": [launcher_info],
            "builders": [builder_info],
        }

        # Mock successful version check
        mock_run.return_value = Mock(returncode=0, stdout="1.0.0")

        loader = BinaryLoader(mock_manager)
        result = loader.test_ingredients()

        assert len(result["passed"]) == 2
        assert len(result["failed"]) == 0
        assert result["passed"][0]["name"] == "go-launcher"
        assert result["passed"][0]["version"] == "1.0.0"

    @patch("flavor.ingredients.binary_loader.run")
    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_test_ingredients_some_failed(
        self, mock_get_platform: Mock, mock_run: Mock, tmp_path: Path
    ) -> None:
        """Test testing ingredients when some fail."""
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

        mock_manager.list_ingredients.return_value = {
            "launchers": [launcher_info],
            "builders": [builder_info],
        }

        # First call succeeds, second fails
        mock_run.side_effect = [
            Mock(returncode=0, stdout="1.0.0"),
            Mock(returncode=1, stderr="error output"),
        ]

        loader = BinaryLoader(mock_manager)
        result = loader.test_ingredients()

        assert len(result["passed"]) == 1
        assert len(result["failed"]) == 1
        assert result["failed"][0]["name"] == "rs-builder"
        assert "Exit code 1" in result["failed"][0]["error"]

    @patch("flavor.ingredients.binary_loader.run")
    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_test_ingredients_exception(
        self, mock_get_platform: Mock, mock_run: Mock, tmp_path: Path
    ) -> None:
        """Test testing ingredients when exception occurs."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()

        launcher_info = Mock()
        launcher_info.name = "go-launcher"
        launcher_info.language = "go"
        launcher_info.path = tmp_path / "launcher"
        mock_manager.list_ingredients.return_value = {"launchers": [launcher_info], "builders": []}

        # Mock exception
        mock_run.side_effect = Exception("Timeout")

        loader = BinaryLoader(mock_manager)
        result = loader.test_ingredients()

        assert len(result["passed"]) == 0
        assert len(result["failed"]) == 1
        assert result["failed"][0]["name"] == "go-launcher"
        assert "Timeout" in result["failed"][0]["error"]

    @patch("flavor.ingredients.binary_loader.run")
    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_test_ingredients_filter_by_language(
        self, mock_get_platform: Mock, mock_run: Mock, tmp_path: Path
    ) -> None:
        """Test testing ingredients filtered by language."""
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
        mock_manager.list_ingredients.return_value = {
            "launchers": [go_launcher],
            "builders": [rs_builder],
        }

        mock_run.return_value = Mock(returncode=0, stdout="1.0.0")

        loader = BinaryLoader(mock_manager)
        result = loader.test_ingredients(language="go")

        assert len(result["passed"]) == 1
        assert result["passed"][0]["name"] == "go-launcher"


class TestHelperMethods:
    """Test helper methods."""

    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_generate_ingredient_names(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test _generate_ingredient_names method."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()

        with patch("flavor.ingredients.binary_loader.Path") as mock_path_class:
            mock_bin_dir = tmp_path / "bin"
            mock_bin_dir.mkdir()

            mock_path_instance = Mock()
            mock_path_instance.parent = tmp_path
            mock_path_instance.parent.__truediv__ = lambda self, x: mock_bin_dir if x == "bin" else Mock()
            mock_path_class.return_value = mock_path_instance

            loader = BinaryLoader(mock_manager)

            with patch.object(loader, "_find_versioned_ingredients", return_value=["v1.0.0"]):
                with patch.object(loader, "_get_package_version_name", return_value="v0.1.0"):
                    result = loader._generate_ingredient_names("test-ingredient")

                    assert "v1.0.0" in result
                    assert "v0.1.0" in result
                    assert "test-ingredient-linux_x86_64" in result
                    assert "test-ingredient" in result

    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_find_versioned_ingredients(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test _find_versioned_ingredients method."""
        mock_get_platform.return_value = "darwin_arm64"
        mock_manager = Mock()
        loader = BinaryLoader(mock_manager)

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        # Create versioned files
        (bin_dir / "test-1.0.0-darwin_arm64").write_text("v1")
        (bin_dir / "test-2.0.0-darwin_arm64").write_text("v2")
        (bin_dir / "test-3.0.0").write_text("v3")

        result = loader._find_versioned_ingredients(bin_dir, "test")

        assert len(result) >= 2
        assert "test-1.0.0-darwin_arm64" in result or "test-2.0.0-darwin_arm64" in result

    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_get_package_version_name_success(self, mock_get_platform: Mock) -> None:
        """Test _get_package_version_name when version is available."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        loader = BinaryLoader(mock_manager)

        with patch("flavor.ingredients.binary_loader.__version__", "1.2.3", create=True):
            result = loader._get_package_version_name("test")
            assert result == "test-1.2.3-linux_x86_64"

    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_get_package_version_name_no_version(self, mock_get_platform: Mock) -> None:
        """Test _get_package_version_name when version not available."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        loader = BinaryLoader(mock_manager)

        # Simulate ImportError
        result = loader._get_package_version_name("test")
        assert result is None

    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_remove_duplicates(self, mock_get_platform: Mock) -> None:
        """Test _remove_duplicates method."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        loader = BinaryLoader(mock_manager)

        names = ["a", "b", "a", "c", "b", "d"]
        result = loader._remove_duplicates(names)

        assert result == ["a", "b", "c", "d"]
        assert len(result) == 4

    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_search_ingredient_locations_embedded(
        self, mock_get_platform: Mock, tmp_path: Path
    ) -> None:
        """Test _search_ingredient_locations finds embedded ingredient."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        mock_manager.ingredients_bin = tmp_path / "dist_bin"

        loader = BinaryLoader(mock_manager)

        embedded_bin = tmp_path / "embedded" / "bin"
        embedded_bin.mkdir(parents=True)
        ingredient_file = embedded_bin / "test-ingredient"
        ingredient_file.write_text("binary")

        with patch("flavor.ingredients.binary_loader.Path") as mock_path_class:
            mock_path_instance = Mock()
            mock_path_instance.parent = tmp_path / "embedded"
            mock_path_instance.parent.__truediv__ = lambda self, x: embedded_bin if x == "bin" else Mock()
            mock_path_class.return_value = mock_path_instance

            result = loader._search_ingredient_locations("test-ingredient")
            assert result == ingredient_file

    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_search_ingredient_locations_local(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test _search_ingredient_locations finds local ingredient."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()

        local_bin = tmp_path / "local_bin"
        local_bin.mkdir()
        ingredient_file = local_bin / "test-ingredient"
        ingredient_file.write_text("binary")

        mock_manager.ingredients_bin = local_bin

        loader = BinaryLoader(mock_manager)

        with patch("flavor.ingredients.binary_loader.Path") as mock_path_class:
            # Mock embedded location to not exist
            mock_path_instance = Mock()
            mock_path_instance.parent = tmp_path / "nonexistent"
            mock_embedded = Mock()
            mock_embedded.exists.return_value = False
            mock_path_instance.parent.__truediv__ = lambda self, x: mock_embedded
            mock_path_class.return_value = mock_path_instance

            result = loader._search_ingredient_locations("test-ingredient")
            assert result == ingredient_file

    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_search_ingredient_locations_not_found(
        self, mock_get_platform: Mock, tmp_path: Path
    ) -> None:
        """Test _search_ingredient_locations returns None when not found."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        mock_manager.ingredients_bin = tmp_path / "nonexistent"

        loader = BinaryLoader(mock_manager)

        with patch("flavor.ingredients.binary_loader.Path") as mock_path_class:
            mock_path_instance = Mock()
            mock_embedded = Mock()
            mock_embedded.exists.return_value = False
            mock_path_instance.parent.__truediv__ = lambda self, x: mock_embedded
            mock_path_class.return_value = mock_path_instance

            result = loader._search_ingredient_locations("nonexistent")
            assert result is None

    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_ensure_executable_not_executable(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test _ensure_executable makes file executable."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        loader = BinaryLoader(mock_manager)

        test_file = tmp_path / "test_binary"
        test_file.write_text("binary")
        test_file.chmod(0o644)  # Not executable

        with patch("flavor.ingredients.binary_loader.os.access", return_value=False):
            loader._ensure_executable(test_file)
            # File should now be executable
            assert test_file.stat().st_mode & 0o111  # Check executable bits

    @patch("flavor.ingredients.binary_loader.get_platform_string")
    def test_ensure_executable_already_executable(
        self, mock_get_platform: Mock, tmp_path: Path
    ) -> None:
        """Test _ensure_executable does nothing if already executable."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        loader = BinaryLoader(mock_manager)

        test_file = tmp_path / "test_binary"
        test_file.write_text("binary")
        test_file.chmod(0o755)  # Already executable

        with patch("flavor.ingredients.binary_loader.os.access", return_value=True):
            # Should not raise exception
            loader._ensure_executable(test_file)


# 🌶️📦🧪🪄
