#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for WheelBuilder - critical features."""

import importlib.metadata
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

import pytest

import flavor.packaging.python.pypapip_manager as _pip_mod
from flavor.packaging.python.wheel_builder import WheelBuilder


class TestWheelBuilderCriticalFeatures:
    """Test CRITICAL features that must never be broken."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.wheel_builder = WheelBuilder()

    def test_uses_pypapip_for_wheel_building(self) -> None:
        """CRITICAL: Must use PyPA pip for wheel building, not UV."""
        # Verify PyPA pip manager is available
        assert hasattr(self.wheel_builder, "pypapip")
        assert hasattr(self.wheel_builder.pypapip, "_get_pypapip_wheel_cmd")

        # Verify UV is available but separate
        assert hasattr(self.wheel_builder, "uv")

        # Verify no direct UV wheel building methods
        assert not hasattr(self.wheel_builder, "_get_uv_wheel_cmd")

    def test_always_uses_pypapip_for_wheel_downloads(self) -> None:
        """CRITICAL: Must always use PyPA pip for wheel downloads (manylinux compatibility)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            wheel_dir = Path(temp_dir)
            requirements_file = Path(temp_dir) / "requirements.txt"
            requirements_file.write_text("requests==2.28.0\n")

            python_exe = Path("/usr/bin/python3")

            def mock_download_side_effect(python_exe: Path, requirements_file: Path, wheel_dir: Path) -> None:
                # Create fake wheel files to simulate successful download
                fake_wheel = wheel_dir / "requests-2.28.0-py3-none-any.whl"
                fake_wheel.write_bytes(b"fake wheel content")

            with patch(
                "flavor.packaging.python.pypapip_manager.PyPaPipManager.download_wheels_from_requirements",
                side_effect=mock_download_side_effect,
            ) as mock_download:
                # Even with use_uv_for_download=True, should still use PyPA pip
                result = self.wheel_builder.download_wheels_for_resolved_deps(
                    python_exe,
                    requirements_file,
                    wheel_dir,
                    use_uv_for_download=True,  # This should be ignored
                )

                # Verify PyPA pip was used
                mock_download.assert_called_once_with(python_exe, requirements_file, wheel_dir)

                # Verify wheel files were returned
                assert len(result) == 1
                assert result[0].name == "requests-2.28.0-py3-none-any.whl"

    def test_dependency_resolution_has_uv_fallback(self) -> None:
        """CRITICAL: Dependency resolution must have UV + pip-tools fallback chain."""
        python_exe = Path("/usr/bin/python3")
        packages = ["requests"]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Verify UV is tried first
            with patch.object(self.wheel_builder.uv, "compile_requirements") as mock_uv:
                mock_uv.return_value = output_dir / "requirements.txt"

                self.wheel_builder.resolve_dependencies(
                    python_exe,
                    packages=packages,
                    output_dir=output_dir,
                    use_uv_for_resolution=True,
                )

                mock_uv.assert_called_once()

    def test_build_isolation_configurable(self) -> None:
        """CRITICAL: Build isolation must be configurable for complex packages."""
        from flavor.packaging.python.wheel_builder import _PINNED_BUILD_BACKENDS

        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "package"
            source_path.mkdir()
            wheel_dir = Path(temp_dir) / "wheels"
            wheel_dir.mkdir()

            # Create mock wheel
            wheel_file = wheel_dir / "package-1.0.0-py3-none-any.whl"
            wheel_file.touch()

            python_exe = Path("/usr/bin/python3")

            with patch("flavor.packaging.python.wheel_builder.importlib_metadata") as mock_meta:
                mock_meta.version.side_effect = lambda pkg: _PINNED_BUILD_BACKENDS[pkg]
                with patch("flavor.packaging.python.wheel_builder.run") as mock_run:
                    mock_result = Mock(returncode=0, stdout="Built wheel")
                    mock_run.side_effect = [mock_result, mock_result, mock_result]

                    # Test with isolation disabled
                    self.wheel_builder.build_wheel_from_source(
                        python_exe, source_path, wheel_dir, use_isolation=False
                    )

                    args = mock_run.call_args_list[-1][0]
                    cmd = args[0]
                    assert "--no-build-isolation" in cmd

    @patch("flavor.packaging.python.wheel_builder.run")
    def test_build_wheel_bootstraps_pip_with_ensurepip(self, mock_run: Mock) -> None:
        """Test wheel building bootstraps pip when the target Python lacks it."""
        pip_missing = RuntimeError("pip missing")
        success = Mock(returncode=0, stdout="ok")
        mock_run.side_effect = [pip_missing, success, success]

        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "mypackage"
            source_path.mkdir()
            wheel_dir = Path(temp_dir) / "wheels"
            wheel_dir.mkdir()
            wheel_file = wheel_dir / "mypackage-1.0.0-py3-none-any.whl"
            wheel_file.touch()

            python_exe = Path("/usr/bin/python3")
            with patch.object(_pip_mod.sys, "platform", "linux"):
                result = self.wheel_builder.build_wheel_from_source(python_exe, source_path, wheel_dir)

            assert result == wheel_file
            assert mock_run.call_args_list[0][0][0] == ["/usr/bin/python3", "-m", "pip", "--version"]
            assert mock_run.call_args_list[1][0][0] == ["/usr/bin/python3", "-m", "ensurepip", "--default-pip"]
            assert mock_run.call_args_list[2][0][0][0:4] == ["/usr/bin/python3", "-m", "pip", "wheel"]

    @patch("flavor.packaging.python.wheel_builder.run")
    def test_build_wheel_bootstraps_pip_with_uv_fallback(self, mock_run: Mock) -> None:
        """Test wheel building falls back to UV when ensurepip is unavailable."""
        pip_missing = RuntimeError("pip missing")
        ensurepip_missing = RuntimeError("ensurepip missing")
        success = Mock(returncode=0, stdout="ok")
        mock_run.side_effect = [pip_missing, ensurepip_missing, success, success]

        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "mypackage"
            source_path.mkdir()
            wheel_dir = Path(temp_dir) / "wheels"
            wheel_dir.mkdir()
            wheel_file = wheel_dir / "mypackage-1.0.0-py3-none-any.whl"
            wheel_file.touch()

            python_exe = Path("/usr/bin/python3")
            with patch.object(
                self.wheel_builder.uv,
                "_get_uv_pip_install_cmd",
                return_value=["uv", "pip", "install", "--python", "/usr/bin/python3", "pip"],
            ) as mock_uv_install_cmd:
                result = self.wheel_builder.build_wheel_from_source(python_exe, source_path, wheel_dir)

            assert result == wheel_file
            mock_uv_install_cmd.assert_called_once_with(python_exe, ["pip"])
            assert mock_run.call_args_list[2][0][0] == [
                "uv",
                "pip",
                "install",
                "--python",
                "/usr/bin/python3",
                "pip",
            ]

    def test_ensure_backend_raises_on_version_mismatch(self) -> None:
        """CRITICAL: version mismatch must raise RuntimeError — never install."""
        python_exe = Path("/usr/bin/python3")

        with patch("flavor.packaging.python.wheel_builder.importlib_metadata") as mock_meta:
            mock_meta.version.side_effect = lambda pkg: (
                "99.0.0" if pkg == "setuptools" else "99.0.0"
            )
            with pytest.raises(RuntimeError, match="Build backend mismatch"):
                self.wheel_builder._ensure_no_isolation_build_backend(python_exe)

    def test_ensure_backend_passes_on_correct_versions(self) -> None:
        """CRITICAL: correct versions must pass silently with no subprocess calls."""
        from flavor.packaging.python.wheel_builder import _PINNED_BUILD_BACKENDS
        python_exe = Path("/usr/bin/python3")

        with patch("flavor.packaging.python.wheel_builder.importlib_metadata") as mock_meta:
            mock_meta.version.side_effect = lambda pkg: _PINNED_BUILD_BACKENDS[pkg]
            with patch("flavor.packaging.python.wheel_builder.run") as mock_run:
                self.wheel_builder._ensure_no_isolation_build_backend(python_exe)
                mock_run.assert_not_called()

    def test_ensure_backend_raises_when_package_not_installed(self) -> None:
        """CRITICAL: missing package must raise RuntimeError — never install."""
        python_exe = Path("/usr/bin/python3")

        with patch("flavor.packaging.python.wheel_builder.importlib_metadata") as mock_meta:
            mock_meta.version.side_effect = importlib.metadata.PackageNotFoundError("setuptools")
            mock_meta.PackageNotFoundError = importlib.metadata.PackageNotFoundError
            with pytest.raises(RuntimeError, match="Build backend not found"):
                self.wheel_builder._ensure_no_isolation_build_backend(python_exe)

    def test_manager_separation_maintained(self) -> None:
        """CRITICAL: PyPA pip and UV managers must remain separate and distinct."""
        # Verify both managers are separate instances
        assert self.wheel_builder.pypapip is not self.wheel_builder.uv

        # Verify they have different capabilities
        assert hasattr(self.wheel_builder.pypapip, "_get_pypapip_download_cmd")
        assert hasattr(self.wheel_builder.uv, "_get_uv_venv_cmd")

        # Verify no cross-contamination of methods
        assert not hasattr(self.wheel_builder.pypapip, "_get_uv_venv_cmd")
        assert not hasattr(self.wheel_builder.uv, "_get_pypapip_download_cmd")


# 🌶️📦🔚
