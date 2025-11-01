#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for PythonSlotBuilder artifact preparation."""

from __future__ import annotations

from pathlib import Path
import tarfile
from unittest.mock import Mock, patch

import pytest

from flavor.packaging.python.slot_builder import PythonSlotBuilder


class TestPrepareArtifactsLinux:
    """Test prepare_artifacts on Linux platform."""

    @patch("flavor.packaging.python.slot_builder.get_arch_name")
    @patch("flavor.packaging.python.slot_builder.get_os_name")
    @patch.object(PythonSlotBuilder, "_build_wheels")
    @patch.object(PythonSlotBuilder, "_create_metadata")
    @patch.object(PythonSlotBuilder, "_copy_executable")
    def test_prepare_artifacts_linux_uv_download_success(
        self,
        mock_copy: Mock,
        mock_create_meta: Mock,
        mock_build_wheels: Mock,
        mock_get_os: Mock,
        mock_get_arch: Mock,
        tmp_path: Path,
    ) -> None:
        """Test prepare_artifacts on Linux with successful UV download."""
        mock_get_os.return_value = "linux"
        mock_get_arch.return_value = "x86_64"

        # Setup mock UV manager
        mock_uv_manager = Mock()
        downloaded_uv = tmp_path / "payload" / "bin" / "uv"
        downloaded_uv.parent.mkdir(parents=True, exist_ok=True)
        downloaded_uv.write_text("#!/bin/sh\necho uv")
        mock_uv_manager.download_uv_binary.return_value = downloaded_uv

        # Create builder with mock wheel builder
        mock_wheel_builder = Mock()
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
            wheel_builder=mock_wheel_builder,
        )
        builder.uv_manager = mock_uv_manager

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        # Mock env_builder to avoid actual python placeholder creation
        builder.env_builder.create_python_placeholder = Mock()  # type: ignore[method-assign]

        artifacts = builder.prepare_artifacts(work_dir)

        # Verify UV download was called
        mock_uv_manager.download_uv_binary.assert_called_once()

        # Verify UV was copied to work dir
        mock_copy.assert_called()

        # Verify artifacts structure
        assert "payload_dir" in artifacts
        assert "payload_tgz" in artifacts
        assert "metadata_tgz" in artifacts
        assert "python_tgz" in artifacts
        assert "uv_binary" in artifacts

    @patch("flavor.packaging.python.slot_builder.get_arch_name")
    @patch("flavor.packaging.python.slot_builder.get_os_name")
    @patch.object(PythonSlotBuilder, "_build_wheels")
    def test_prepare_artifacts_linux_uv_download_failure(
        self,
        mock_build_wheels: Mock,
        mock_get_os: Mock,
        mock_get_arch: Mock,
        tmp_path: Path,
    ) -> None:
        """Test prepare_artifacts on Linux with UV download failure."""
        mock_get_os.return_value = "linux"
        mock_get_arch.return_value = "x86_64"

        # Setup mock UV manager that fails download
        mock_uv_manager = Mock()
        mock_uv_manager.download_uv_binary.return_value = None

        # Create builder
        mock_wheel_builder = Mock()
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
            wheel_builder=mock_wheel_builder,
        )
        builder.uv_manager = mock_uv_manager

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        # Should raise FileNotFoundError when UV download fails on Linux
        with pytest.raises(FileNotFoundError, match=r"Failed to download.*compatible UV wheel for Linux"):
            builder.prepare_artifacts(work_dir)

    @patch("flavor.packaging.python.slot_builder.get_arch_name")
    @patch("flavor.packaging.python.slot_builder.get_os_name")
    @patch.object(PythonSlotBuilder, "_build_wheels")
    def test_prepare_artifacts_linux_uv_download_exception(
        self,
        mock_build_wheels: Mock,
        mock_get_os: Mock,
        mock_get_arch: Mock,
        tmp_path: Path,
    ) -> None:
        """Test prepare_artifacts on Linux with UV download exception."""
        mock_get_os.return_value = "linux"
        mock_get_arch.return_value = "x86_64"

        # Setup mock UV manager that raises exception
        mock_uv_manager = Mock()
        mock_uv_manager.download_uv_binary.side_effect = Exception("Download error")

        # Create builder
        mock_wheel_builder = Mock()
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
            wheel_builder=mock_wheel_builder,
        )
        builder.uv_manager = mock_uv_manager

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        # Should raise FileNotFoundError with context
        with pytest.raises(FileNotFoundError, match="Critical error downloading UV for Linux"):
            builder.prepare_artifacts(work_dir)


class TestPrepareArtifactsNonLinux:
    """Test prepare_artifacts on non-Linux platforms (macOS, Windows)."""

    @patch("flavor.packaging.python.slot_builder.get_arch_name")
    @patch("flavor.packaging.python.slot_builder.get_os_name")
    @patch.object(PythonSlotBuilder, "_build_wheels")
    @patch.object(PythonSlotBuilder, "_create_metadata")
    @patch.object(PythonSlotBuilder, "_copy_executable")
    def test_prepare_artifacts_macos_uv_from_host(
        self,
        mock_copy: Mock,
        mock_create_meta: Mock,
        mock_build_wheels: Mock,
        mock_get_os: Mock,
        mock_get_arch: Mock,
        tmp_path: Path,
    ) -> None:
        """Test prepare_artifacts on macOS using host UV."""
        mock_get_os.return_value = "darwin"
        mock_get_arch.return_value = "arm64"

        # Mock env_builder to return host UV path
        host_uv = tmp_path / "host_uv"
        host_uv.write_text("#!/bin/sh\necho uv")

        mock_wheel_builder = Mock()
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
            wheel_builder=mock_wheel_builder,
        )
        builder.env_builder.find_uv_command = Mock(return_value=host_uv)  # type: ignore[method-assign]
        builder.env_builder.create_python_placeholder = Mock()  # type: ignore[method-assign]

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        artifacts = builder.prepare_artifacts(work_dir)

        # Verify UV was copied from host
        builder.env_builder.find_uv_command.assert_called_once_with(raise_if_not_found=False)

        # Verify artifacts were created
        assert "uv_binary" in artifacts

    @patch("flavor.packaging.python.slot_builder.get_arch_name")
    @patch("flavor.packaging.python.slot_builder.get_os_name")
    @patch.object(PythonSlotBuilder, "_build_wheels")
    def test_prepare_artifacts_macos_uv_not_found(
        self,
        mock_build_wheels: Mock,
        mock_get_os: Mock,
        mock_get_arch: Mock,
        tmp_path: Path,
    ) -> None:
        """Test prepare_artifacts on macOS when UV is not found on host."""
        mock_get_os.return_value = "darwin"
        mock_get_arch.return_value = "arm64"

        mock_wheel_builder = Mock()
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
            wheel_builder=mock_wheel_builder,
        )
        builder.env_builder.find_uv_command = Mock(return_value=None)  # type: ignore[method-assign]

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        # Should raise FileNotFoundError when UV is not found
        with pytest.raises(FileNotFoundError, match="UV binary not found on host system"):
            builder.prepare_artifacts(work_dir)

    @patch("flavor.packaging.python.slot_builder.get_arch_name")
    @patch("flavor.packaging.python.slot_builder.get_os_name")
    @patch.object(PythonSlotBuilder, "_build_wheels")
    @patch.object(PythonSlotBuilder, "_create_metadata")
    @patch.object(PythonSlotBuilder, "_copy_executable")
    def test_prepare_artifacts_windows_uv_from_host(
        self,
        mock_copy: Mock,
        mock_create_meta: Mock,
        mock_build_wheels: Mock,
        mock_get_os: Mock,
        mock_get_arch: Mock,
        tmp_path: Path,
    ) -> None:
        """Test prepare_artifacts on Windows using host UV."""
        mock_get_os.return_value = "windows"
        mock_get_arch.return_value = "x86_64"

        # Mock env_builder to return host UV path
        host_uv = tmp_path / "host_uv.exe"
        host_uv.write_text("@echo off\necho uv")

        mock_wheel_builder = Mock()
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
            is_windows=True,
            wheel_builder=mock_wheel_builder,
        )
        builder.env_builder.find_uv_command = Mock(return_value=host_uv)  # type: ignore[method-assign]
        builder.env_builder.create_python_placeholder = Mock()  # type: ignore[method-assign]

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        artifacts = builder.prepare_artifacts(work_dir)

        # Verify UV was copied from host
        builder.env_builder.find_uv_command.assert_called_once_with(raise_if_not_found=False)

        # Verify artifacts were created
        assert "uv_binary" in artifacts
        # On Windows, should use uv.exe
        assert builder.uv_exe == "uv.exe"


class TestPrepareArtifactsArchiveCreation:
    """Test archive creation in prepare_artifacts."""

    @patch("flavor.packaging.python.slot_builder.get_arch_name")
    @patch("flavor.packaging.python.slot_builder.get_os_name")
    @patch.object(PythonSlotBuilder, "_build_wheels")
    @patch.object(PythonSlotBuilder, "_create_metadata")
    @patch.object(PythonSlotBuilder, "_copy_executable")
    def test_prepare_artifacts_creates_payload_archive(
        self,
        mock_copy: Mock,
        mock_create_meta: Mock,
        mock_build_wheels: Mock,
        mock_get_os: Mock,
        mock_get_arch: Mock,
        tmp_path: Path,
    ) -> None:
        """Test that prepare_artifacts creates payload.tgz archive."""
        mock_get_os.return_value = "darwin"
        mock_get_arch.return_value = "arm64"

        # Setup host UV
        host_uv = tmp_path / "host_uv"
        host_uv.write_text("#!/bin/sh\necho uv")

        mock_wheel_builder = Mock()
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
            wheel_builder=mock_wheel_builder,
        )
        builder.env_builder.find_uv_command = Mock(return_value=host_uv)  # type: ignore[method-assign]
        builder.env_builder.create_python_placeholder = Mock()  # type: ignore[method-assign]

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        artifacts = builder.prepare_artifacts(work_dir)

        # Verify payload archive was created
        payload_tgz = artifacts["payload_tgz"]
        assert payload_tgz.exists()
        assert payload_tgz.name == "payload.tgz"

        # Verify it's a valid tar.gz file
        with tarfile.open(payload_tgz, "r:gz") as tar:
            members = tar.getmembers()
            assert len(members) > 0

    @patch("flavor.packaging.python.slot_builder.get_arch_name")
    @patch("flavor.packaging.python.slot_builder.get_os_name")
    @patch.object(PythonSlotBuilder, "_build_wheels")
    @patch.object(PythonSlotBuilder, "_create_metadata")
    @patch.object(PythonSlotBuilder, "_copy_executable")
    def test_prepare_artifacts_creates_metadata_archive(
        self,
        mock_copy: Mock,
        mock_create_meta: Mock,
        mock_build_wheels: Mock,
        mock_get_os: Mock,
        mock_get_arch: Mock,
        tmp_path: Path,
    ) -> None:
        """Test that prepare_artifacts creates metadata.tgz archive."""
        mock_get_os.return_value = "darwin"
        mock_get_arch.return_value = "arm64"

        # Setup host UV
        host_uv = tmp_path / "host_uv"
        host_uv.write_text("#!/bin/sh\necho uv")

        mock_wheel_builder = Mock()
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
            wheel_builder=mock_wheel_builder,
        )
        builder.env_builder.find_uv_command = Mock(return_value=host_uv)  # type: ignore[method-assign]
        builder.env_builder.create_python_placeholder = Mock()  # type: ignore[method-assign]

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        artifacts = builder.prepare_artifacts(work_dir)

        # Verify metadata archive was created
        metadata_tgz = artifacts["metadata_tgz"]
        assert metadata_tgz.exists()
        assert metadata_tgz.name == "metadata.tgz"

        # Verify it's a valid tar.gz file
        with tarfile.open(metadata_tgz, "r:gz") as tar:
            members = tar.getmembers()
            # May be empty, but should be valid
            assert isinstance(members, list)

    @patch("flavor.packaging.python.slot_builder.get_arch_name")
    @patch("flavor.packaging.python.slot_builder.get_os_name")
    @patch.object(PythonSlotBuilder, "_build_wheels")
    @patch.object(PythonSlotBuilder, "_create_metadata")
    @patch.object(PythonSlotBuilder, "_copy_executable")
    def test_prepare_artifacts_creates_python_placeholder(
        self,
        mock_copy: Mock,
        mock_create_meta: Mock,
        mock_build_wheels: Mock,
        mock_get_os: Mock,
        mock_get_arch: Mock,
        tmp_path: Path,
    ) -> None:
        """Test that prepare_artifacts creates python.tgz placeholder."""
        mock_get_os.return_value = "darwin"
        mock_get_arch.return_value = "arm64"

        # Setup host UV
        host_uv = tmp_path / "host_uv"
        host_uv.write_text("#!/bin/sh\necho uv")

        mock_wheel_builder = Mock()
        builder = PythonSlotBuilder(
            manifest_dir=tmp_path,
            package_name="testpkg",
            entry_point="testpkg:main",
            wheel_builder=mock_wheel_builder,
        )
        builder.env_builder.find_uv_command = Mock(return_value=host_uv)  # type: ignore[method-assign]
        builder.env_builder.create_python_placeholder = Mock()  # type: ignore[method-assign]

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        artifacts = builder.prepare_artifacts(work_dir)

        # Verify Python placeholder was created
        python_tgz = artifacts["python_tgz"]
        assert python_tgz == work_dir / "python.tgz"
        builder.env_builder.create_python_placeholder.assert_called_once_with(python_tgz)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# 🌶️📦🔚
