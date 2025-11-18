#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for orchestrator_helpers finder functions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from flavor.exceptions import BuildError
from flavor.packaging.orchestrator_helpers import (
    find_builder_executable,
    find_launcher_executable,
)


class TestFindBuilderExecutable:
    """Test find_builder_executable function."""

    def test_with_builder_bin_parameter(self, tmp_path: Path) -> None:
        """Test find_builder_executable with builder_bin parameter."""
        builder_bin = tmp_path / "custom-builder"
        builder_bin.write_text("#!/bin/sh\necho builder")

        result = find_builder_executable(str(builder_bin))

        assert result == builder_bin

    def test_with_builder_bin_not_found(self, tmp_path: Path) -> None:
        """Test find_builder_executable with non-existent builder_bin."""
        builder_bin = tmp_path / "nonexistent-builder"

        with pytest.raises(BuildError, match=r"Builder binary not found: .*nonexistent-builder"):
            find_builder_executable(str(builder_bin))

    @patch.dict("os.environ", {"FLAVOR_BUILDER_BIN": "/tmp/env-builder"})
    def test_with_env_var(self, tmp_path: Path) -> None:
        """Test find_builder_executable with FLAVOR_BUILDER_BIN environment variable."""
        env_builder = Path("/tmp/env-builder")
        env_builder.parent.mkdir(parents=True, exist_ok=True)
        env_builder.write_text("#!/bin/sh\necho builder")

        try:
            result = find_builder_executable(None)
            assert result == env_builder
        finally:
            env_builder.unlink()

    @patch.dict("os.environ", {"FLAVOR_BUILDER_BIN": "/tmp/nonexistent"})
    def test_with_env_var_not_found(self) -> None:
        """Test find_builder_executable with non-existent FLAVOR_BUILDER_BIN."""
        with pytest.raises(BuildError, match=r"Builder binary not found: /tmp/nonexistent"):
            find_builder_executable(None)

    @patch("flavor.helpers.manager.HelperManager")
    def test_rust_builder_found(self, mock_manager_class: Mock) -> None:
        """Test find_builder_executable finds Rust builder."""
        mock_manager = Mock()
        rust_builder = Path("/path/to/flavor-rs-builder")
        mock_manager.get_helper.return_value = rust_builder
        mock_manager_class.return_value = mock_manager

        result = find_builder_executable(None)

        assert result == rust_builder
        mock_manager.get_helper.assert_called_once_with("flavor-rs-builder")

    @patch("flavor.helpers.manager.HelperManager")
    def test_rust_not_found_fallback_to_go(self, mock_manager_class: Mock) -> None:
        """Test find_builder_executable falls back to Go when Rust not found."""
        mock_manager = Mock()
        go_builder = Path("/path/to/flavor-go-builder")

        # First call (Rust) raises FileNotFoundError, second call (Go) succeeds
        mock_manager.get_helper.side_effect = [
            FileNotFoundError("Rust builder not found"),
            go_builder,
        ]
        mock_manager_class.return_value = mock_manager

        result = find_builder_executable(None)

        assert result == go_builder
        assert mock_manager.get_helper.call_count == 2
        mock_manager.get_helper.assert_any_call("flavor-rs-builder")
        mock_manager.get_helper.assert_any_call("flavor-go-builder")

    @patch("flavor.helpers.manager.HelperManager")
    def test_no_builders_found(self, mock_manager_class: Mock) -> None:
        """Test find_builder_executable when no builders are found."""
        mock_manager = Mock()
        mock_manager.helpers_bin = Path("/helpers/bin")
        mock_manager.installed_helpers_bin = Path("/installed/bin")

        # Both Rust and Go raise FileNotFoundError
        mock_manager.get_helper.side_effect = FileNotFoundError("Not found")
        mock_manager_class.return_value = mock_manager

        with pytest.raises(BuildError, match=r"❌ No builder binaries found!"):
            find_builder_executable(None)

        # Verify helpful error message contains suggestions
        try:
            find_builder_executable(None)
        except BuildError as e:
            error_msg = str(e)
            assert "cd helpers && ./build.sh" in error_msg
            assert "make build-helpers" in error_msg
            assert "flavor helpers build" in error_msg
            assert "--builder-bin" in error_msg
            assert "FLAVOR_BUILDER_BIN" in error_msg
            assert "/helpers/bin" in error_msg
            assert "/installed/bin" in error_msg


class TestFindLauncherExecutable:
    """Test find_launcher_executable function."""

    def test_with_launcher_bin_parameter(self, tmp_path: Path) -> None:
        """Test find_launcher_executable with launcher_bin parameter."""
        launcher_bin = tmp_path / "custom-launcher"
        launcher_bin.write_text("#!/bin/sh\necho launcher")

        result = find_launcher_executable(str(launcher_bin))

        assert result == launcher_bin

    def test_with_launcher_bin_not_found(self, tmp_path: Path) -> None:
        """Test find_launcher_executable with non-existent launcher_bin."""
        launcher_bin = tmp_path / "nonexistent-launcher"

        with pytest.raises(BuildError, match=r"Launcher binary not found: .*nonexistent-launcher"):
            find_launcher_executable(str(launcher_bin))

    @patch.dict("os.environ", {"FLAVOR_LAUNCHER_BIN": "/tmp/env-launcher"})
    def test_with_env_var(self, tmp_path: Path) -> None:
        """Test find_launcher_executable with FLAVOR_LAUNCHER_BIN environment variable."""
        env_launcher = Path("/tmp/env-launcher")
        env_launcher.parent.mkdir(parents=True, exist_ok=True)
        env_launcher.write_text("#!/bin/sh\necho launcher")

        try:
            result = find_launcher_executable(None)
            assert result == env_launcher
        finally:
            env_launcher.unlink()

    @patch.dict("os.environ", {"FLAVOR_LAUNCHER_BIN": "/tmp/nonexistent"})
    def test_with_env_var_not_found(self) -> None:
        """Test find_launcher_executable with non-existent FLAVOR_LAUNCHER_BIN."""
        with pytest.raises(BuildError, match=r"Launcher binary from FLAVOR_LAUNCHER_BIN not found"):
            find_launcher_executable(None)

    @patch("flavor.helpers.manager.HelperManager")
    def test_rust_launcher_found(self, mock_manager_class: Mock) -> None:
        """Test find_launcher_executable finds Rust launcher."""
        mock_manager = Mock()
        rust_launcher = Path("/path/to/flavor-rs-launcher")
        mock_manager.get_helper.return_value = rust_launcher
        mock_manager_class.return_value = mock_manager

        result = find_launcher_executable(None)

        assert result == rust_launcher
        mock_manager.get_helper.assert_called_once_with("flavor-rs-launcher")

    @patch("flavor.helpers.manager.HelperManager")
    def test_rust_not_found_fallback_to_go(self, mock_manager_class: Mock) -> None:
        """Test find_launcher_executable falls back to Go when Rust not found."""
        mock_manager = Mock()
        go_launcher = Path("/path/to/flavor-go-launcher")

        # First call (Rust) raises FileNotFoundError, second call (Go) succeeds
        mock_manager.get_helper.side_effect = [
            FileNotFoundError("Rust launcher not found"),
            go_launcher,
        ]
        mock_manager_class.return_value = mock_manager

        result = find_launcher_executable(None)

        assert result == go_launcher
        assert mock_manager.get_helper.call_count == 2
        mock_manager.get_helper.assert_any_call("flavor-rs-launcher")
        mock_manager.get_helper.assert_any_call("flavor-go-launcher")

    @patch("flavor.helpers.manager.HelperManager")
    def test_no_launchers_found(self, mock_manager_class: Mock) -> None:
        """Test find_launcher_executable when no launchers are found."""
        mock_manager = Mock()
        mock_manager.helpers_bin = Path("/helpers/bin")
        mock_manager.installed_helpers_bin = Path("/installed/bin")

        # Both Rust and Go raise FileNotFoundError
        mock_manager.get_helper.side_effect = FileNotFoundError("Not found")
        mock_manager_class.return_value = mock_manager

        with pytest.raises(BuildError, match=r"❌ No launcher binaries found!"):
            find_launcher_executable(None)

        # Verify helpful error message contains suggestions
        try:
            find_launcher_executable(None)
        except BuildError as e:
            error_msg = str(e)
            assert "cd helpers && ./build.sh" in error_msg
            assert "make build-helpers" in error_msg
            assert "flavor helpers build" in error_msg
            assert "--launcher-bin" in error_msg
            assert "FLAVOR_LAUNCHER_BIN" in error_msg
            assert "/helpers/bin" in error_msg
            assert "/installed/bin" in error_msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# 🌶️📦🔚
