#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for PythonDistManager distribution handling functionality."""

import os
from pathlib import Path
import tempfile
from typing import Any
from unittest.mock import Mock, patch

from flavor.packaging.python.dist_manager import PythonDistManager


class TestPythonDistManager:
    """Test PythonDistManager functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.dist_manager = PythonDistManager(python_version="3.11")

    def test_initialization(self) -> None:
        """Test PythonDistManager initialization."""
        assert self.dist_manager.python_version == "3.11"
        assert self.dist_manager.use_uv_for_venv is True
        assert hasattr(self.dist_manager, "pypapip")
        assert hasattr(self.dist_manager, "uv")
        assert hasattr(self.dist_manager, "wheel_builder")

        # Test without UV
        manager_no_uv = PythonDistManager(use_uv_for_venv=False)
        assert manager_no_uv.uv is None

    @patch("flavor.packaging.python.dist_manager.run")
    def test_create_python_environment_with_uv(self, mock_run: Mock) -> None:
        """Test Python environment creation using UV."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir) / "test_venv"
            python_exe = Path("/usr/bin/python3")

            # Mock UV create_venv to succeed
            with patch.object(self.dist_manager.uv, "create_venv") as mock_uv_create:
                # Mock the venv structure
                venv_path.mkdir(parents=True)
                venv_python = venv_path / "bin" / "python"
                venv_python.parent.mkdir(parents=True)
                venv_python.touch()

                result = self.dist_manager.create_python_environment(venv_path, python_exe)

                # Verify UV was used
                mock_uv_create.assert_called_once_with(venv_path, python_version="3.11")

                # Verify result
                assert result == venv_python
                assert result.exists()

    @patch("flavor.packaging.python.dist_manager.run")
    def test_create_python_environment_fallback_to_venv(self, mock_run: Mock) -> None:
        """Test fallback to standard venv when UV fails."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir) / "test_venv"
            python_exe = Path("/usr/bin/python3")

            # Mock UV to fail
            with patch.object(self.dist_manager.uv, "create_venv") as mock_uv_create:
                mock_uv_create.side_effect = Exception("UV failed")

                # Mock the venv structure
                def mock_venv_creation(*args: Any, **kwargs: Any) -> Any:
                    venv_path.mkdir(parents=True)
                    venv_python = venv_path / "bin" / "python"
                    venv_python.parent.mkdir(parents=True)
                    venv_python.touch()
                    return mock_result

                mock_run.side_effect = mock_venv_creation

                result = self.dist_manager.create_python_environment(venv_path, python_exe)

                # Verify UV was attempted
                mock_uv_create.assert_called_once()

                # Verify standard venv was used as fallback
                mock_run.assert_called_once()
                args = mock_run.call_args[0]
                cmd = args[0]
                assert cmd[0] == "/usr/bin/python3"
                assert cmd[1:4] == ["-m", "venv", str(venv_path)]

                # Verify result
                assert result.name == "python"

    def test_get_venv_python_path_unix(self) -> None:
        """Test getting venv Python path on Unix systems."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir) / "venv"

            with patch("os.name", "posix"):
                result = self.dist_manager._get_venv_python_path(venv_path)
                expected = venv_path / "bin" / "python"
                assert result == expected

    def test_get_venv_python_path_windows(self) -> None:
        """Test getting venv Python path on Windows."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir) / "venv"

            with patch("os.name", "nt"):
                result = self.dist_manager._get_venv_python_path(venv_path)
                expected = venv_path / "Scripts" / "python.exe"
                assert result == expected

    @patch("flavor.packaging.python.dist_manager.run")
    def test_install_wheels_to_environment(self, mock_run: Mock) -> None:
        """Test installing wheels to Python environment."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        with tempfile.TemporaryDirectory() as temp_dir:
            venv_python = Path(temp_dir) / "venv" / "bin" / "python"

            wheel_files = [
                Path(temp_dir) / "package1-1.0.0-py3-none-any.whl",
                Path(temp_dir) / "package2-2.0.0-py3-none-any.whl",
            ]

            for wheel in wheel_files:
                wheel.touch()

            self.dist_manager.install_wheels_to_environment(venv_python, wheel_files)

            # Verify run was called
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args

            cmd = args[0]
            assert cmd[0] == str(venv_python)
            assert cmd[1:4] == ["-m", "pip", "install"]
            assert "--no-deps" in cmd
            assert str(wheel_files[0]) in cmd
            assert str(wheel_files[1]) in cmd

            # Verify error handling enabled
            assert kwargs["check"] is True

    def test_install_wheels_empty_list(self) -> None:
        """Test installing empty wheel list does nothing."""
        venv_python = Path("/tmp/venv/bin/python")

        with patch("flavor.packaging.python.dist_manager.run") as mock_run:
            self.dist_manager.install_wheels_to_environment(venv_python, [])

            # Should not call run for empty list
            mock_run.assert_not_called()

    @patch("flavor.packaging.python.dist_manager.run")
    def test_prepare_site_packages(self, mock_run: Mock) -> None:
        """Test site-packages preparation."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir) / "venv"
            venv_python = venv_path / "bin" / "python"
            site_packages = venv_path / "lib" / "python3.11" / "site-packages"

            # Create mock site-packages structure
            site_packages.mkdir(parents=True)

            # Create some test files
            test_package = site_packages / "test_package"
            test_package.mkdir()
            (test_package / "__init__.py").touch()

            pycache_dir = test_package / "__pycache__"
            pycache_dir.mkdir()
            (pycache_dir / "test.pyc").touch()

            result = self.dist_manager.prepare_site_packages(venv_python, optimization_level=1)

            # Verify compilation was attempted
            mock_run.assert_called()
            args = mock_run.call_args[0]
            cmd = args[0]
            assert cmd[0] == str(venv_python)
            assert cmd[1:3] == ["-m", "compileall"]
            assert "-b" in cmd
            assert str(site_packages) in cmd

            # Verify result
            assert result == site_packages

    def test_compile_python_files(self) -> None:
        """Test Python file compilation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_python = Path(temp_dir) / "venv" / "bin" / "python"
            site_packages = Path(temp_dir) / "site-packages"
            site_packages.mkdir()

            with patch("flavor.packaging.python.dist_manager.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)

                self.dist_manager._compile_python_files(venv_python, site_packages, 2)

                args = mock_run.call_args[0]
                cmd = args[0]
                assert cmd[0] == str(venv_python)
                assert cmd[1:3] == ["-m", "compileall"]
                assert "-b" in cmd
                assert "-O2" in cmd
                assert f"-j{os.cpu_count() or 1}" in cmd
                assert str(site_packages) in cmd

    def test_cleanup_site_packages(self) -> None:
        """Test site-packages cleanup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            site_packages = Path(temp_dir) / "site-packages"

            # Create test structure with files to be cleaned
            example_package = site_packages / "example_package"
            example_package.mkdir(parents=True)

            # Files that should be removed
            pycache_dir = example_package / "__pycache__"
            pycache_dir.mkdir()
            (pycache_dir / "test.pyc").touch()

            test_dir = example_package / "tests"
            test_dir.mkdir()
            (test_dir / "test_something.py").touch()

            egg_info = site_packages / "package.egg-info"
            egg_info.mkdir()
            (egg_info / "PKG-INFO").touch()

            # Files that should remain
            (example_package / "__init__.py").touch()
            (example_package / "main.py").touch()

            self.dist_manager._cleanup_site_packages(site_packages)

            # Verify cleanup
            assert not pycache_dir.exists()
            assert not test_dir.exists()
            assert not egg_info.exists()

            # Verify important files remain
            assert (example_package / "__init__.py").exists()
            assert (example_package / "main.py").exists()

    def test_get_directory_size(self) -> None:
        """Test directory size calculation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir) / "test"
            test_dir.mkdir()

            # Create files with known sizes
            file1 = test_dir / "file1.txt"
            file2 = test_dir / "subdir" / "file2.txt"
            file2.parent.mkdir()

            file1.write_text("Hello")  # 5 bytes
            file2.write_text("World!")  # 6 bytes

            size = self.dist_manager._get_directory_size(test_dir)
            assert size == 11  # 5 + 6 bytes

    def test_validate_distribution_valid(self) -> None:
        """Test distribution validation with valid distribution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            site_packages = Path(temp_dir) / "site-packages"
            site_packages.mkdir()

            # Create some content
            (site_packages / "setuptools").mkdir()
            (site_packages / "pkg_resources.py").touch()

            dist_info = {
                "site_packages": site_packages,
                "distribution_size": 1024 * 1024,  # 1MB
            }

            result = self.dist_manager.validate_distribution(dist_info)
            assert result is True

    def test_validate_distribution_empty(self) -> None:
        """Test distribution validation with empty site-packages."""
        with tempfile.TemporaryDirectory() as temp_dir:
            site_packages = Path(temp_dir) / "site-packages"
            site_packages.mkdir()

            dist_info = {
                "site_packages": site_packages,
                "distribution_size": 0,
            }

            result = self.dist_manager.validate_distribution(dist_info)
            assert result is False

    def test_validate_distribution_missing(self) -> None:
        """Test distribution validation with missing site-packages."""
        with tempfile.TemporaryDirectory() as temp_dir:
            site_packages = Path(temp_dir) / "nonexistent"

            dist_info = {
                "site_packages": site_packages,
                "distribution_size": 0,
            }

            result = self.dist_manager.validate_distribution(dist_info)
            assert result is False

    @patch.object(PythonDistManager, "create_python_environment")
    @patch.object(PythonDistManager, "install_wheels_to_environment")
    @patch.object(PythonDistManager, "prepare_site_packages")
    @patch("shutil.copytree")
    def test_create_standalone_distribution(
        self, mock_copytree: Mock, mock_prepare: Mock, mock_install: Mock, mock_create_env: Mock
    ) -> None:
        """Test complete standalone distribution creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "myproject"
            project_dir.mkdir()
            output_dir = Path(temp_dir) / "output"

            # Mock wheel building by replacing the instance attribute
            mock_wheel_builder = Mock()
            build_info = {
                "project_wheel": Path(temp_dir) / "project-1.0.0-py3-none-any.whl",
                "dependency_wheels": [Path(temp_dir) / "dep-1.0.0-py3-none-any.whl"],
                "locked_requirements": Path(temp_dir) / "requirements.txt",
                "wheel_dir": Path(temp_dir) / "wheels",
                "total_wheels": 2,
            }
            mock_wheel_builder.build_and_resolve_project.return_value = build_info
            self.dist_manager.wheel_builder = mock_wheel_builder

            # Mock environment creation
            venv_python = Path(temp_dir) / "venv" / "bin" / "python"
            mock_create_env.return_value = venv_python

            # Mock site-packages preparation
            site_packages = Path(temp_dir) / "site-packages"
            site_packages.mkdir()
            mock_prepare.return_value = site_packages

            result = self.dist_manager.create_standalone_distribution(project_dir, output_dir)

            # Verify all steps were called
            mock_wheel_builder.build_and_resolve_project.assert_called_once()
            mock_create_env.assert_called_once()
            mock_install.assert_called_once()
            mock_prepare.assert_called_once()
            mock_copytree.assert_called_once()

            # Verify result structure
            assert "project_name" in result
            assert "python_version" in result
            assert "site_packages" in result
            assert "total_wheels" in result
            assert "build_info" in result
            assert "venv_python" in result
            assert "distribution_size" in result

            assert result["project_name"] == "myproject"
            assert result["python_version"] == "3.11"
            assert result["total_wheels"] == 2


class TestPythonDistManagerCriticalFeatures:
    """Test CRITICAL features that must never be broken."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.dist_manager = PythonDistManager()

    def test_uses_separate_managers(self) -> None:
        """CRITICAL: Must use separate specialized managers."""
        assert hasattr(self.dist_manager, "pypapip")
        assert hasattr(self.dist_manager, "uv")
        assert hasattr(self.dist_manager, "wheel_builder")

        # Verify they're different instances
        assert self.dist_manager.pypapip is not self.dist_manager.uv
        assert self.dist_manager.pypapip is not self.dist_manager.wheel_builder
        assert self.dist_manager.uv is not self.dist_manager.wheel_builder

    def test_uv_fallback_behavior(self) -> None:
        """CRITICAL: UV must have fallback to standard tools."""
        # UV can be disabled
        manager_no_uv = PythonDistManager(use_uv_for_venv=False)
        assert manager_no_uv.uv is None

        # Manager should still function without UV
        assert hasattr(manager_no_uv, "pypapip")
        assert hasattr(manager_no_uv, "wheel_builder")

    def test_always_uses_pypapip_for_installation(self) -> None:
        """CRITICAL: Must always use PyPA pip for wheel installation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_python = Path(temp_dir) / "venv" / "bin" / "python"
            wheel_files = [Path(temp_dir) / "test.whl"]
            wheel_files[0].touch()

            with patch("flavor.packaging.python.dist_manager.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)

                self.dist_manager.install_wheels_to_environment(venv_python, wheel_files)

                args = mock_run.call_args[0]
                cmd = args[0]
                # Must use pip, not uv pip
                assert cmd[1:4] == ["-m", "pip", "install"]

    def test_site_packages_cleanup_preserves_critical_files(self) -> None:
        """CRITICAL: Cleanup must not remove critical Python files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            site_packages = Path(temp_dir) / "site-packages"

            # Create critical files that must be preserved
            critical_files = [
                site_packages / "setuptools" / "__init__.py",
                site_packages / "pkg_resources.py",
                site_packages / "_distutils_hack" / "__init__.py",
                site_packages / "important_package" / "main.py",
            ]

            for file_path in critical_files:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.touch()

            # Create files that should be removed
            removable_files = [
                site_packages / "test_package" / "__pycache__" / "test.pyc",
                site_packages / "package" / "tests" / "test_something.py",
                site_packages / "package.egg-info" / "PKG-INFO",
            ]

            for file_path in removable_files:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.touch()

            self.dist_manager._cleanup_site_packages(site_packages)

            # Verify critical files are preserved
            for critical_file in critical_files:
                assert critical_file.exists(), f"Critical file removed: {critical_file}"

            # Verify removable files are gone
            for removable_file in removable_files:
                assert not removable_file.exists(), f"File not removed: {removable_file}"

    def test_distribution_validation_comprehensive(self) -> None:
        """CRITICAL: Distribution validation must be thorough."""
        with tempfile.TemporaryDirectory() as temp_dir:
            site_packages = Path(temp_dir) / "site-packages"
            site_packages.mkdir()

            # Create minimal valid structure
            (site_packages / "setuptools").mkdir()
            (site_packages / "pkg_resources.py").touch()

            dist_info = {
                "site_packages": site_packages,
                "distribution_size": 10 * 1024 * 1024,  # 10MB
            }

            # Should pass validation
            assert self.dist_manager.validate_distribution(dist_info) is True

            # Test size warning threshold
            dist_info["distribution_size"] = 600 * 1024 * 1024  # 600MB
            with patch("flavor.packaging.python.dist_manager.logger") as mock_logger:
                result = self.dist_manager.validate_distribution(dist_info)
                assert result is True  # Still valid but should warn
                mock_logger.warning.assert_called()


# 🌶️📦🔚
