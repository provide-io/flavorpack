#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for PythonPackager - Python-specific packaging orchestration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flavor.packaging.python.packager import PythonPackager


class TestArtifactPreparation:
    """Test artifact preparation."""

    def test_prepare_artifacts_delegation(self, tmp_path: Path) -> None:
        """Test prepare_artifacts delegates to slot_builder."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        expected_artifacts = {
            "payload_tgz": work_dir / "payload.tar.gz",
            "metadata_tgz": work_dir / "metadata.tar.gz",
            "uv_binary": work_dir / "uv",
            "python_tgz": work_dir / "python.tar.gz",
        }

        with patch.object(packager.slot_builder, "prepare_artifacts") as mock_prepare:
            mock_prepare.return_value = expected_artifacts

            result = packager.prepare_artifacts(work_dir)

            mock_prepare.assert_called_once_with(work_dir)
            assert result == expected_artifacts

    def test_prepare_artifacts_returns_artifact_dict(self, tmp_path: Path) -> None:
        """Test prepare_artifacts returns dictionary with artifact paths."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        artifact_paths = {
            "payload_tgz": tmp_path / "payload.tar.gz",
            "python_tgz": tmp_path / "python.tar.gz",
        }

        with patch.object(packager.slot_builder, "prepare_artifacts", return_value=artifact_paths):
            result = packager.prepare_artifacts(work_dir)

            assert isinstance(result, dict)
            assert "payload_tgz" in result
            assert isinstance(result["payload_tgz"], Path)


@pytest.mark.unit
class TestCleanup:
    """Test cleanup operations."""

    def test_clean_build_artifacts_all_dirs(self, tmp_path: Path) -> None:
        """Test cleaning all standard build directories."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        # Create directories to clean
        payload_dir = work_dir / "payload"
        payload_dir.mkdir()
        (payload_dir / "test.txt").write_text("test")

        metadata_dir = work_dir / "metadata_content"
        metadata_dir.mkdir()

        venv_dir = work_dir / "venv"
        venv_dir.mkdir()

        build_dir = work_dir / "build"
        build_dir.mkdir()

        with patch("flavor.packaging.python.packager.safe_rmtree") as mock_rmtree:
            packager.clean_build_artifacts(work_dir)

            # Verify safe_rmtree called for each directory
            assert mock_rmtree.call_count == 4
            calls = [call[0][0] for call in mock_rmtree.call_args_list]
            assert payload_dir in calls
            assert metadata_dir in calls
            assert venv_dir in calls
            assert build_dir in calls

    def test_clean_build_artifacts_missing_dirs(self, tmp_path: Path) -> None:
        """Test cleaning handles missing directories gracefully."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        # Don't create any directories

        with patch("flavor.packaging.python.packager.safe_rmtree") as mock_rmtree:
            packager.clean_build_artifacts(work_dir)

            # Should not call safe_rmtree since directories don't exist
            mock_rmtree.assert_not_called()

    def test_clean_build_artifacts_error_handling(self, tmp_path: Path) -> None:
        """Test error handling during cleanup."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        payload_dir = work_dir / "payload"
        payload_dir.mkdir()

        with patch("flavor.packaging.python.packager.safe_rmtree") as mock_rmtree:
            mock_rmtree.side_effect = PermissionError("Cannot remove directory")

            # Should not raise, just log error
            packager.clean_build_artifacts(work_dir)

            assert mock_rmtree.called

    def test_clean_build_artifacts_uses_safe_rmtree(self, tmp_path: Path) -> None:
        """Test that safe_rmtree is used with missing_ok=True."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        payload_dir = work_dir / "payload"
        payload_dir.mkdir()

        with patch("flavor.packaging.python.packager.safe_rmtree") as mock_rmtree:
            packager.clean_build_artifacts(work_dir)

            # Verify safe_rmtree called with missing_ok=True
            for call in mock_rmtree.call_args_list:
                assert call[1]["missing_ok"] is True


@pytest.mark.unit
class TestDelegationMethods:
    """Test delegation helper methods."""

    def test_copy_executable_delegation(self, tmp_path: Path) -> None:
        """Test _copy_executable delegates to env_builder."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        src = tmp_path / "source.exe"
        src.touch()
        dest = tmp_path / "dest.exe"

        with patch.object(packager.env_builder, "_copy_executable") as mock_copy:
            packager._copy_executable(src, dest)

            mock_copy.assert_called_once_with(src, dest)

    def test_download_uv_binary_delegation(self, tmp_path: Path) -> None:
        """Test download_uv_binary delegates to env_builder."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        dest_dir = tmp_path / "uv_dest"
        dest_dir.mkdir()
        uv_binary = dest_dir / "uv"

        with patch.object(packager.env_builder, "download_uv_wheel") as mock_download:
            mock_download.return_value = uv_binary

            result = packager.download_uv_binary(dest_dir)

            mock_download.assert_called_once_with(dest_dir)
            assert result == uv_binary

    def test_write_json_delegation(self, tmp_path: Path) -> None:
        """Test _write_json uses write_json utility."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        packager = PythonPackager(
            manifest_dir=manifest_dir,
            package_name="test-package",
            entry_point="module:main",
        )

        json_path = tmp_path / "data.json"
        data = {"key": "value", "number": 42}

        with patch("flavor.packaging.python.packager.write_json") as mock_write_json:
            packager._write_json(json_path, data)

            mock_write_json.assert_called_once_with(json_path, data, indent=2)


@pytest.mark.unit
class TestRepr:
    """Test string representation."""

    def test_repr_unix_platform(self, tmp_path: Path) -> None:
        """Test __repr__ returns correct string for Unix platform."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        with patch("sys.platform", "linux"):
            packager = PythonPackager(
                manifest_dir=manifest_dir,
                package_name="my-package",
                entry_point="module:main",
                python_version="3.12",
            )

            repr_str = repr(packager)

            assert "PythonPackager" in repr_str
            assert "package=my-package" in repr_str
            assert "python=3.12" in repr_str
            assert "platform=unix" in repr_str

    def test_repr_windows_platform(self, tmp_path: Path) -> None:
        """Test __repr__ returns correct string for Windows platform."""
        manifest_dir = tmp_path / "project"
        manifest_dir.mkdir()

        with patch("sys.platform", "win32"):
            packager = PythonPackager(
                manifest_dir=manifest_dir,
                package_name="win-package",
                entry_point="module:main",
                python_version="3.11",
            )

            repr_str = repr(packager)

            assert "PythonPackager" in repr_str
            assert "package=win-package" in repr_str
            assert "python=3.11" in repr_str
            assert "platform=windows" in repr_str


# 🌶️📦🔚
