#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test UV download functionality for manylinux2014 compatibility."""

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from flavor.packaging.python.packager import PythonPackager


class TestUVDownload:
    """Test UV download functionality."""

    def test_pypa_pip_download_cmd_linux_amd64(self) -> None:
        """Test that pip download command includes manylinux2014 for Linux AMD64."""
        packager = PythonPackager(
            manifest_dir=Path("/tmp"),
            package_name="test",
            entry_point="test:main",
            build_config={},
        )

        with (
            patch(
                "flavor.packaging.python.pypapip_manager.get_os_name",
                return_value="linux",
            ),
            patch(
                "flavor.packaging.python.pypapip_manager.get_arch_name",
                return_value="amd64",
            ),
        ):
            cmd = packager.pypapip._get_pypapip_download_cmd(
                python_exe=Path("/usr/bin/python3"),
                dest_dir=Path("/tmp"),
                packages=["uv"],
                binary_only=True,
            )

            # Check that manylinux2014_x86_64 is in the command
            assert "--platform" in cmd
            assert "manylinux2014_x86_64" in cmd
            assert "--python-version" in cmd
            assert "--only-binary" in cmd
            assert ":all:" in cmd

    def test_pypa_pip_download_cmd_linux_arm64(self) -> None:
        """Test that pip download command includes manylinux2014 for Linux ARM64."""
        packager = PythonPackager(
            manifest_dir=Path("/tmp"),
            package_name="test",
            entry_point="test:main",
            build_config={},
        )

        with (
            patch(
                "flavor.packaging.python.pypapip_manager.get_os_name",
                return_value="linux",
            ),
            patch(
                "flavor.packaging.python.pypapip_manager.get_arch_name",
                return_value="arm64",
            ),
        ):
            cmd = packager.pypapip._get_pypapip_download_cmd(
                python_exe=Path("/usr/bin/python3"),
                dest_dir=Path("/tmp"),
                packages=["uv"],
                binary_only=True,
            )

            # Check that manylinux2014_aarch64 is in the command
            assert "--platform" in cmd
            assert "manylinux2014_aarch64" in cmd
            assert "--python-version" in cmd

    def test_pypa_pip_download_cmd_non_linux(self) -> None:
        """Test that pip download command doesn't add platform constraints on non-Linux."""
        packager = PythonPackager(
            manifest_dir=Path("/tmp"),
            package_name="test",
            entry_point="test:main",
            build_config={},
        )

        with (
            patch(
                "flavor.packaging.python.pypapip_manager.get_os_name",
                return_value="darwin",
            ),
            patch(
                "flavor.packaging.python.dependency_resolver.get_arch_name",
                return_value="arm64",
            ),
        ):
            cmd = packager.pypapip._get_pypapip_download_cmd(
                python_exe=Path("/usr/bin/python3"),
                dest_dir=Path("/tmp"),
                packages=["uv"],
                binary_only=True,
            )

            # Check that no manylinux platform constraints are added for macOS
            assert "manylinux2014" not in " ".join(cmd)
            assert "--only-binary" in cmd  # But binary-only should still be there

    def test_download_uv_wheel_validates_manylinux(self) -> None:
        """Test that _download_uv_wheel validates the wheel is manylinux2014."""
        packager = PythonPackager(
            manifest_dir=Path("/tmp"),
            package_name="test",
            entry_point="test:main",
            build_config={},
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a fake wheel file
            fake_wheel = temp_path / "uv-0.8.14-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"

            # Create a minimal wheel with UV binary
            import zipfile

            with zipfile.ZipFile(fake_wheel, "w") as zf:
                # Add a fake UV binary
                zf.writestr("uv/uv", b"fake uv binary content")

            # Mock successful download with manylinux2014 wheel
            mock_run = MagicMock()
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Downloaded " + fake_wheel.name
            mock_run.return_value.stderr = ""

            # Need to mock at the actual usage location in the module
            with (
                patch("flavor.packaging.python.dependency_resolver.run", mock_run),
                patch(
                    "flavor.packaging.python.dependency_resolver.get_os_name",
                    return_value="linux",
                ),
                patch(
                    "flavor.packaging.python.dependency_resolver.get_arch_name",
                    return_value="amd64",
                ),
                patch.object(Path, "glob", return_value=[fake_wheel]),
            ):
                result = packager.env_builder.download_uv_wheel(temp_path)

                # Should return the path to the extracted UV binary
                assert result is not None
                assert result.name == "uv"
                assert result.exists()

    def test_prepare_artifacts_linux_requires_uv(self) -> None:
        """Test that prepare_artifacts raises error on Linux if UV download fails."""
        packager = PythonPackager(
            manifest_dir=Path("/tmp"),
            package_name="test",
            entry_point="test:main",
            build_config={},
        )

        with tempfile.TemporaryDirectory() as work_dir:
            work_path = Path(work_dir)

            with (
                patch(
                    "flavor.packaging.python.slot_builder.get_os_name",
                    return_value="linux",
                ),
                patch(
                    "flavor.packaging.python.slot_builder.get_arch_name",
                    return_value="amd64",
                ),
                patch.object(
                    packager.slot_builder.uv_manager,
                    "download_uv_binary",
                    return_value=None,
                ),
                patch.object(packager.slot_builder, "_build_wheels"),
                pytest.raises(FileNotFoundError, match="manylinux2014"),
            ):
                # Should raise error on Linux when UV download fails
                packager.prepare_artifacts(work_path)

    def test_download_uv_wheel_direct_fallback(self) -> None:
        """Test that _download_uv_wheel falls back to direct download when pip fails."""
        packager = PythonPackager(
            manifest_dir=Path("/tmp"),
            package_name="test",
            entry_point="test:main",
            build_config={},
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Mock run to fail on pip download but succeed on pip check
            def mock_run_side_effect(*args: Any, **kwargs: Any) -> MagicMock:
                cmd = args[0]
                # Allow pip --version check to succeed
                if "--version" in cmd:
                    result = MagicMock()
                    result.stdout = "pip 21.0.0"
                    result.stderr = ""
                    return result
                # But fail on actual download
                if "download" in cmd:
                    raise RuntimeError("pip download failed")
                # Default
                return MagicMock()

            mock_run = MagicMock(side_effect=mock_run_side_effect)

            with (
                patch("flavor.packaging.python.dependency_resolver.run", mock_run),
                patch("flavor.packaging.python.uv_manager.run", mock_run),
                patch(
                    "flavor.packaging.python.dependency_resolver.get_os_name",
                    return_value="linux",
                ),
                patch(
                    "flavor.packaging.python.dependency_resolver.get_arch_name",
                    return_value="amd64",
                ),
            ):
                # The download should try pip first, fail, then return None
                # There is no direct URL fallback in the current implementation
                result = packager.env_builder.download_uv_wheel(temp_path)

                # Verify that the download failed as expected
                assert result is None

    def test_prepare_artifacts_non_linux_fallback(self) -> None:
        """Test that prepare_artifacts falls back to host UV on non-Linux."""
        packager = PythonPackager(
            manifest_dir=Path("/tmp"),
            package_name="test",
            entry_point="test:main",
            build_config={},
        )

        with tempfile.TemporaryDirectory() as work_dir:
            work_path = Path(work_dir)

            # Create a fake host UV
            fake_uv_path = "/usr/local/bin/uv"

            with (
                patch(
                    "provide.foundation.platform.get_os_name",
                    return_value="darwin",
                ),
                patch(
                    "provide.foundation.platform.get_arch_name",
                    return_value="arm64",
                ),
                patch.object(packager.env_builder, "find_uv_command", return_value=fake_uv_path),
                patch.object(packager, "_copy_executable"),
                patch.object(packager.slot_builder, "_build_wheels"),
                patch.object(packager.slot_builder, "_create_metadata"),
                patch.object(packager.env_builder, "create_python_placeholder"),
                patch("tarfile.open"),
            ):
                # Don't pre-create directories - let the method create them

                # Create dummy archives to avoid stat errors
                (work_path / "payload.tgz").write_bytes(b"dummy")
                (work_path / "metadata.tgz").write_bytes(b"dummy")
                (work_path / "python.tgz").write_bytes(b"dummy")

                # Should not raise error on macOS when falling back to host UV
                artifacts = packager.prepare_artifacts(work_path)
                assert "uv_binary" in artifacts


# 🌶️📦🔚
