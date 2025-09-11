#
# tests/packaging/python/test_uv_manager.py
#
"""Tests for UVManager UV tool management functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from flavor.packaging.python.uv_manager import UVManager
from provide.foundation.config import BaseConfig
from provide.foundation.tools.base import ToolNotFoundError


class TestUVManager:
    """Test UV manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = BaseConfig()
        self.uv_manager = UVManager(self.config)
    
    def test_initialization(self):
        """Test UVManager initialization."""
        assert self.uv_manager.tool_name == "uv"
        assert self.uv_manager.executable_name == "uv"
        assert self.uv_manager.python_version == "3.11"
        assert self.uv_manager.use_system_uv is True
        
        # Test with None config
        manager_no_config = UVManager()
        assert manager_no_config.config is not None
    
    @patch("platform.machine")
    @patch("platform.system")
    def test_get_metadata_linux_amd64(self, mock_system, mock_machine):
        """Test metadata generation for Linux amd64."""
        mock_system.return_value = "Linux"
        mock_machine.return_value = "x86_64"
        
        metadata = self.uv_manager.get_metadata("0.1.45")
        
        assert metadata.name == "uv"
        assert metadata.version == "0.1.45"
        assert metadata.platform == "linux"
        assert metadata.arch == "amd64"
        assert "x86_64-unknown-linux-gnu" in metadata.download_url
        assert metadata.executable_name == "uv"
    
    @patch("platform.machine")
    @patch("platform.system")
    def test_get_metadata_darwin_arm64(self, mock_system, mock_machine):
        """Test metadata generation for macOS ARM64."""
        mock_system.return_value = "Darwin"
        mock_machine.return_value = "arm64"
        
        metadata = self.uv_manager.get_metadata("0.1.45")
        
        assert metadata.name == "uv"
        assert metadata.version == "0.1.45"
        assert metadata.platform == "darwin"
        assert metadata.arch == "arm64"
        assert "aarch64-apple-darwin" in metadata.download_url
    
    @patch("platform.machine")
    @patch("platform.system")
    def test_get_metadata_windows_amd64(self, mock_system, mock_machine):
        """Test metadata generation for Windows amd64."""
        mock_system.return_value = "Windows"
        mock_machine.return_value = "x86_64"
        
        metadata = self.uv_manager.get_metadata("0.1.45")
        
        assert metadata.name == "uv"
        assert metadata.version == "0.1.45"
        assert metadata.platform == "windows"
        assert metadata.arch == "amd64"
        assert "x86_64-pc-windows-msvc" in metadata.download_url
    
    @patch("platform.machine")
    @patch("platform.system")
    def test_get_metadata_unsupported_platform(self, mock_system, mock_machine):
        """Test error handling for unsupported platforms."""
        mock_system.return_value = "FreeBSD"
        mock_machine.return_value = "x86_64"
        
        with pytest.raises(ToolNotFoundError, match="Unsupported platform: freebsd"):
            self.uv_manager.get_metadata("0.1.45")
    
    @patch("platform.machine")
    @patch("platform.system")
    def test_get_metadata_unsupported_arch(self, mock_system, mock_machine):
        """Test error handling for unsupported architectures."""
        mock_system.return_value = "Linux"
        mock_machine.return_value = "riscv64"
        
        with pytest.raises(ToolNotFoundError, match="Unsupported Linux architecture: riscv64"):
            self.uv_manager.get_metadata("0.1.45")
    
    def test_get_available_versions(self):
        """Test getting available UV versions."""
        versions = self.uv_manager.get_available_versions()
        
        assert isinstance(versions, list)
        assert len(versions) > 0
        assert "0.1.45" in versions
        
        # Versions should be in descending order (newest first)
        for i in range(len(versions) - 1):
            assert versions[i] >= versions[i + 1]
    
    @patch("shutil.which")
    def test_find_system_uv_found(self, mock_which):
        """Test finding system UV when it exists."""
        mock_which.return_value = "/usr/local/bin/uv"
        
        result = self.uv_manager.find_system_uv()
        
        assert result == Path("/usr/local/bin/uv")
        mock_which.assert_called_once_with("uv")
    
    @patch("shutil.which")
    def test_find_system_uv_not_found(self, mock_which):
        """Test finding system UV when it doesn't exist."""
        mock_which.return_value = None
        
        result = self.uv_manager.find_system_uv()
        
        assert result is None
        mock_which.assert_called_once_with("uv")
    
    def test_get_uv_venv_cmd_basic(self):
        """Test UV venv command generation."""
        with patch.object(self.uv_manager, 'get_uv_executable') as mock_get_uv:
            mock_get_uv.return_value = Path("/usr/local/bin/uv")
            
            python_exe = Path("/usr/bin/python3")
            venv_path = Path("/tmp/test_venv")
            
            cmd = self.uv_manager._get_uv_venv_cmd(python_exe, venv_path)
            
            expected = ["/usr/local/bin/uv", "venv", "/tmp/test_venv"]
            assert cmd == expected
    
    def test_get_uv_venv_cmd_with_python_version(self):
        """Test UV venv command with Python version."""
        with patch.object(self.uv_manager, 'get_uv_executable') as mock_get_uv:
            mock_get_uv.return_value = Path("/usr/local/bin/uv")
            
            python_exe = Path("/usr/bin/python3")
            venv_path = Path("/tmp/test_venv")
            
            cmd = self.uv_manager._get_uv_venv_cmd(python_exe, venv_path, "3.11")
            
            expected = ["/usr/local/bin/uv", "venv", "/tmp/test_venv", "--python", "3.11"]
            assert cmd == expected
    
    def test_get_uv_pip_install_cmd_packages(self):
        """Test UV pip install command with packages."""
        with patch.object(self.uv_manager, 'get_uv_executable') as mock_get_uv:
            mock_get_uv.return_value = Path("/usr/local/bin/uv")
            
            venv_python = Path("/tmp/venv/bin/python")
            packages = ["numpy", "scipy"]
            
            cmd = self.uv_manager._get_uv_pip_install_cmd(venv_python, packages)
            
            expected = [
                "/usr/local/bin/uv", "pip", "install", 
                "--python", "/tmp/venv/bin/python",
                "numpy", "scipy"
            ]
            assert cmd == expected
    
    def test_get_uv_pip_install_cmd_requirements_file(self):
        """Test UV pip install command with requirements file."""
        with patch.object(self.uv_manager, 'get_uv_executable') as mock_get_uv:
            mock_get_uv.return_value = Path("/usr/local/bin/uv")
            
            venv_python = Path("/tmp/venv/bin/python")
            requirements_file = Path("/tmp/requirements.txt")
            
            cmd = self.uv_manager._get_uv_pip_install_cmd(venv_python, [], requirements_file)
            
            expected = [
                "/usr/local/bin/uv", "pip", "install", 
                "--python", "/tmp/venv/bin/python",
                "-r", "/tmp/requirements.txt"
            ]
            assert cmd == expected
    
    def test_get_uv_pip_compile_cmd_basic(self):
        """Test UV pip-compile command generation."""
        with patch.object(self.uv_manager, 'get_uv_executable') as mock_get_uv:
            mock_get_uv.return_value = Path("/usr/local/bin/uv")
            
            input_file = Path("/tmp/requirements.in")
            output_file = Path("/tmp/requirements.txt")
            
            cmd = self.uv_manager._get_uv_pip_compile_cmd(input_file, output_file)
            
            expected = [
                "/usr/local/bin/uv", "pip", "compile", 
                "/tmp/requirements.in", "--output-file", "/tmp/requirements.txt",
                "--no-strip-extras"
            ]
            assert cmd == expected
    
    def test_get_uv_pip_compile_cmd_with_python_version(self):
        """Test UV pip-compile command with Python version."""
        with patch.object(self.uv_manager, 'get_uv_executable') as mock_get_uv:
            mock_get_uv.return_value = Path("/usr/local/bin/uv")
            
            input_file = Path("/tmp/requirements.in")
            output_file = Path("/tmp/requirements.txt")
            
            cmd = self.uv_manager._get_uv_pip_compile_cmd(input_file, output_file, "3.11")
            
            expected = [
                "/usr/local/bin/uv", "pip", "compile", 
                "/tmp/requirements.in", "--output-file", "/tmp/requirements.txt",
                "--no-strip-extras",
                "--python-version", "3.11"
            ]
            assert cmd == expected
    
    @patch("flavor.packaging.python.uv_manager.run_command")
    def test_create_venv(self, mock_run_command):
        """Test UV venv creation."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run_command.return_value = mock_result
        
        with patch.object(self.uv_manager, 'get_uv_executable') as mock_get_uv:
            mock_get_uv.return_value = Path("/usr/local/bin/uv")
            
            venv_path = Path("/tmp/test_venv")
            
            self.uv_manager.create_venv(venv_path)
            
            # Verify run_command was called
            mock_run_command.assert_called_once()
            args, kwargs = mock_run_command.call_args
            
            cmd = args[0]
            assert cmd[0] == "/usr/local/bin/uv"
            assert cmd[1] == "venv"
            assert "/tmp/test_venv" in cmd
            
            # Verify error handling enabled
            assert kwargs["check"] is True
    
    @patch("flavor.packaging.python.uv_manager.run_command")
    def test_install_packages_fast(self, mock_run_command):
        """Test UV fast package installation."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run_command.return_value = mock_result
        
        with patch.object(self.uv_manager, 'get_uv_executable') as mock_get_uv:
            mock_get_uv.return_value = Path("/usr/local/bin/uv")
            
            venv_python = Path("/tmp/venv/bin/python")
            packages = ["requests", "click"]
            
            self.uv_manager.install_packages_fast(venv_python, packages)
            
            # Verify run_command was called
            mock_run_command.assert_called_once()
            args, kwargs = mock_run_command.call_args
            
            cmd = args[0]
            assert cmd[0] == "/usr/local/bin/uv"
            assert cmd[1:3] == ["pip", "install"]
            assert "--python" in cmd
            assert "requests" in cmd
            assert "click" in cmd
            
            # Verify error handling enabled
            assert kwargs["check"] is True
    
    @patch("flavor.packaging.python.uv_manager.run_command")
    def test_compile_requirements(self, mock_run_command):
        """Test UV requirements compilation."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run_command.return_value = mock_result
        
        with patch.object(self.uv_manager, 'get_uv_executable') as mock_get_uv:
            mock_get_uv.return_value = Path("/usr/local/bin/uv")
            
            input_file = Path("/tmp/requirements.in")
            output_file = Path("/tmp/requirements.txt")
            
            self.uv_manager.compile_requirements(input_file, output_file)
            
            # Verify run_command was called
            mock_run_command.assert_called_once()
            args, kwargs = mock_run_command.call_args
            
            cmd = args[0]
            assert cmd[0] == "/usr/local/bin/uv"
            assert cmd[1:3] == ["pip", "compile"]
            assert "/tmp/requirements.in" in cmd
            assert "--output-file" in cmd
            assert "/tmp/requirements.txt" in cmd
            
            # Verify error handling enabled
            assert kwargs["check"] is True
    
    def test_empty_package_lists_handled_gracefully(self):
        """Test that empty package lists are handled without errors."""
        venv_python = Path("/tmp/venv/bin/python")
        
        # Should not raise exceptions and should not call run_command
        with patch("flavor.packaging.python.uv_manager.run_command") as mock_run:
            self.uv_manager.install_packages_fast(venv_python, [])
            
            # Should not have called run_command for empty lists
            mock_run.assert_not_called()


class TestUVManagerCriticalFeatures:
    """Test CRITICAL features that must never be broken."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.uv_manager = UVManager()
    
    def test_tool_manager_inheritance(self):
        """CRITICAL: UVManager must properly extend BaseToolManager."""
        from provide.foundation.tools.base import BaseToolManager
        
        assert isinstance(self.uv_manager, BaseToolManager)
        assert hasattr(self.uv_manager, 'install')
        assert hasattr(self.uv_manager, 'uninstall')
        assert hasattr(self.uv_manager, 'get_metadata')
        assert hasattr(self.uv_manager, 'get_available_versions')
    
    def test_method_names_are_debug_resistant(self):
        """CRITICAL: Method names must be debug-resistant to prevent confusion."""
        # Ensure the critical methods exist with correct names
        assert hasattr(self.uv_manager, '_get_uv_venv_cmd')
        assert hasattr(self.uv_manager, '_get_uv_pip_install_cmd')
        assert hasattr(self.uv_manager, '_get_uv_pip_compile_cmd')
        
        # Ensure they're callable
        assert callable(self.uv_manager._get_uv_venv_cmd)
        assert callable(self.uv_manager._get_uv_pip_install_cmd)
        assert callable(self.uv_manager._get_uv_pip_compile_cmd)
    
    def test_never_replaces_pip_commands(self):
        """CRITICAL: UV methods must be clearly separate from pip methods."""
        # UV methods should have UV prefix to avoid confusion with pip methods
        assert not hasattr(self.uv_manager, '_get_pip_install_cmd')
        assert not hasattr(self.uv_manager, '_get_pip_wheel_cmd')
        assert not hasattr(self.uv_manager, '_get_pip_download_cmd')
        
        # All UV methods should be clearly prefixed
        uv_methods = [method for method in dir(self.uv_manager) if method.startswith('_get_uv_')]
        assert len(uv_methods) >= 3  # At least the three core methods
        
        for method in uv_methods:
            assert 'uv' in method.lower()
    
    def test_system_uv_preference_configurable(self):
        """CRITICAL: System UV preference must be configurable."""
        assert hasattr(self.uv_manager, 'use_system_uv')
        assert isinstance(self.uv_manager.use_system_uv, bool)
        
        # Should be able to toggle system UV preference
        original_value = self.uv_manager.use_system_uv
        self.uv_manager.use_system_uv = not original_value
        assert self.uv_manager.use_system_uv != original_value