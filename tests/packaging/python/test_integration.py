#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Integration tests for Python packaging managers working together."""

from pathlib import Path
import sys
import tempfile
from unittest.mock import Mock, patch

from provide.foundation.archive import GzipCompressor, TarArchive
import pytest

from flavor.packaging.python.dist_manager import PythonDistManager
from flavor.packaging.python.pypapip_manager import PyPaPipManager
from flavor.packaging.python.uv_manager import UVManager
from flavor.packaging.python.wheel_builder import WheelBuilder


class TestPythonPackagingIntegration:
    """Test integration between all Python packaging managers."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.python_version = "3.11"

        # Initialize all managers
        self.pypapip = PyPaPipManager(python_version=self.python_version)
        self.uv_manager = UVManager()
        self.wheel_builder = WheelBuilder(python_version=self.python_version)
        self.dist_manager = PythonDistManager(python_version=self.python_version)
        self.tar_archive = TarArchive(deterministic=True)
        self.gzip_compressor = GzipCompressor()

    def test_managers_initialization_compatible(self) -> None:
        """Test that all managers initialize without conflicts."""
        # All managers should be independent instances
        assert self.pypapip is not self.uv_manager
        assert self.pypapip is not self.wheel_builder
        assert self.pypapip is not self.dist_manager

        # All managers should have their expected capabilities
        assert hasattr(self.pypapip, "_get_pypapip_install_cmd")
        assert hasattr(self.uv_manager, "_get_uv_venv_cmd")
        assert hasattr(self.wheel_builder, "build_wheel_from_source")
        assert hasattr(self.dist_manager, "create_python_environment")
        assert hasattr(self.tar_archive, "create")

    def test_python_version_consistency(self) -> None:
        """Test that Python version is consistent across managers."""
        assert self.pypapip.python_version == self.python_version
        assert self.wheel_builder.python_version == self.python_version
        assert self.dist_manager.python_version == self.python_version

    @patch("flavor.packaging.python.wheel_builder.run")
    @patch("flavor.packaging.python.dist_manager.run")
    def test_wheel_builder_dist_manager_integration(self, mock_dist_run: Mock, mock_wheel_run: Mock) -> None:
        """Test WheelBuilder and PythonDistManager working together."""
        # Mock successful command execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Success"
        mock_dist_run.return_value = mock_result
        mock_wheel_run.return_value = mock_result

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create mock project structure
            project_dir = temp_path / "test_project"
            project_dir.mkdir()
            (project_dir / "setup.py").write_text("from setuptools import setup; setup(name='test')")
            (project_dir / "pyproject.toml").write_text("""
[project]
name = "test-project"
version = "1.0.0"
""")

            build_dir = temp_path / "build"
            build_dir.mkdir()

            # Mock the managers' dependencies
            with (
                patch.object(self.wheel_builder, "pypapip") as mock_pypapip,
                patch.object(self.wheel_builder, "uv"),
                patch.object(self.dist_manager, "pypapip"),
            ):
                # Mock wheel building
                mock_pypapip._get_pypapip_wheel_cmd.return_value = [
                    "python",
                    "-m",
                    "pip",
                    "wheel",
                    str(project_dir),
                ]

                # Mock wheel files
                wheel_dir = build_dir / "wheels"
                wheel_dir.mkdir(parents=True)
                test_wheel = wheel_dir / "test_project-1.0.0-py3-none-any.whl"
                test_wheel.touch()

                # Test wheel building
                result = self.wheel_builder.build_wheel_from_source(
                    python_exe=Path(sys.executable),
                    source_path=project_dir,
                    wheel_dir=wheel_dir,
                )

                assert result.exists()
                assert result.name.endswith(".whl")

    @patch("shutil.which")
    def test_uv_manager_system_detection(self, mock_which: Mock) -> None:
        """Test UVManager system UV detection."""
        # Test when UV is found
        mock_which.return_value = "/usr/local/bin/uv"

        result = self.uv_manager.find_system_uv()
        assert result == Path("/usr/local/bin/uv")

        # Test when UV is not found
        mock_which.return_value = None
        result = self.uv_manager.find_system_uv()
        assert result is None

    def test_archive_utils_deterministic_output(self) -> None:
        """Test foundation archive tools produce deterministic output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create identical test structures with same directory name
            tar_files = []
            for i in range(2):
                # Use the same source directory name for consistent archive structure
                source_dir = temp_path / "source"  # Same name for both
                if source_dir.exists():
                    import shutil

                    shutil.rmtree(source_dir)
                source_dir.mkdir()
                (source_dir / "file.txt").write_text("Content")

                # Create tar files (deterministic)
                tar_path = temp_path / f"archive_{i}.tar"
                self.tar_archive.create(source_dir, tar_path)
                tar_files.append(tar_path)

            # Tar files should be identical
            tar_0_bytes = tar_files[0].read_bytes()
            tar_1_bytes = tar_files[1].read_bytes()
            assert tar_0_bytes == tar_1_bytes

            # Compress using bytes to avoid filename in gzip header
            gz_0_bytes = self.gzip_compressor.compress_bytes(tar_0_bytes)
            gz_1_bytes = self.gzip_compressor.compress_bytes(tar_1_bytes)

            # Compressed bytes should be identical
            assert gz_0_bytes == gz_1_bytes

    def test_pypapip_manylinux_compatibility(self) -> None:
        """Test PyPaPipManager manylinux compatibility."""
        with (
            patch("flavor.packaging.python.pypapip_manager.get_os_name") as mock_os,
            patch("flavor.packaging.python.pypapip_manager.get_arch_name") as mock_arch,
        ):
            mock_os.return_value = "linux"
            mock_arch.return_value = "amd64"

            python_exe = Path("/usr/bin/python")
            dest_dir = Path("/tmp/wheels")
            packages = ["numpy"]

            cmd = self.pypapip._get_pypapip_download_cmd(
                python_exe, dest_dir, packages=packages, binary_only=True
            )

            # Should include manylinux2014_x86_64 for Linux compatibility
            assert "manylinux2014_x86_64" in cmd
            assert "--python-version" in cmd
            assert "3.11" in cmd

    def test_manager_error_isolation(self) -> None:
        """Test that errors in one manager don't affect others."""
        # Test that UV manager errors don't affect PyPA pip
        with patch.object(self.uv_manager, "find_system_uv") as mock_uv_find:
            mock_uv_find.side_effect = Exception("UV error")

            # PyPA pip should still work
            python_exe = Path("/usr/bin/python")
            packages = ["test-package"]

            cmd = self.pypapip._get_pypapip_install_cmd(python_exe, packages)
            expected = ["/usr/bin/python", "-m", "pip", "install", "test-package"]
            assert cmd == expected

    @patch("flavor.packaging.python.dist_manager.run")
    def test_dist_manager_wheel_installation(self, mock_run: Mock) -> None:
        """Test PythonDistManager wheel installation integration."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create mock wheels
            wheel_files = [
                temp_path / "package1-1.0.0-py3-none-any.whl",
                temp_path / "package2-2.0.0-py3-none-any.whl",
            ]

            for wheel in wheel_files:
                wheel.touch()

            venv_python = temp_path / "venv" / "bin" / "python"

            # Test installation
            self.dist_manager.install_wheels_to_environment(venv_python, wheel_files)

            # Verify PyPA pip was used (not UV pip)
            mock_run.assert_called_once()
            args = mock_run.call_args[0]
            cmd = args[0]

            assert cmd[1:4] == ["-m", "pip", "install"]
            assert "--no-deps" in cmd

    def test_all_managers_use_same_python_version(self) -> None:
        """Test that all managers can be configured with the same Python version."""
        test_version = "3.12"

        # Initialize all managers with same version
        pypapip_312 = PyPaPipManager(python_version=test_version)
        wheel_builder_312 = WheelBuilder(python_version=test_version)
        dist_manager_312 = PythonDistManager(python_version=test_version)

        assert pypapip_312.python_version == test_version
        assert wheel_builder_312.python_version == test_version
        assert dist_manager_312.python_version == test_version

        # Verify they can work together
        assert wheel_builder_312.pypapip.python_version == test_version
        assert dist_manager_312.pypapip.python_version == test_version


class TestPackagingWorkflow:
    """Test realistic packaging workflows using all managers together."""

    def test_complete_packaging_workflow_mock(self) -> None:
        """Test complete packaging workflow with mocked operations."""
        python_version = "3.11"

        # Initialize managers
        PyPaPipManager(python_version=python_version)
        UVManager()
        wheel_builder = WheelBuilder(python_version=python_version)
        dist_manager = PythonDistManager(python_version=python_version)
        tar_archive = TarArchive(deterministic=True)
        gzip_compressor = GzipCompressor()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create mock project
            project_dir = temp_path / "test_project"
            project_dir.mkdir()
            (project_dir / "setup.py").write_text("""
from setuptools import setup
setup(name='test-project', version='1.0.0', py_modules=['main'])
""")
            (project_dir / "main.py").write_text("def main(): print('Hello, World!')")

            # Mock all the complex operations
            with (
                patch.object(wheel_builder, "build_and_resolve_project") as mock_build,
                patch.object(dist_manager, "create_standalone_distribution") as mock_dist,
            ):
                # Mock successful wheel building
                wheel_dir = temp_path / "wheels"
                wheel_dir.mkdir()
                test_wheel = wheel_dir / "test_project-1.0.0-py3-none-any.whl"
                test_wheel.touch()

                mock_build.return_value = {
                    "project_wheel": test_wheel,
                    "dependency_wheels": [],
                    "wheel_dir": wheel_dir,
                    "total_wheels": 1,
                }

                # Mock successful distribution creation
                site_packages = temp_path / "site-packages"
                site_packages.mkdir()
                (site_packages / "test_module.py").write_text("# Test module")

                mock_dist.return_value = {
                    "project_name": "test-project",
                    "site_packages": site_packages,
                    "distribution_size": 1024,
                    "total_wheels": 1,
                }

                # Test the workflow
                # 1. Build wheels
                build_result = wheel_builder.build_and_resolve_project(
                    python_exe=Path(sys.executable),
                    project_dir=project_dir,
                    build_dir=temp_path / "build",
                )

                assert build_result["total_wheels"] == 1
                assert build_result["project_wheel"].exists()

                # 2. Create distribution
                dist_result = dist_manager.create_standalone_distribution(
                    project_dir=project_dir, output_dir=temp_path / "output"
                )

                assert dist_result["project_name"] == "test-project"
                assert dist_result["site_packages"].exists()

                # 3. Create archive using foundation tools
                archive_path = temp_path / "final.tar.gz"
                tar_path = temp_path / "final.tar"
                tar_archive.create(dist_result["site_packages"], tar_path)

                # Compress deterministically
                tar_bytes = tar_path.read_bytes()
                gz_bytes = gzip_compressor.compress_bytes(tar_bytes)
                archive_path.write_bytes(gz_bytes)

                assert archive_path.exists()

                # 4. Basic validation - archive exists and has content
                assert archive_path.stat().st_size > 0

    def test_error_handling_across_managers(self) -> None:
        """Test error handling when managers interact."""
        wheel_builder = WheelBuilder(python_version="3.11")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create invalid project (missing setup.py)
            project_dir = temp_path / "invalid_project"
            project_dir.mkdir()

            # Should handle errors gracefully
            with patch.object(wheel_builder, "pypapip") as mock_pypapip:
                mock_pypapip._get_pypapip_wheel_cmd.side_effect = RuntimeError("Build failed")

                with pytest.raises(RuntimeError, match="Build failed"):
                    wheel_builder.build_wheel_from_source(
                        python_exe=Path(sys.executable),
                        source_path=project_dir,
                        wheel_dir=temp_path / "wheels",
                    )


# 🌶️📦🔚
