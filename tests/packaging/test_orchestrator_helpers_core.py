#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for orchestrator_helpers core functions."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from flavor.exceptions import BuildError
from flavor.packaging.orchestrator_helpers import (
    create_python_slot_tarballs,
    create_slot_tarballs,
    get_cli_executable_name,
    write_manifest_file,
)


class TestGetCliExecutableName:
    """Test get_cli_executable_name function."""

    def test_with_cli_scripts_unix(self) -> None:
        """Test with CLI scripts on Unix."""
        build_config = {"cli_scripts": {"mytool": "package.cli:main"}}
        result = get_cli_executable_name("mypackage", build_config, windows=False)
        assert result == "mytool"

    def test_with_cli_scripts_windows(self) -> None:
        """Test with CLI scripts on Windows."""
        build_config = {"cli_scripts": {"mytool": "package.cli:main"}}
        result = get_cli_executable_name("mypackage", build_config, windows=True)
        assert result == "mytool.exe"

    def test_with_multiple_cli_scripts_unix(self) -> None:
        """Test with multiple CLI scripts, uses first one on Unix."""
        build_config = {
            "cli_scripts": {
                "first": "package.cli:main",
                "second": "package.cli:other",
            }
        }
        result = get_cli_executable_name("mypackage", build_config, windows=False)
        assert result == "first"

    def test_without_cli_scripts_unix(self) -> None:
        """Test without CLI scripts on Unix."""
        build_config: dict[str, Any] = {}
        result = get_cli_executable_name("mypackage", build_config, windows=False)
        assert result == "mypackage"

    def test_without_cli_scripts_windows(self) -> None:
        """Test without CLI scripts on Windows."""
        build_config: dict[str, Any] = {}
        result = get_cli_executable_name("mypackage", build_config, windows=True)
        assert result == "mypackage.exe"

    def test_with_empty_cli_scripts(self) -> None:
        """Test with empty CLI scripts dict."""
        build_config: dict[str, Any] = {"cli_scripts": {}}
        result = get_cli_executable_name("mypackage", build_config, windows=False)
        assert result == "mypackage"


class TestCreateSlotTarballs:
    """Test create_slot_tarballs function."""

    @patch("flavor.packaging.orchestrator_helpers.is_windows")
    def test_create_slot_tarballs_unix(self, mock_is_windows: Mock, tmp_path: Path) -> None:
        """Test creating slot tarballs on Unix."""
        mock_is_windows.return_value = False

        # Create mock artifacts
        payload_dir = tmp_path / "payload"
        payload_dir.mkdir()
        bin_dir = payload_dir / "bin"
        bin_dir.mkdir()
        uv_binary = bin_dir / "uv"
        uv_binary.write_text("#!/bin/sh\necho uv")

        wheels_dir = payload_dir / "wheels"
        wheels_dir.mkdir()
        wheel1 = wheels_dir / "package1-1.0.0-py3-none-any.whl"
        wheel1.write_text("fake wheel")

        python_tgz = tmp_path / "python.tgz"
        python_tgz.write_text("fake python tarball")

        artifacts = {
            "payload_dir": payload_dir,
            "python_tgz": python_tgz,
        }

        slots = create_slot_tarballs(tmp_path, artifacts)

        assert "uv" in slots
        assert "python" in slots
        assert "wheels" in slots
        assert slots["uv"] == uv_binary
        assert slots["python"] == python_tgz
        assert slots["wheels"].exists()
        assert slots["wheels"].name == "wheels.tar"

    @patch("flavor.packaging.orchestrator_helpers.is_windows")
    def test_create_slot_tarballs_windows(self, mock_is_windows: Mock, tmp_path: Path) -> None:
        """Test creating slot tarballs on Windows."""
        mock_is_windows.return_value = True

        # Create mock artifacts
        payload_dir = tmp_path / "payload"
        payload_dir.mkdir()
        bin_dir = payload_dir / "bin"
        bin_dir.mkdir()
        uv_binary = bin_dir / "uv.exe"
        uv_binary.write_text("@echo off\necho uv")

        wheels_dir = payload_dir / "wheels"
        wheels_dir.mkdir()

        python_tgz = tmp_path / "python.tgz"
        python_tgz.write_text("fake python tarball")

        artifacts = {
            "payload_dir": payload_dir,
            "python_tgz": python_tgz,
        }

        slots = create_slot_tarballs(tmp_path, artifacts)

        assert slots["uv"] == uv_binary
        assert slots["uv"].name == "uv.exe"

    @patch("flavor.packaging.orchestrator_helpers.is_windows")
    def test_create_slot_tarballs_missing_python(self, mock_is_windows: Mock, tmp_path: Path) -> None:
        """Test creating slot tarballs with missing Python tarball."""
        mock_is_windows.return_value = False

        payload_dir = tmp_path / "payload"
        payload_dir.mkdir()
        bin_dir = payload_dir / "bin"
        bin_dir.mkdir()
        uv_binary = bin_dir / "uv"
        uv_binary.write_text("#!/bin/sh\necho uv")

        wheels_dir = payload_dir / "wheels"
        wheels_dir.mkdir()

        artifacts = {
            "payload_dir": payload_dir,
            # Missing python_tgz
        }

        with pytest.raises(BuildError, match="Python runtime tarball not found"):
            create_slot_tarballs(tmp_path, artifacts)

    @patch("flavor.packaging.orchestrator_helpers.is_windows")
    def test_create_slot_tarballs_with_multiple_wheels(self, mock_is_windows: Mock, tmp_path: Path) -> None:
        """Test creating slot tarballs with multiple wheels."""
        mock_is_windows.return_value = False

        payload_dir = tmp_path / "payload"
        payload_dir.mkdir()
        bin_dir = payload_dir / "bin"
        bin_dir.mkdir()
        uv_binary = bin_dir / "uv"
        uv_binary.write_text("#!/bin/sh\necho uv")

        wheels_dir = payload_dir / "wheels"
        wheels_dir.mkdir()
        wheel1 = wheels_dir / "package1-1.0.0-py3-none-any.whl"
        wheel1.write_text("fake wheel 1")
        wheel2 = wheels_dir / "package2-2.0.0-py3-none-any.whl"
        wheel2.write_text("fake wheel 2")

        python_tgz = tmp_path / "python.tgz"
        python_tgz.write_text("fake python tarball")

        artifacts = {
            "payload_dir": payload_dir,
            "python_tgz": python_tgz,
        }

        slots = create_slot_tarballs(tmp_path, artifacts)

        # Verify wheels tarball was created
        assert slots["wheels"].exists()
        import tarfile

        with tarfile.open(slots["wheels"], "r") as tar:
            members = tar.getmembers()
            assert len(members) == 2
            names = [m.name for m in members]
            assert "wheels/package1-1.0.0-py3-none-any.whl" in names
            assert "wheels/package2-2.0.0-py3-none-any.whl" in names


class TestWriteManifestFile:
    """Test write_manifest_file function."""

    @patch("flavor.packaging.orchestrator_helpers.write_json")
    def test_write_manifest_file(self, mock_write_json: Mock, tmp_path: Path) -> None:
        """Test writing manifest file."""
        manifest = {
            "name": "test-package",
            "version": "1.0.0",
            "command": "{workenv}/bin/test-package",
        }

        result = write_manifest_file(manifest, tmp_path)

        assert result == tmp_path / "manifest.json"
        mock_write_json.assert_called_once_with(
            tmp_path / "manifest.json",
            manifest,
            indent=2,
        )


class TestCreatePythonSlotTarballs:
    """Test create_python_slot_tarballs function."""

    @patch("flavor.packaging.orchestrator_helpers.is_windows")
    def test_create_python_slot_tarballs_unix(self, mock_is_windows: Mock, tmp_path: Path) -> None:
        """Test creating Python slot tarballs on Unix."""
        mock_is_windows.return_value = False

        payload_dir = tmp_path / "payload"
        payload_dir.mkdir()
        bin_dir = payload_dir / "bin"
        bin_dir.mkdir()
        uv_binary = bin_dir / "uv"
        uv_binary.write_text("#!/bin/sh\necho uv")

        wheels_dir = payload_dir / "wheels"
        wheels_dir.mkdir()
        wheel1 = wheels_dir / "package1-1.0.0-py3-none-any.whl"
        wheel1.write_text("fake wheel")

        python_tgz = tmp_path / "python.tgz"
        python_tgz.write_text("fake python tarball")

        artifacts = {
            "payload_dir": payload_dir,
            "python_tgz": python_tgz,
        }

        uv_path, python_tarball, wheels_tarball = create_python_slot_tarballs(tmp_path, artifacts)

        assert uv_path == uv_binary
        assert python_tarball == python_tgz
        assert wheels_tarball.exists()
        assert wheels_tarball.name == "wheels.tar"

    @patch("flavor.packaging.orchestrator_helpers.is_windows")
    def test_create_python_slot_tarballs_windows(self, mock_is_windows: Mock, tmp_path: Path) -> None:
        """Test creating Python slot tarballs on Windows."""
        mock_is_windows.return_value = True

        payload_dir = tmp_path / "payload"
        payload_dir.mkdir()
        bin_dir = payload_dir / "bin"
        bin_dir.mkdir()
        uv_binary = bin_dir / "uv.exe"
        uv_binary.write_text("@echo off\necho uv")

        wheels_dir = payload_dir / "wheels"
        wheels_dir.mkdir()

        python_tgz = tmp_path / "python.tgz"
        python_tgz.write_text("fake python tarball")

        artifacts = {
            "payload_dir": payload_dir,
            "python_tgz": python_tgz,
        }

        uv_path, _python_tarball, _wheels_tarball = create_python_slot_tarballs(tmp_path, artifacts)

        assert uv_path.name == "uv.exe"

    @patch("flavor.packaging.orchestrator_helpers.is_windows")
    def test_create_python_slot_tarballs_missing_python(self, mock_is_windows: Mock, tmp_path: Path) -> None:
        """Test creating Python slot tarballs with missing Python."""
        mock_is_windows.return_value = False

        payload_dir = tmp_path / "payload"
        payload_dir.mkdir()
        bin_dir = payload_dir / "bin"
        bin_dir.mkdir()
        uv_binary = bin_dir / "uv"
        uv_binary.write_text("#!/bin/sh\necho uv")

        wheels_dir = payload_dir / "wheels"
        wheels_dir.mkdir()

        artifacts = {
            "payload_dir": payload_dir,
            # Missing python_tgz
        }

        with pytest.raises(BuildError, match="Python runtime tarball not found"):
            create_python_slot_tarballs(tmp_path, artifacts)

    @patch("flavor.packaging.orchestrator_helpers.is_windows")
    def test_create_python_slot_tarballs_with_wheels(self, mock_is_windows: Mock, tmp_path: Path) -> None:
        """Test creating Python slot tarballs with actual wheels."""
        mock_is_windows.return_value = False

        payload_dir = tmp_path / "payload"
        payload_dir.mkdir()
        bin_dir = payload_dir / "bin"
        bin_dir.mkdir()
        uv_binary = bin_dir / "uv"
        uv_binary.write_text("#!/bin/sh\necho uv")

        wheels_dir = payload_dir / "wheels"
        wheels_dir.mkdir()
        wheel1 = wheels_dir / "package1-1.0.0-py3-none-any.whl"
        wheel1.write_text("fake wheel content")

        python_tgz = tmp_path / "python.tgz"
        python_tgz.write_text("fake python tarball")

        artifacts = {
            "payload_dir": payload_dir,
            "python_tgz": python_tgz,
        }

        _uv_path, _python_tarball, wheels_tarball = create_python_slot_tarballs(tmp_path, artifacts)

        # Verify wheels were added to tarball
        import tarfile

        with tarfile.open(wheels_tarball, "r") as tar:
            members = tar.getmembers()
            assert len(members) == 1
            assert members[0].name == "wheels/package1-1.0.0-py3-none-any.whl"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# 🌶️📦🔚
