#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for flavor.helpers.binary_loader - Test and helper methods."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

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




# 🌶️📦🔚
