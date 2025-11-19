#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for PyPaPipManager critical functionality."""

from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

from flavor.packaging.python.pypapip_manager import PyPaPipManager


class TestPyPaPipManager:
    """Test PyPA pip manager critical functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.pip_manager = PyPaPipManager(python_version="3.11")

    def test_initialization(self) -> None:
        """Test PyPaPipManager initialization."""
        assert self.pip_manager.python_version == "3.11"
        assert self.pip_manager.MANYLINUX_TAG == "manylinux2014"

        # Test custom python version
        custom_manager = PyPaPipManager(python_version="3.12")
        assert custom_manager.python_version == "3.12"

    def test_get_pypapip_install_cmd(self) -> None:
        """Test PyPA pip install command generation."""
        python_exe = Path("/usr/bin/python3")
        packages = ["numpy", "scipy"]

        cmd = self.pip_manager._get_pypapip_install_cmd(python_exe, packages)

        expected = ["/usr/bin/python3", "-m", "pip", "install", "numpy", "scipy"]
        assert cmd == expected

    def test_get_pypapip_wheel_cmd_basic(self) -> None:
        """Test PyPA pip wheel command generation."""
        python_exe = Path("/usr/bin/python3")
        wheel_dir = Path("/tmp/wheels")
        source_dir = Path("/tmp/mypackage")

        cmd = self.pip_manager._get_pypapip_wheel_cmd(python_exe, wheel_dir, source_dir, no_deps=False)

        expected = [
            "/usr/bin/python3",
            "-m",
            "pip",
            "wheel",
            "--wheel-dir",
            "/tmp/wheels",
            "/tmp/mypackage",
        ]
        assert cmd == expected

    def test_get_pypapip_wheel_cmd_no_deps(self) -> None:
        """Test PyPA pip wheel command with no-deps flag."""
        python_exe = Path("/usr/bin/python3")
        wheel_dir = Path("/tmp/wheels")
        source_dir = Path("/tmp/mypackage")

        cmd = self.pip_manager._get_pypapip_wheel_cmd(python_exe, wheel_dir, source_dir, no_deps=True)

        expected = [
            "/usr/bin/python3",
            "-m",
            "pip",
            "wheel",
            "--wheel-dir",
            "/tmp/wheels",
            "--no-deps",
            "/tmp/mypackage",
        ]
        assert cmd == expected

    @patch("flavor.packaging.python.pypapip_manager.get_os_name")
    def test_get_pypapip_download_cmd_non_linux(self, mock_os_name: Mock) -> None:
        """Test PyPA pip download command on non-Linux systems."""
        mock_os_name.return_value = "darwin"

        python_exe = Path("/usr/bin/python3")
        dest_dir = Path("/tmp/downloads")
        packages = ["requests"]

        cmd = self.pip_manager._get_pypapip_download_cmd(
            python_exe, dest_dir, packages=packages, binary_only=True
        )

        expected = [
            "/usr/bin/python3",
            "-m",
            "pip",
            "download",
            "--dest",
            "/tmp/downloads",
            "--only-binary",
            ":all:",
            "--python-version",
            "3.11",
            "requests",
        ]
        assert cmd == expected

    @patch("flavor.packaging.python.pypapip_manager.get_arch_name")
    @patch("flavor.packaging.python.pypapip_manager.get_os_name")
    def test_get_pypapip_download_cmd_linux_amd64(self, mock_os_name: Mock, mock_arch_name: Mock) -> None:
        """Test CRITICAL manylinux2014 handling for Linux amd64."""
        mock_os_name.return_value = "linux"
        mock_arch_name.return_value = "amd64"

        python_exe = Path("/usr/bin/python3")
        dest_dir = Path("/tmp/downloads")
        packages = ["numpy"]

        cmd = self.pip_manager._get_pypapip_download_cmd(
            python_exe, dest_dir, packages=packages, binary_only=True
        )

        # CRITICAL: Must include manylinux2014_x86_64 platform tag for Linux compatibility
        expected = [
            "/usr/bin/python3",
            "-m",
            "pip",
            "download",
            "--dest",
            "/tmp/downloads",
            "--only-binary",
            ":all:",
            "--python-version",
            "3.11",
            "--platform",
            "manylinux2014_x86_64",
            "numpy",
        ]
        assert cmd == expected

    @patch("flavor.packaging.python.pypapip_manager.get_arch_name")
    @patch("flavor.packaging.python.pypapip_manager.get_os_name")
    def test_get_pypapip_download_cmd_linux_arm64(self, mock_os_name: Mock, mock_arch_name: Mock) -> None:
        """Test CRITICAL manylinux2014 handling for Linux ARM64."""
        mock_os_name.return_value = "linux"
        mock_arch_name.return_value = "arm64"

        python_exe = Path("/usr/bin/python3")
        dest_dir = Path("/tmp/downloads")
        packages = ["scipy"]

        cmd = self.pip_manager._get_pypapip_download_cmd(
            python_exe, dest_dir, packages=packages, binary_only=True
        )

        # CRITICAL: Must include manylinux2014_aarch64 platform tag for ARM64 Linux
        # Note: This matches published wheels (manylinux2014 == manylinux_2_17, both glibc 2.17+)
        expected = [
            "/usr/bin/python3",
            "-m",
            "pip",
            "download",
            "--dest",
            "/tmp/downloads",
            "--only-binary",
            ":all:",
            "--python-version",
            "3.11",
            "--platform",
            "manylinux2014_aarch64",
            "scipy",
        ]
        assert cmd == expected

    def test_get_pypapip_download_cmd_explicit_platform(self) -> None:
        """Test explicit platform tag override."""
        python_exe = Path("/usr/bin/python3")
        dest_dir = Path("/tmp/downloads")
        packages = ["wheel"]

        cmd = self.pip_manager._get_pypapip_download_cmd(
            python_exe,
            dest_dir,
            packages=packages,
            binary_only=True,
            platform_tag="linux_x86_64",
        )

        expected = [
            "/usr/bin/python3",
            "-m",
            "pip",
            "download",
            "--dest",
            "/tmp/downloads",
            "--only-binary",
            ":all:",
            "--python-version",
            "3.11",
            "--platform",
            "linux_x86_64",
            "wheel",
        ]
        assert cmd == expected

    def test_get_pypapip_download_cmd_requirements_file(self) -> None:
        """Test download command with requirements file."""
        python_exe = Path("/usr/bin/python3")
        dest_dir = Path("/tmp/downloads")
        requirements_file = Path("/tmp/requirements.txt")

        cmd = self.pip_manager._get_pypapip_download_cmd(
            python_exe, dest_dir, requirements_file=requirements_file, binary_only=True
        )

        expected = [
            "/usr/bin/python3",
            "-m",
            "pip",
            "download",
            "--dest",
            "/tmp/downloads",
            "--only-binary",
            ":all:",
            "--python-version",
            "3.11",
            "-r",
            "/tmp/requirements.txt",
        ]
        assert cmd == expected

    def test_python_version_parsing(self) -> None:
        """Test Python version parsing for platform tags."""
        # Test different version formats
        manager_310 = PyPaPipManager(python_version="3.10")
        manager_311 = PyPaPipManager(python_version="3.11.5")
        manager_312 = PyPaPipManager(python_version="3.12")

        assert manager_310.python_version == "3.10"
        assert manager_311.python_version == "3.11.5"
        assert manager_312.python_version == "3.12"

        # Test that platform tags use correct Python version
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
            cmd_310 = manager_310._get_pypapip_download_cmd(
                Path("/usr/bin/python3"), Path("/tmp"), packages=["test"]
            )
            cmd_312 = manager_312._get_pypapip_download_cmd(
                Path("/usr/bin/python3"), Path("/tmp"), packages=["test"]
            )

            # Check Python version in commands
            assert "--python-version" in cmd_310 and "3.10" in cmd_310
            assert "--python-version" in cmd_312 and "3.12" in cmd_312

    @patch("flavor.packaging.python.pypapip_manager.run")
    def test_download_wheels_from_requirements(self, mock_run: Mock) -> None:
        """Test downloading wheels from requirements file."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("numpy\nscipy\n")
            f.flush()
            requirements_file = Path(f.name)

        try:
            python_exe = Path("/usr/bin/python3")
            dest_dir = Path("/tmp/wheels")

            self.pip_manager.download_wheels_from_requirements(python_exe, requirements_file, dest_dir)

            # Verify run was called
            mock_run.assert_called_once()
            args, _kwargs = mock_run.call_args

            # Verify command structure
            cmd = args[0]
            assert cmd[0] == "/usr/bin/python3"
            assert cmd[1:4] == ["-m", "pip", "download"]
            assert "--dest" in cmd
            assert "/tmp/wheels" in cmd
            assert "-r" in cmd
            assert str(requirements_file) in cmd

        finally:
            requirements_file.unlink()

    @patch("flavor.packaging.python.pypapip_manager.run")
    def test_build_wheel_from_source(self, mock_run: Mock) -> None:
        """Test building wheel from source directory."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Built wheel: mypackage-1.0.0-py3-none-any.whl"
        mock_run.return_value = mock_result

        python_exe = Path("/usr/bin/python3")
        source_path = Path("/tmp/mypackage")
        wheel_dir = Path("/tmp/wheels")

        self.pip_manager.build_wheel_from_source(python_exe, source_path, wheel_dir)

        # Verify run was called with correct arguments
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args

        cmd = args[0]
        assert cmd[0] == "/usr/bin/python3"
        assert cmd[1:4] == ["-m", "pip", "wheel"]
        assert "--wheel-dir" in cmd
        assert "/tmp/wheels" in cmd
        assert "--no-deps" in cmd  # Default behavior
        assert "/tmp/mypackage" in cmd

        # Verify check=True for error handling
        assert kwargs["check"] is True

    @patch("flavor.packaging.python.pypapip_manager.run")
    def test_install_packages(self, mock_run: Mock) -> None:
        """Test installing packages."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        python_exe = Path("/usr/bin/python3")
        packages = ["requests", "urllib3"]

        self.pip_manager.install_packages(python_exe, packages)

        # Verify run was called
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args

        cmd = args[0]
        expected = ["/usr/bin/python3", "-m", "pip", "install", "requests", "urllib3"]
        assert cmd == expected

        # Verify error handling enabled
        assert kwargs["check"] is True

    def test_empty_package_lists_handled_gracefully(self) -> None:
        """Test that empty package lists are handled without errors."""
        python_exe = Path("/usr/bin/python3")
        dest_dir = Path("/tmp/wheels")

        # These should not raise exceptions and should not call run
        with patch("flavor.packaging.python.pypapip_manager.run") as mock_run:
            self.pip_manager.download_wheels_for_packages(python_exe, [], dest_dir)
            self.pip_manager.install_packages(python_exe, [])

            # Should not have called run for empty lists
            mock_run.assert_not_called()


class TestPyPaPipManagerCriticalFeatures:
    """Test CRITICAL features that must never be broken."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.pip_manager = PyPaPipManager(python_version="3.11")

    def test_manylinux2014_constant_never_changes(self) -> None:
        """CRITICAL: manylinux2014 tag must never change - breaks Linux compatibility."""
        # This test ensures the manylinux tag never accidentally changes
        assert self.pip_manager.MANYLINUX_TAG == "manylinux2014"

        # Verify it's used in Linux platform tags
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
            cmd = self.pip_manager._get_pypapip_download_cmd(
                Path("/usr/bin/python3"), Path("/tmp"), packages=["test"]
            )

            # Must contain manylinux2014_x86_64 for CentOS 7+ compatibility
            assert "manylinux2014_x86_64" in cmd

    @patch("flavor.packaging.python.pypapip_manager.get_os_name")
    @patch("flavor.packaging.python.pypapip_manager.get_arch_name")
    def test_linux_platforms_always_get_manylinux_tags(self, mock_arch: Mock, mock_os: Mock) -> None:
        """CRITICAL: Linux builds must always get manylinux2014 tags."""
        mock_os.return_value = "linux"

        # Test both supported architectures
        # Note: Both use manylinux2014 format for compatibility with published wheels
        for arch, expected_tag in [
            ("amd64", "manylinux2014_x86_64"),
            ("arm64", "manylinux2014_aarch64"),
        ]:
            mock_arch.return_value = arch

            cmd = self.pip_manager._get_pypapip_download_cmd(
                Path("/usr/bin/python3"),
                Path("/tmp"),
                packages=["test"],
                binary_only=True,
            )

            # MUST contain correct platform tag
            assert expected_tag in cmd
            # MUST contain Python version
            assert "--python-version" in cmd
            assert "3.11" in cmd

    def test_method_names_are_debug_resistant(self) -> None:
        """CRITICAL: Method names must be debug-resistant to prevent confusion."""
        # Ensure the critical methods exist with correct names
        assert hasattr(self.pip_manager, "_get_pypapip_install_cmd")
        assert hasattr(self.pip_manager, "_get_pypapip_wheel_cmd")
        assert hasattr(self.pip_manager, "_get_pypapip_download_cmd")

        # Ensure they're callable
        assert callable(self.pip_manager._get_pypapip_install_cmd)
        assert callable(self.pip_manager._get_pypapip_wheel_cmd)
        assert callable(self.pip_manager._get_pypapip_download_cmd)

    def test_never_uses_uv_pip_in_commands(self) -> None:
        """CRITICAL: Commands must NEVER use 'uv pip' - only real pip."""
        python_exe = Path("/usr/bin/python3")
        dest_dir = Path("/tmp")

        # Test all command generation methods
        install_cmd = self.pip_manager._get_pypapip_install_cmd(python_exe, ["test"])
        wheel_cmd = self.pip_manager._get_pypapip_wheel_cmd(python_exe, dest_dir, dest_dir)
        download_cmd = self.pip_manager._get_pypapip_download_cmd(python_exe, dest_dir, packages=["test"])

        # All commands must use "python -m pip", never "uv pip"
        for cmd in [install_cmd, wheel_cmd, download_cmd]:
            assert cmd[1:4] == ["-m", "pip", cmd[3]]  # [python, -m, pip, {command}]
            assert "uv" not in cmd

    def test_binary_only_flag_always_present_for_downloads(self) -> None:
        """CRITICAL: binary-only flag must be present to avoid compilation issues."""
        python_exe = Path("/usr/bin/python3")
        dest_dir = Path("/tmp")

        # Test with packages
        cmd1 = self.pip_manager._get_pypapip_download_cmd(
            python_exe, dest_dir, packages=["test"], binary_only=True
        )
        assert "--only-binary" in cmd1
        assert ":all:" in cmd1

        # Test with requirements file
        cmd2 = self.pip_manager._get_pypapip_download_cmd(
            python_exe,
            dest_dir,
            requirements_file=Path("/tmp/req.txt"),
            binary_only=True,
        )
        assert "--only-binary" in cmd2
        assert ":all:" in cmd2


# 🌶️📦🔚
