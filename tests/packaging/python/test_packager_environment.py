#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for PythonPackager - Python-specific packaging orchestration."""

from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import patch

import pytest

from flavor.packaging.python.packager import PythonPackager


class TestBuildEnvironment:
    """Test build environment creation."""

    def test_create_build_environment_with_uv(self, tmp_path: Path) -> None:
        """Test creating build environment using UV."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        build_dir = tmp_path / "build"
        build_dir.mkdir()
        venv_dir = build_dir / "venv"
        venv_bin = venv_dir / packager.venv_bin_dir
        venv_bin.mkdir(parents=True)
        python_exe = venv_bin / ("python.exe" if packager.is_windows else "python")
        python_exe.touch()

        # Mock UV being available
        with (
            patch.object(packager.env_builder, "find_uv_command") as mock_find_uv,
            patch.object(packager.uv, "create_venv") as mock_create_venv,
            patch.object(packager.pypapip, "_get_pypapip_install_cmd") as mock_get_cmd,
            patch("provide.foundation.process.run") as mock_run,
        ):
            mock_find_uv.return_value = "/usr/bin/uv"
            mock_get_cmd.return_value = ["pip", "install", "pip", "wheel", "setuptools"]

            result = packager.create_build_environment(build_dir)

            # Verify UV was used
            mock_find_uv.assert_called_once()
            mock_create_venv.assert_called_once_with(venv_dir, "3.11")

            # Verify pip/wheel installed
            assert mock_get_cmd.called
            assert mock_run.called

            assert result == python_exe

    def test_create_build_environment_fallback_venv(self, tmp_path: Path) -> None:
        """Test fallback to standard venv when UV is not available."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        build_dir = tmp_path / "build"
        build_dir.mkdir()
        venv_dir = build_dir / "venv"
        venv_bin = venv_dir / packager.venv_bin_dir
        venv_bin.mkdir(parents=True)
        python_exe = venv_bin / ("python.exe" if packager.is_windows else "python")
        python_exe.touch()

        # Mock UV not being available
        with (
            patch.object(packager.env_builder, "find_uv_command") as mock_find_uv,
            patch("venv.create") as mock_venv_create,
            patch.object(packager.pypapip, "_get_pypapip_install_cmd") as mock_get_cmd,
            patch("provide.foundation.process.run") as mock_run,
        ):
            mock_find_uv.return_value = None
            mock_get_cmd.return_value = ["pip", "install", "pip", "wheel", "setuptools"]

            result = packager.create_build_environment(build_dir)

            # Verify standard venv was used
            mock_venv_create.assert_called_once_with(venv_dir, with_pip=True)

            # Verify pip/wheel installed
            assert mock_get_cmd.called
            assert mock_run.called

            assert result == python_exe

    def test_create_build_environment_pip_installation(self, tmp_path: Path) -> None:
        """Test pip and wheel installation in build environment."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        build_dir = tmp_path / "build"
        build_dir.mkdir()
        venv_dir = build_dir / "venv"
        venv_bin = venv_dir / packager.venv_bin_dir
        venv_bin.mkdir(parents=True)
        python_exe = venv_bin / ("python.exe" if packager.is_windows else "python")
        python_exe.touch()

        with (
            patch.object(packager.env_builder, "find_uv_command", return_value=None),
            patch("venv.create"),
            patch.object(packager.pypapip, "_get_pypapip_install_cmd") as mock_get_cmd,
            patch("provide.foundation.process.run") as mock_run,
        ):
            install_cmd = ["python", "-m", "pip", "install", "pip", "wheel", "setuptools"]
            mock_get_cmd.return_value = install_cmd

            packager.create_build_environment(build_dir)

            # Verify pip install command was called correctly
            mock_get_cmd.assert_called_once_with(python_exe, ["pip", "wheel", "setuptools"])
            mock_run.assert_called_once_with(install_cmd, check=True, capture_output=True)

    def test_create_build_environment_python_not_found(self, tmp_path: Path) -> None:
        """Test when python executable is not found in venv."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        build_dir = tmp_path / "build"
        build_dir.mkdir()

        # Don't create the python executable

        with (
            patch.object(packager.env_builder, "find_uv_command", return_value=None),
            patch("venv.create"),
            patch("provide.foundation.process.run") as mock_run,
        ):
            # Python exe doesn't exist, so pip install should be skipped
            result = packager.create_build_environment(build_dir)

            # run should not be called since python_exe doesn't exist
            mock_run.assert_not_called()

            # Still returns the expected path (even if it doesn't exist)
            expected_python = (
                build_dir
                / "venv"
                / packager.venv_bin_dir
                / ("python.exe" if packager.is_windows else "python")
            )
            assert result == expected_python


@pytest.mark.unit
class TestGetPythonBinaryInfo:
    """Test Python binary information retrieval."""

    def test_get_python_binary_info_uv_found(self, tmp_path: Path) -> None:
        """Test when UV is found and available."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
            python_version="3.12",
        )

        with patch.object(packager.env_builder, "find_uv_command") as mock_find_uv:
            mock_find_uv.return_value = "/usr/bin/uv"

            info = packager.get_python_binary_info()

            assert info["version"] == "3.12"
            assert info["path"] is None  # UV handles Python
            assert info["is_system"] is False
            assert info["manager"] == "uv"

    def test_get_python_binary_info_uv_exception(self, tmp_path: Path) -> None:
        """Test fallback when UV raises exception."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
            python_version="3.11",
        )

        with patch.object(packager.env_builder, "find_uv_command") as mock_find_uv:
            mock_find_uv.side_effect = RuntimeError("UV not found")

            info = packager.get_python_binary_info()

            # Should fall back to system Python
            assert info["version"] == "3.11"
            assert info["path"] == sys.executable
            assert info["is_system"] is True
            assert info["manager"] == "system"

    def test_get_python_binary_info_system_fallback(self, tmp_path: Path) -> None:
        """Test system Python fallback when UV not available."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
            python_version="3.10",
        )

        with patch.object(packager.env_builder, "find_uv_command") as mock_find_uv:
            mock_find_uv.return_value = None  # UV not found

            info = packager.get_python_binary_info()

            assert info["version"] == "3.10"
            assert info["path"] == sys.executable
            assert info["is_system"] is True
            assert info["manager"] == "system"


# 🌶️📦🔚
