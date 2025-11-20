#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for flavor.helpers.binary_loader - Build and clean operations."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from flavor.helpers.binary_loader import BinaryLoader


class TestBinaryLoaderInit:
    """Test BinaryLoader initialization."""

    def test_init(self) -> None:
        """Test BinaryLoader initialization."""
        mock_manager = Mock()
        loader = BinaryLoader(mock_manager)
        assert loader.manager is mock_manager

    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_current_platform_property(self, mock_get_platform: Mock) -> None:
        """Test current_platform property."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        loader = BinaryLoader(mock_manager)
        assert loader.current_platform == "linux_x86_64"


class TestGetHelper:
    """Test get_helper method."""

    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_get_helper_found_embedded(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test get_helper finds embedded helper."""
        mock_get_platform.return_value = "darwin_arm64"
        mock_manager = Mock()
        mock_manager.helpers_bin = tmp_path / "dist_bin"

        # Create embedded bin directory
        embedded_bin = tmp_path / "embedded_bin"
        embedded_bin.mkdir()
        helper_file = embedded_bin / "flavor-go-launcher-darwin_arm64"
        helper_file.write_text("binary")
        helper_file.chmod(0o755)

        with patch("flavor.helpers.binary_loader.Path") as mock_path_class:
            # Mock Path(__file__).parent to return our tmp_path
            mock_path_class.__file__ = str(tmp_path / "binary_loader.py")
            mock_path_instance = Mock()
            mock_parent = Mock()
            mock_parent.__truediv__ = lambda self, x: embedded_bin if x == "bin" else Mock()
            mock_path_instance.parent = mock_parent
            mock_path_class.return_value = mock_path_instance

            loader = BinaryLoader(mock_manager)
            # Mock the _search_helper_locations to return our file
            with patch.object(loader, "_search_helper_locations", return_value=helper_file):
                result = loader.get_helper("flavor-go-launcher")
                assert result == helper_file

    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_get_helper_not_found(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test get_helper raises FileNotFoundError when not found."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        mock_manager.helpers_bin = tmp_path / "bin"

        loader = BinaryLoader(mock_manager)
        # Mock _search_helper_locations to return None (not found)
        with (
            patch.object(loader, "_search_helper_locations", return_value=None),
            pytest.raises(FileNotFoundError, match="Helper 'test-helper' not found"),
        ):
            loader.get_helper("test-helper")


class TestBuildHelpers:
    """Test build_helpers methods."""

    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_build_helpers_all(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test building all helpers (go and rust)."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        mock_manager.go_src_dir = tmp_path / "go_src"
        mock_manager.rust_src_dir = tmp_path / "rust_src"
        mock_manager.helpers_bin = tmp_path / "bin"

        loader = BinaryLoader(mock_manager)

        go_binaries = [tmp_path / "go-launcher", tmp_path / "go-builder"]
        rust_binaries = [tmp_path / "rs-launcher", tmp_path / "rs-builder"]

        with (
            patch.object(loader, "_build_go_helpers", return_value=go_binaries),
            patch.object(loader, "_build_rust_helpers", return_value=rust_binaries),
        ):
            result = loader.build_helpers(language=None, force=False)

            assert len(result) == 4
            assert go_binaries[0] in result
            assert rust_binaries[0] in result

    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_build_helpers_go_only(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test building go helpers only."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        loader = BinaryLoader(mock_manager)

        go_binaries = [tmp_path / "go-launcher"]

        with (
            patch.object(loader, "_build_go_helpers", return_value=go_binaries) as mock_go,
            patch.object(loader, "_build_rust_helpers") as mock_rust,
        ):
            result = loader.build_helpers(language="go", force=True)

            mock_go.assert_called_once_with(True)
            mock_rust.assert_not_called()
            assert result == go_binaries

    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_build_helpers_rust_only(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test building rust helpers only."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        loader = BinaryLoader(mock_manager)

        rust_binaries = [tmp_path / "rs-builder"]

        with (
            patch.object(loader, "_build_go_helpers") as mock_go,
            patch.object(loader, "_build_rust_helpers", return_value=rust_binaries) as mock_rust,
        ):
            result = loader.build_helpers(language="rust", force=False)

            mock_go.assert_not_called()
            mock_rust.assert_called_once_with(False)
            assert result == rust_binaries


class TestBuildGoHelpers:
    """Test _build_go_helpers method."""

    @patch("flavor.helpers.binary_loader.ensure_dir")
    @patch("flavor.helpers.binary_loader.run")
    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_build_go_helpers_source_not_found(
        self, mock_get_platform: Mock, mock_run: Mock, mock_ensure_dir: Mock, tmp_path: Path
    ) -> None:
        """Test building go helpers when source directory doesn't exist."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        mock_go_src = Mock()
        mock_go_src.exists.return_value = False
        mock_manager.go_src_dir = mock_go_src

        loader = BinaryLoader(mock_manager)
        result = loader._build_go_helpers(force=False)

        assert result == []
        mock_run.assert_not_called()

    @patch("flavor.helpers.binary_loader.ensure_dir")
    @patch("flavor.helpers.binary_loader.run")
    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_build_go_helpers_already_exists_no_force(
        self, mock_get_platform: Mock, mock_run: Mock, mock_ensure_dir: Mock, tmp_path: Path
    ) -> None:
        """Test building go helpers when binaries exist and force=False."""
        mock_get_platform.return_value = "darwin_arm64"
        mock_manager = Mock()
        mock_go_src = Mock()
        mock_go_src.exists.return_value = True
        mock_manager.go_src_dir = mock_go_src

        # Create existing binaries
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        launcher = bin_dir / "flavor-go-launcher-darwin_arm64"
        builder = bin_dir / "flavor-go-builder-darwin_arm64"
        launcher.write_text("existing")
        builder.write_text("existing")

        # Mock Path operations for the binary paths - create Mock with __truediv__
        mock_bin = Mock()
        mock_bin.__truediv__ = lambda self, x: bin_dir / x
        mock_manager.helpers_bin = mock_bin

        loader = BinaryLoader(mock_manager)
        result = loader._build_go_helpers(force=False)

        # Should return existing binaries without building
        assert len(result) == 2
        mock_run.assert_not_called()

    @patch("flavor.helpers.binary_loader.ensure_dir")
    @patch("flavor.helpers.binary_loader.run")
    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_build_go_helpers_success(
        self, mock_get_platform: Mock, mock_run: Mock, mock_ensure_dir: Mock, tmp_path: Path
    ) -> None:
        """Test successful go helpers build."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        mock_go_src = Mock()
        mock_go_src.exists.return_value = True
        mock_manager.go_src_dir = mock_go_src

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        # Mock successful build
        mock_run.return_value = Mock(returncode=0)

        # Setup Path mocking - create Mock with __truediv__
        def mock_truediv(_path_obj: Path, name: str) -> Path:
            p = bin_dir / name
            # Create the file when accessed
            if not p.exists():
                p.write_text("binary")
            return p

        mock_bin = Mock()
        mock_bin.__truediv__ = mock_truediv
        mock_manager.helpers_bin = mock_bin

        loader = BinaryLoader(mock_manager)
        result = loader._build_go_helpers(force=True)

        assert len(result) == 2
        assert mock_run.call_count == 2

    @patch("flavor.helpers.binary_loader.ensure_dir")
    @patch("flavor.helpers.binary_loader.run")
    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_build_go_helpers_build_failure(
        self, mock_get_platform: Mock, mock_run: Mock, mock_ensure_dir: Mock, tmp_path: Path
    ) -> None:
        """Test go helpers build failure."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        mock_go_src = Mock()
        mock_go_src.exists.return_value = True
        mock_manager.go_src_dir = mock_go_src

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        # Mock failed build
        mock_run.return_value = Mock(returncode=1, stderr="build error")

        # Create Mock with __truediv__
        mock_bin = Mock()
        mock_bin.__truediv__ = lambda self, name: bin_dir / name
        mock_manager.helpers_bin = mock_bin

        loader = BinaryLoader(mock_manager)
        result = loader._build_go_helpers(force=True)

        assert result == []


class TestBuildRustHelpers:
    """Test _build_rust_helpers method."""

    @patch("flavor.helpers.binary_loader.ensure_dir")
    @patch("flavor.helpers.binary_loader.run")
    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_build_rust_helpers_source_not_found(
        self, mock_get_platform: Mock, mock_run: Mock, mock_ensure_dir: Mock, tmp_path: Path
    ) -> None:
        """Test building rust helpers when source directory doesn't exist."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        mock_rust_src = Mock()
        mock_rust_src.exists.return_value = False
        mock_manager.rust_src_dir = mock_rust_src

        loader = BinaryLoader(mock_manager)
        result = loader._build_rust_helpers(force=False)

        assert result == []
        mock_run.assert_not_called()

    @patch("flavor.helpers.binary_loader.ensure_dir")
    @patch("flavor.helpers.binary_loader.safe_copy")
    @patch("flavor.helpers.binary_loader.run")
    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_build_rust_helpers_success(
        self,
        mock_get_platform: Mock,
        mock_run: Mock,
        mock_safe_copy: Mock,
        mock_ensure_dir: Mock,
        tmp_path: Path,
    ) -> None:
        """Test successful rust helpers build."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        mock_rust_src = tmp_path / "rust_src"
        mock_rust_src.mkdir()
        mock_manager.rust_src_dir = mock_rust_src

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        # Create target/release directory
        target_dir = tmp_path / "rust_src" / "target" / "release"
        target_dir.mkdir(parents=True)
        (target_dir / "flavor-rs-launcher").write_text("binary")
        (target_dir / "flavor-rs-builder").write_text("binary")

        # Mock successful build
        mock_run.return_value = Mock(returncode=0)

        # Create Mock with __truediv__
        def mock_truediv(_path_obj: Path, name: str) -> Path:
            p = bin_dir / name
            if not p.exists():
                p.write_text("binary")
            return p

        mock_bin = Mock()
        mock_bin.__truediv__ = mock_truediv
        mock_manager.helpers_bin = mock_bin

        loader = BinaryLoader(mock_manager)
        result = loader._build_rust_helpers(force=True)

        assert len(result) == 2
        assert mock_run.call_count == 2
        assert mock_safe_copy.call_count == 2

    @patch("flavor.helpers.binary_loader.ensure_dir")
    @patch("flavor.helpers.binary_loader.run")
    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_build_rust_helpers_built_but_not_found(
        self, mock_get_platform: Mock, mock_run: Mock, mock_ensure_dir: Mock, tmp_path: Path
    ) -> None:
        """Test rust build succeeds but binary not found in target/release."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        mock_rust_src = tmp_path / "rust_src"
        mock_rust_src.mkdir()
        mock_manager.rust_src_dir = mock_rust_src
        mock_manager.helpers_bin = tmp_path / "bin"

        # Create rust_src but not the target/release binaries
        # Mock successful build but file doesn't exist
        mock_run.return_value = Mock(returncode=0)

        loader = BinaryLoader(mock_manager)
        result = loader._build_rust_helpers(force=True)

        assert result == []


class TestCleanHelpers:
    """Test clean_helpers method."""

    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_clean_helpers_dir_not_exist(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test clean when helpers bin doesn't exist."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        mock_bin = Mock()
        mock_bin.exists.return_value = False
        mock_manager.helpers_bin = mock_bin

        loader = BinaryLoader(mock_manager)
        result = loader.clean_helpers()

        assert result == []

    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_clean_helpers_all(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test cleaning all helpers."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        # Create some helper files
        go_launcher = bin_dir / "flavor-go-launcher"
        rs_builder = bin_dir / "flavor-rs-builder"
        other_file = bin_dir / "other.txt"
        go_launcher.write_text("binary")
        rs_builder.write_text("binary")
        other_file.write_text("text")

        mock_manager.helpers_bin = bin_dir

        loader = BinaryLoader(mock_manager)
        result = loader.clean_helpers(language=None)

        assert len(result) == 2
        assert go_launcher in result
        assert rs_builder in result

    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_clean_helpers_go_only(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test cleaning go helpers only."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        go_launcher = bin_dir / "flavor-go-launcher"
        go_launcher.write_text("binary")

        mock_manager.helpers_bin = bin_dir

        loader = BinaryLoader(mock_manager)
        result = loader.clean_helpers(language="go")

        assert len(result) == 1
        assert go_launcher in result

    @patch("flavor.helpers.binary_loader.get_platform_string")
    def test_clean_helpers_rust_only(self, mock_get_platform: Mock, tmp_path: Path) -> None:
        """Test cleaning rust helpers only."""
        mock_get_platform.return_value = "linux_x86_64"
        mock_manager = Mock()
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        rs_builder = bin_dir / "flavor-rs-builder"
        rs_builder.write_text("binary")

        mock_manager.helpers_bin = bin_dir

        loader = BinaryLoader(mock_manager)
        result = loader.clean_helpers(language="rust")

        assert len(result) == 1
        assert rs_builder in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# 🌶️📦🔚
