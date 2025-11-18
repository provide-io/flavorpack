#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test helpers/manager.py - List and get operations."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from flavor.helpers.manager import HelperInfo, HelperManager


@pytest.mark.unit
class TestListHelpers:
    """Test listing helpers."""

    @patch("flavor.helpers.manager.ensure_dir")
    @patch("flavor.helpers.manager.get_platform_string")
    @patch("flavor.helpers.binary_loader.BinaryLoader")
    def setup_manager(
        self, mock_binary_loader: MagicMock, mock_platform: MagicMock, mock_ensure_dir: MagicMock
    ) -> HelperManager:
        """Create manager instance for testing."""
        mock_platform.return_value = "linux_amd64"
        return HelperManager()

    def test_list_helpers_empty(self) -> None:
        """Test listing helpers when directory is empty."""
        manager = self.setup_manager()
        manager.helpers_bin = Mock(spec=Path)
        manager.helpers_bin.exists.return_value = True
        manager.helpers_bin.iterdir.return_value = []

        # Mock the Path(__file__).parent / "bin" embedded path
        with patch("flavor.helpers.manager.Path") as mock_path_class:
            mock_file_path = Mock(spec=Path)
            mock_parent = Mock(spec=Path)
            mock_embedded_bin = Mock(spec=Path)

            mock_file_path.parent = mock_parent
            mock_parent.__truediv__ = Mock(return_value=mock_embedded_bin)
            mock_embedded_bin.exists.return_value = False

            mock_path_class.return_value = mock_file_path

            helpers = manager.list_helpers()

        assert helpers == {"launchers": [], "builders": []}


class TestGetHelperInfo:
    """Test getting helper information."""

    @patch("flavor.helpers.manager.ensure_dir")
    @patch("flavor.helpers.manager.get_platform_string")
    @patch("flavor.helpers.binary_loader.BinaryLoader")
    def setup_manager(
        self, mock_binary_loader: MagicMock, mock_platform: MagicMock, mock_ensure_dir: MagicMock
    ) -> HelperManager:
        """Create manager instance for testing."""
        mock_platform.return_value = "linux_amd64"
        return HelperManager()

    def test_get_helper_info_success(self) -> None:
        """Test getting helper info successfully."""
        manager = self.setup_manager()

        mock_path = Mock(spec=Path)
        mock_path.name = "flavor-go-launcher"

        manager.helpers_bin = Mock(spec=Path)
        manager.helpers_bin.__truediv__ = Mock(return_value=mock_path)
        mock_path.exists.return_value = True

        expected_info = HelperInfo(
            name="flavor-go-launcher",
            path=mock_path,
            type="launcher",
            language="go",
            size=1024,
        )
        manager._get_helper_info = Mock(return_value=expected_info)

        info = manager.get_helper_info("flavor-go-launcher")
        assert info is not None
        assert info.name == "flavor-go-launcher"

    def test_get_helper_info_partial_name(self) -> None:
        """Test getting helper info by partial name."""
        manager = self.setup_manager()

        # Exact match doesn't exist
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = False
        manager.helpers_bin = Mock(spec=Path)
        manager.helpers_bin.__truediv__ = Mock(return_value=mock_path)

        # But list_helpers finds a match
        mock_helper = HelperInfo(
            name="flavor-go-launcher-linux_amd64",
            path=Path("/path/to/launcher"),
            type="launcher",
            language="go",
            size=1024,
        )
        manager.list_helpers = Mock(
            return_value={
                "launchers": [mock_helper],
                "builders": [],
            }
        )

        info = manager.get_helper_info("launcher")
        assert info is not None
        assert "launcher" in info.name

    def test_get_helper_info_not_found(self) -> None:
        """Test getting helper info when not found."""
        manager = self.setup_manager()

        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = False
        manager.helpers_bin = Mock(spec=Path)
        manager.helpers_bin.__truediv__ = Mock(return_value=mock_path)

        manager.list_helpers = Mock(
            return_value={
                "launchers": [],
                "builders": [],
            }
        )

        info = manager.get_helper_info("nonexistent")
        assert info is None


@pytest.mark.unit
class TestDelegationMethods:
    """Test methods that delegate to BinaryLoader."""

    @patch("flavor.helpers.manager.ensure_dir")
    @patch("flavor.helpers.manager.get_platform_string")
    @patch("flavor.helpers.binary_loader.BinaryLoader")
    def setup_manager(
        self, mock_binary_loader: MagicMock, mock_platform: MagicMock, mock_ensure_dir: MagicMock
    ) -> tuple[HelperManager, MagicMock]:
        """Create manager instance for testing."""
        mock_platform.return_value = "linux_amd64"
        manager = HelperManager()
        return manager, mock_binary_loader

    def test_build_helpers_delegation(self) -> None:
        """Test build_helpers delegates to binary loader."""
        manager, mock_binary_loader = self.setup_manager()
        mock_loader_instance = mock_binary_loader.return_value
        mock_loader_instance.build_helpers.return_value = [Path("/path/to/built")]

        result = manager.build_helpers("go", force=True)

        mock_loader_instance.build_helpers.assert_called_once_with("go", True)
        assert result == [Path("/path/to/built")]

    def test_clean_helpers_delegation(self) -> None:
        """Test clean_helpers delegates to binary loader."""
        manager, mock_binary_loader = self.setup_manager()
        mock_loader_instance = mock_binary_loader.return_value
        mock_loader_instance.clean_helpers.return_value = [Path("/path/to/cleaned")]

        result = manager.clean_helpers("rust")

        mock_loader_instance.clean_helpers.assert_called_once_with("rust")
        assert result == [Path("/path/to/cleaned")]

    def test_test_helpers_delegation(self) -> None:
        """Test test_helpers delegates to binary loader."""
        manager, mock_binary_loader = self.setup_manager()
        mock_loader_instance = mock_binary_loader.return_value
        mock_loader_instance.test_helpers.return_value = {"passed": 5, "failed": 0}

        result = manager.test_helpers("go")

        mock_loader_instance.test_helpers.assert_called_once_with("go")
        assert result == {"passed": 5, "failed": 0}

    def test_get_helper_delegation(self) -> None:
        """Test get_helper delegates to binary loader."""
        manager, mock_binary_loader = self.setup_manager()
        mock_loader_instance = mock_binary_loader.return_value
        mock_loader_instance.get_helper.return_value = Path("/path/to/helper")

        result = manager.get_helper("flavor-go-launcher")

        mock_loader_instance.get_helper.assert_called_once_with("flavor-go-launcher")
        assert result == Path("/path/to/helper")


@pytest.mark.unit
class TestGetHelperInfoHelper:
    """Test _get_helper_info helper method."""

    @patch("flavor.helpers.manager.ensure_dir")
    @patch("flavor.helpers.manager.get_platform_string")
    @patch("flavor.helpers.binary_loader.BinaryLoader")
    def setup_manager(
        self, mock_binary_loader: MagicMock, mock_platform: MagicMock, mock_ensure_dir: MagicMock
    ) -> HelperManager:
        """Create manager instance for testing."""
        mock_platform.return_value = "linux_amd64"
        return HelperManager()

    def test_get_helper_info_complete(self) -> None:
        """Test _get_helper_info with all information."""
        manager = self.setup_manager()

        mock_path = Mock(spec=Path)
        mock_path.name = "flavor-go-launcher-linux_amd64"

        # Mock all helper methods
        manager._parse_helper_identity = Mock(return_value=("launcher", "go"))
        manager._get_file_size = Mock(return_value=12345)
        manager._calculate_checksum = Mock(return_value="abcd1234")
        manager._extract_version = Mock(return_value="1.2.3")
        manager._determine_build_source = Mock(return_value=Path("/src/go"))

        info = manager._get_helper_info(mock_path)

        assert info is not None
        assert info.name == "flavor-go-launcher-linux_amd64"
        assert info.type == "launcher"
        assert info.language == "go"
        assert info.size == 12345
        assert info.checksum == "abcd1234"
        assert info.version == "1.2.3"
        assert info.built_from == Path("/src/go")

    def test_get_helper_info_invalid_identity(self) -> None:
        """Test _get_helper_info with invalid identity."""
        manager = self.setup_manager()

        mock_path = Mock(spec=Path)
        mock_path.name = "random-file.txt"

        manager._parse_helper_identity = Mock(return_value=(None, None))

        info = manager._get_helper_info(mock_path)
        assert info is None

    def test_get_helper_info_no_size(self) -> None:
        """Test _get_helper_info when file size cannot be determined."""
        manager = self.setup_manager()

        mock_path = Mock(spec=Path)
        mock_path.name = "flavor-go-launcher"

        manager._parse_helper_identity = Mock(return_value=("launcher", "go"))
        manager._get_file_size = Mock(return_value=None)

        info = manager._get_helper_info(mock_path)
        assert info is None


# 🌶️📦🔚
