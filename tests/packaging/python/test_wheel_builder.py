#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for WheelBuilder dependency resolution functionality."""

from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

import pytest

import flavor.packaging.python.pypapip_manager as _pip_mod
from flavor.packaging.python.wheel_builder import WheelBuilder


class TestWheelBuilder:
    """Test WheelBuilder functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.wheel_builder = WheelBuilder(python_version="3.11")

    def test_initialization(self) -> None:
        """Test WheelBuilder initialization."""
        assert self.wheel_builder.python_version == "3.11"
        assert hasattr(self.wheel_builder, "pypapip")
        assert hasattr(self.wheel_builder, "uv")

        # Test custom Python version
        builder_312 = WheelBuilder(python_version="3.12")
        assert builder_312.python_version == "3.12"

    @patch("flavor.packaging.python.wheel_builder.run")
    def test_build_wheel_from_source_basic(self, mock_run: Mock) -> None:
        """Test basic wheel building from source."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Built wheel: mypackage-1.0.0-py3-none-any.whl"
        mock_run.side_effect = [mock_result, mock_result]

        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "mypackage"
            source_path.mkdir()
            wheel_dir = Path(temp_dir) / "wheels"
            wheel_dir.mkdir()

            # Create a mock wheel file
            wheel_file = wheel_dir / "mypackage-1.0.0-py3-none-any.whl"
            wheel_file.touch()

            python_exe = Path("/usr/bin/python3")

            with patch.object(_pip_mod.sys, "platform", "linux"):
                result = self.wheel_builder.build_wheel_from_source(python_exe, source_path, wheel_dir)

            # Verify the wheel build command was issued after the pip availability check
            assert mock_run.call_count == 2
            args, kwargs = mock_run.call_args_list[-1]

            cmd = args[0]
            assert cmd[0] == "/usr/bin/python3"
            assert cmd[1:4] == ["-m", "pip", "wheel"]
            assert "--wheel-dir" in cmd
            assert wheel_dir.as_posix() in cmd
            assert "--no-deps" in cmd
            assert source_path.as_posix() in cmd

            # Verify result
            assert result.name == "mypackage-1.0.0-py3-none-any.whl"
            assert kwargs["check"] is True

    @patch("flavor.packaging.python.wheel_builder.run")
    def test_build_wheel_with_options(self, mock_run: Mock) -> None:
        """Test wheel building with custom build options."""
        from flavor.packaging.python.wheel_builder import _PINNED_BUILD_BACKENDS

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Built wheel: mypackage-1.0.0-py3-none-any.whl"
        mock_run.side_effect = [mock_result, mock_result, mock_result]

        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "mypackage"
            source_path.mkdir()
            wheel_dir = Path(temp_dir) / "wheels"
            wheel_dir.mkdir()

            # Create a mock wheel file
            wheel_file = wheel_dir / "mypackage-1.0.0-py3-none-any.whl"
            wheel_file.touch()

            python_exe = Path("/usr/bin/python3")
            build_options = {
                "verbose": True,
                "config-settings": "key=value",
                "no-build-isolation": False,
            }

            with patch("flavor.packaging.python.wheel_builder.importlib_metadata") as mock_meta:
                mock_meta.version.side_effect = lambda pkg: _PINNED_BUILD_BACKENDS[pkg]
                self.wheel_builder.build_wheel_from_source(
                    python_exe,
                    source_path,
                    wheel_dir,
                    use_isolation=False,
                    build_options=build_options,
                )

            # Verify command includes custom options
            args, _kwargs = mock_run.call_args_list[-1]
            cmd = args[0]

            assert "--no-build-isolation" in cmd
            assert "--verbose" in cmd
            assert "--config-settings" in cmd
            assert "key=value" in cmd

    def test_find_built_wheel_exact_match(self) -> None:
        """Test finding built wheel with exact package name match."""
        with tempfile.TemporaryDirectory() as temp_dir:
            wheel_dir = Path(temp_dir)

            # Create multiple wheel files
            wheel1 = wheel_dir / "mypackage-1.0.0-py3-none-any.whl"
            wheel2 = wheel_dir / "otherpackage-2.0.0-py3-none-any.whl"
            wheel1.touch()
            wheel2.touch()

            result = self.wheel_builder._find_built_wheel(wheel_dir, "mypackage")
            assert result.name == "mypackage-1.0.0-py3-none-any.whl"

    def test_find_built_wheel_no_match_returns_newest(self) -> None:
        """Test finding built wheel returns newest when no exact match."""
        with tempfile.TemporaryDirectory() as temp_dir:
            wheel_dir = Path(temp_dir)

            # Create wheel files with different timestamps
            wheel1 = wheel_dir / "package1-1.0.0-py3-none-any.whl"
            wheel2 = wheel_dir / "package2-2.0.0-py3-none-any.whl"
            wheel1.touch()

            import time

            time.sleep(0.01)  # Ensure different timestamps
            wheel2.touch()

            result = self.wheel_builder._find_built_wheel(wheel_dir, "unknown")
            assert result.name == "package2-2.0.0-py3-none-any.whl"

    def test_find_built_wheel_no_wheels_raises_error(self) -> None:
        """Test finding built wheel raises error when no wheels exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            wheel_dir = Path(temp_dir)

            with pytest.raises(FileNotFoundError):
                self.wheel_builder._find_built_wheel(wheel_dir, "mypackage")

    def test_resolve_dependencies_with_packages(self) -> None:
        """Test dependency resolution with package list."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            python_exe = Path("/usr/bin/python3")
            packages = ["requests", "click"]

            # Mock UV compile_requirements to succeed
            with patch.object(self.wheel_builder.uv, "compile_requirements") as mock_compile:
                result = self.wheel_builder.resolve_dependencies(
                    python_exe, packages=packages, output_dir=output_dir
                )

                # Verify requirements.in was created
                requirements_in = output_dir / "requirements.in"
                assert requirements_in.exists()

                content = requirements_in.read_text()
                assert "requests" in content
                assert "click" in content

                # Verify UV was called
                mock_compile.assert_called_once()
                args = mock_compile.call_args[0]
                assert args[0] == requirements_in
                assert args[1] == output_dir / "requirements.txt"
                assert args[2] == "3.11"

                # Result should be locked requirements file
                assert result.name == "requirements.txt"

    @patch("flavor.packaging.python.wheel_builder.run")
    def test_resolve_dependencies_fallback_to_pip_tools(self, mock_run: Mock) -> None:
        """Test fallback to pip-tools when UV fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            requirements_file = output_dir / "requirements.in"
            requirements_file.write_text("requests>=2.0.0\n")

            python_exe = Path("/usr/bin/python3")

            # Mock UV to fail
            with patch.object(self.wheel_builder.uv, "compile_requirements") as mock_uv_compile:
                mock_uv_compile.side_effect = Exception("UV failed")

                # Mock successful pip-tools execution
                mock_run.return_value = Mock(returncode=0)

                result = self.wheel_builder.resolve_dependencies(
                    python_exe,
                    requirements_file=requirements_file,
                    output_dir=output_dir,
                )

                # Verify UV was attempted
                mock_uv_compile.assert_called_once()

                # Verify pip-tools was called as fallback
                mock_run.assert_called()
                args = mock_run.call_args_list[-1][0]
                cmd = args[0]
                assert "-m" in cmd
                assert "piptools" in cmd
                assert "compile" in cmd

                assert result.name == "requirements.txt"

    def test_resolve_dependencies_no_input_raises_error(self) -> None:
        """Test error when no requirements file or packages provided."""
        python_exe = Path("/usr/bin/python3")

        with pytest.raises(ValueError, match="Either requirements_file or packages must be provided"):
            self.wheel_builder.resolve_dependencies(python_exe)

    def test_download_wheels_for_resolved_deps(self) -> None:
        """Test downloading wheels for resolved dependencies."""
        with tempfile.TemporaryDirectory() as temp_dir:
            wheel_dir = Path(temp_dir) / "wheels"
            requirements_file = Path(temp_dir) / "requirements.txt"
            requirements_file.write_text("requests==2.28.0\nclick==8.0.0\n")

            # Create mock wheel files
            wheel_dir.mkdir()
            wheel1 = wheel_dir / "requests-2.28.0-py3-none-any.whl"
            wheel2 = wheel_dir / "click-8.0.0-py3-none-any.whl"
            wheel1.touch()
            wheel2.touch()

            python_exe = Path("/usr/bin/python3")

            # Patch the pypapip instance method
            with patch.object(
                self.wheel_builder.pypapip, "download_wheels_from_requirements"
            ) as mock_download:
                result = self.wheel_builder.download_wheels_for_resolved_deps(
                    python_exe, requirements_file, wheel_dir
                )

                # Verify PyPA pip was used for download
                mock_download.assert_called_once_with(python_exe, requirements_file, wheel_dir)

            # Verify result contains wheel files
            assert len(result) == 2
            assert any(wheel.name == "requests-2.28.0-py3-none-any.whl" for wheel in result)
            assert any(wheel.name == "click-8.0.0-py3-none-any.whl" for wheel in result)

    @patch("flavor.packaging.python.wheel_builder.run")
    def test_build_and_resolve_project_complete(self, mock_run: Mock) -> None:
        """Test complete project building and resolution."""
        from flavor.packaging.python.wheel_builder import _PINNED_BUILD_BACKENDS

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Built wheel: myproject-1.0.0-py3-none-any.whl"
        mock_run.side_effect = [mock_result, mock_result, mock_result]

        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "myproject"
            project_dir.mkdir()
            build_dir = Path(temp_dir) / "build"

            # Create requirements file
            requirements_file = Path(temp_dir) / "requirements.txt"
            requirements_file.write_text("requests>=2.0.0\n")

            python_exe = Path("/usr/bin/python3")

            # Mock dependency resolution and wheel creation
            with (
                patch("flavor.packaging.python.wheel_builder.importlib_metadata") as mock_meta,
                patch.object(self.wheel_builder, "resolve_dependencies") as mock_resolve,
                patch.object(self.wheel_builder, "download_wheels_for_resolved_deps") as mock_download,
            ):
                mock_meta.version.side_effect = lambda pkg: _PINNED_BUILD_BACKENDS[pkg]
                # Setup mock returns
                locked_reqs = build_dir / "deps" / "requirements.txt"
                locked_reqs.parent.mkdir(parents=True)
                locked_reqs.touch()
                mock_resolve.return_value = locked_reqs

                wheel_dir = build_dir / "wheels"
                wheel_dir.mkdir(parents=True)
                project_wheel = wheel_dir / "myproject-1.0.0-py3-none-any.whl"
                project_wheel.touch()

                dep_wheels = [
                    wheel_dir / "requests-2.28.0-py3-none-any.whl",
                    wheel_dir / "urllib3-1.26.0-py3-none-any.whl",
                ]
                for wheel in dep_wheels:
                    wheel.touch()
                mock_download.return_value = dep_wheels

                result = self.wheel_builder.build_and_resolve_project(
                    python_exe,
                    project_dir,
                    build_dir,
                    requirements_file=requirements_file,
                    extra_packages=["click"],
                )

                # Verify all operations were called
                mock_run.assert_called()  # For wheel building
                mock_resolve.assert_called_once()
                mock_download.assert_called_once()

                # Verify result structure
                assert "project_wheel" in result
                assert "dependency_wheels" in result
                assert "locked_requirements" in result
                assert "wheel_dir" in result
                assert "total_wheels" in result

                assert result["total_wheels"] == 3  # 1 project + 2 deps
                assert len(result["dependency_wheels"]) == 2


# 🌶️📦🔚
