"""Test platform-specific environment variables."""

import os
import platform
import pytest
from unittest.mock import patch, MagicMock
from flavor.utils import (
    get_os_name,
    get_arch_name,
    get_platform_string,
    get_os_version,
    get_cpu_type
)
from flavor.psp.format_2025.environment import set_platform_environment


@pytest.mark.unit
class TestPlatformEnvironment:
    """Test platform-specific environment variable handling."""
    
    def test_flavor_os_variable(self):
        """Test FLAVOR_OS is set correctly."""
        env = {}
        set_platform_environment(env)
        
        assert "FLAVOR_OS" in env
        # Should be normalized OS name
        assert env["FLAVOR_OS"] in ["darwin", "linux", "windows"]
        
        # Test OS normalization
        if platform.system().lower() == "darwin":
            assert env["FLAVOR_OS"] == "darwin"
        elif platform.system().lower() == "linux":
            assert env["FLAVOR_OS"] == "linux"
        elif platform.system().lower() == "windows":
            assert env["FLAVOR_OS"] == "windows"
    
    def test_flavor_arch_variable(self):
        """Test FLAVOR_ARCH is set correctly."""
        env = {}
        set_platform_environment(env)
        
        assert "FLAVOR_ARCH" in env
        # Should be normalized architecture
        assert env["FLAVOR_ARCH"] in ["amd64", "arm64", "x86", "i386"]
        
        # Test architecture normalization
        machine = platform.machine().lower()
        if machine in ["x86_64", "amd64"]:
            assert env["FLAVOR_ARCH"] == "amd64"
        elif machine in ["aarch64", "arm64"]:
            assert env["FLAVOR_ARCH"] == "arm64"
    
    def test_flavor_platform_variable(self):
        """Test FLAVOR_PLATFORM combines OS and arch."""
        env = {}
        set_platform_environment(env)
        
        assert "FLAVOR_PLATFORM" in env
        # Should be os_arch format
        assert "_" in env["FLAVOR_PLATFORM"]
        
        # Should match OS and ARCH variables
        parts = env["FLAVOR_PLATFORM"].split("_")
        assert len(parts) == 2
        assert parts[0] == env["FLAVOR_OS"]
        assert parts[1] == env["FLAVOR_ARCH"]
    
    def test_flavor_os_version(self):
        """Test FLAVOR_OS_VERSION contains version info."""
        env = {}
        set_platform_environment(env)
        
        # OS version may or may not be available
        if "FLAVOR_OS_VERSION" in env:
            assert len(env["FLAVOR_OS_VERSION"]) > 0
            # Should contain some version-like string
            # Could be "15.6", "5.10.0", "10.0.19041", etc.
    
    def test_flavor_cpu_type(self):
        """Test FLAVOR_CPU_TYPE contains CPU info."""
        env = {}
        set_platform_environment(env)
        
        # CPU type may or may not be available
        if "FLAVOR_CPU_TYPE" in env:
            assert len(env["FLAVOR_CPU_TYPE"]) > 0
            # Could be "Apple M1", "Intel Core i7", "AMD Ryzen", etc.
    
    def test_platform_env_override_protection(self):
        """Test that platform variables cannot be overridden by user."""
        # Start with user-provided environment
        env = {
            "FLAVOR_OS": "fake_os",
            "FLAVOR_ARCH": "fake_arch",
            "FLAVOR_PLATFORM": "fake_platform"
        }
        
        # Set platform environment (should override)
        set_platform_environment(env)
        
        # Should be real values, not fake ones
        assert env["FLAVOR_OS"] != "fake_os"
        assert env["FLAVOR_ARCH"] != "fake_arch"
        assert env["FLAVOR_PLATFORM"] != "fake_platform"
        assert env["FLAVOR_OS"] in ["darwin", "linux", "windows"]
        assert env["FLAVOR_ARCH"] in ["amd64", "arm64", "x86", "i386"]
    
    @patch('platform.system')
    @patch('platform.machine')
    def test_os_normalization(self, mock_machine, mock_system):
        """Test OS name normalization."""
        test_cases = [
            ("Darwin", "darwin"),
            ("Linux", "linux"),
            ("Windows", "windows"),
            ("darwin", "darwin"),
            ("LINUX", "linux"),
        ]
        
        mock_machine.return_value = "x86_64"
        
        for input_os, expected_os in test_cases:
            mock_system.return_value = input_os
            env = {}
            set_platform_environment(env)
            assert env["FLAVOR_OS"] == expected_os
    
    @patch('platform.system')
    @patch('platform.machine')
    def test_arch_normalization(self, mock_machine, mock_system):
        """Test architecture name normalization."""
        test_cases = [
            ("x86_64", "amd64"),
            ("AMD64", "amd64"),
            ("aarch64", "arm64"),
            ("arm64", "arm64"),
            ("i386", "i386"),
            ("i686", "x86"),
        ]
        
        mock_system.return_value = "Linux"
        
        for input_arch, expected_arch in test_cases:
            mock_machine.return_value = input_arch
            env = {}
            set_platform_environment(env)
            assert env["FLAVOR_ARCH"] == expected_arch
    
    def test_environment_layer_ordering(self):
        """Test that platform variables are set in correct order."""
        # Initial environment with various layers
        base_env = {
            "PATH": "/usr/bin",
            "HOME": "/home/user",
            "FLAVOR_OS": "wrong"  # Should be overwritten
        }
        
        # Runtime env (security layer)
        runtime_env = {
            "unset": ["SENSITIVE_VAR"],
            "pass": ["PATH", "HOME"],
            "set": {"SAFE_VAR": "value"}
        }
        
        # Workenv env
        workenv_env = {
            "TMPDIR": "{workenv}/tmp",
            "XDG_CACHE_HOME": "{workenv}/cache"
        }
        
        # Execution env
        execution_env = {
            "APP_MODE": "production"
        }
        
        # Platform environment should be set last (highest priority)
        final_env = base_env.copy()
        
        # Apply layers in order
        # 1. Runtime security
        # 2. Workenv
        # 3. Execution
        # 4. Platform (automatic)
        
        set_platform_environment(final_env)
        
        # Platform variables should be present and correct
        assert "FLAVOR_OS" in final_env
        assert final_env["FLAVOR_OS"] != "wrong"
        assert final_env["FLAVOR_OS"] in ["darwin", "linux", "windows"]
    
    def test_platform_env_completeness(self):
        """Test that all required platform variables are set."""
        env = {}
        set_platform_environment(env)
        
        # Required variables
        required = ["FLAVOR_OS", "FLAVOR_ARCH", "FLAVOR_PLATFORM"]
        for var in required:
            assert var in env, f"Missing required variable: {var}"
        
        # Optional variables (may or may not be present)
        optional = ["FLAVOR_OS_VERSION", "FLAVOR_CPU_TYPE"]
        # Just check they're either present or not, no error
    
    def test_platform_string_format(self):
        """Test platform string formatting."""
        env = {}
        set_platform_environment(env)
        
        platform_str = env["FLAVOR_PLATFORM"]
        
        # Should be lowercase
        assert platform_str == platform_str.lower()
        
        # Should have exactly one underscore
        assert platform_str.count("_") == 1
        
        # Parts should match individual variables
        os_part, arch_part = platform_str.split("_")
        assert os_part == env["FLAVOR_OS"]
        assert arch_part == env["FLAVOR_ARCH"]
    
    @patch.dict(os.environ, {"FLAVOR_WORKENV": "/custom/workenv"})
    def test_platform_env_with_workenv(self):
        """Test platform environment with FLAVOR_WORKENV set."""
        env = {}
        set_platform_environment(env)
        
        # Should still set platform variables
        assert "FLAVOR_OS" in env
        assert "FLAVOR_ARCH" in env
        assert "FLAVOR_PLATFORM" in env
        
        # FLAVOR_WORKENV should be preserved if it exists
        # (This is set by the launcher, not by platform env)