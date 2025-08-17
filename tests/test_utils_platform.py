"""Test platform detection utilities."""

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


class TestPlatformDetection:
    """Test platform detection utility functions."""
    
    def test_get_os_name(self):
        """Test OS name detection and normalization."""
        os_name = get_os_name()
        
        # Should return normalized names
        assert os_name in ["darwin", "linux", "windows"]
        
        # Should match system platform
        system = platform.system().lower()
        if system == "darwin":
            assert os_name == "darwin"
        elif system == "linux":
            assert os_name == "linux"
        elif system == "windows":
            assert os_name == "windows"
    
    @patch('platform.system')
    def test_get_os_name_normalization(self, mock_system):
        """Test OS name normalization for various inputs."""
        test_cases = [
            ("Darwin", "darwin"),
            ("Linux", "linux"),
            ("Windows", "windows"),
            ("darwin", "darwin"),
            ("LINUX", "linux")
        ]
        
        for input_os, expected_os in test_cases:
            mock_system.return_value = input_os
            assert get_os_name() == expected_os
    
    def test_get_arch_name(self):
        """Test architecture detection and normalization."""
        arch_name = get_arch_name()
        
        # Should return normalized architecture names
        assert arch_name in ["amd64", "arm64", "x86", "i386"]
        
        # Check consistency with platform
        machine = platform.machine().lower()
        if machine in ["x86_64", "amd64"]:
            assert arch_name == "amd64"
        elif machine in ["aarch64", "arm64"]:
            assert arch_name == "arm64"
        elif machine == "i386":
            assert arch_name == "i386"
        elif machine in ["i686", "i586", "i486"]:
            assert arch_name == "x86"
    
    @patch('platform.machine')
    def test_get_arch_name_normalization(self, mock_machine):
        """Test architecture normalization for various inputs."""
        test_cases = [
            ("x86_64", "amd64"),
            ("AMD64", "amd64"),
            ("amd64", "amd64"),
            ("aarch64", "arm64"),
            ("arm64", "arm64"),
            ("ARM64", "arm64"),
            ("i386", "i386"),
            ("i686", "x86"),
            ("i586", "x86"),
            ("i486", "x86"),
        ]
        
        for input_arch, expected_arch in test_cases:
            mock_machine.return_value = input_arch
            assert get_arch_name() == expected_arch
    
    def test_get_platform_string(self):
        """Test platform string generation."""
        platform_str = get_platform_string()
        
        # Should be os_arch format
        assert "_" in platform_str
        
        # Should be lowercase
        assert platform_str == platform_str.lower()
        
        # Should match individual components
        parts = platform_str.split("_")
        assert len(parts) == 2
        assert parts[0] == get_os_name()
        assert parts[1] == get_arch_name()
    
    @patch('platform.system')
    @patch('platform.machine')
    def test_get_platform_string_combinations(self, mock_machine, mock_system):
        """Test various platform string combinations."""
        test_cases = [
            ("Darwin", "x86_64", "darwin_amd64"),
            ("Darwin", "arm64", "darwin_arm64"),
            ("Linux", "x86_64", "linux_amd64"),
            ("Linux", "aarch64", "linux_arm64"),
            ("Windows", "AMD64", "windows_amd64"),
            ("Windows", "x86", "windows_x86"),
        ]
        
        for os_name, arch_name, expected_platform in test_cases:
            mock_system.return_value = os_name
            mock_machine.return_value = arch_name
            assert get_platform_string() == expected_platform
    
    def test_get_os_version(self):
        """Test OS version detection."""
        version = get_os_version()
        
        # Version may be None or a string
        if version is not None:
            assert isinstance(version, str)
            assert len(version) > 0
            
            # Basic validation - should contain numbers
            has_number = any(c.isdigit() for c in version)
            assert has_number, f"Version string should contain numbers: {version}"
    
    @patch('platform.system')
    @patch('platform.release')
    @patch('platform.version')
    def test_get_os_version_by_system(self, mock_version, mock_release, mock_system):
        """Test OS version detection for different systems."""
        # macOS
        mock_system.return_value = "Darwin"
        mock_release.return_value = "23.6.0"
        mock_version.return_value = "Darwin Kernel Version 23.6.0"
        
        version = get_os_version()
        assert version is not None
        # Should extract meaningful version (e.g., "14.6" for macOS Sonoma)
        
        # Linux
        mock_system.return_value = "Linux"
        mock_release.return_value = "5.15.0-88-generic"
        mock_version.return_value = "#98-Ubuntu SMP Mon Oct 2 15:18:56 UTC 2023"
        
        version = get_os_version()
        assert version is not None
        assert "5.15" in version or "5.15.0" in version
        
        # Windows
        mock_system.return_value = "Windows"
        mock_release.return_value = "10"
        mock_version.return_value = "10.0.19045"
        
        version = get_os_version()
        assert version is not None
        assert "10" in version
    
    def test_get_cpu_type(self):
        """Test CPU information detection."""
        cpu_info = get_cpu_type()
        
        # CPU info may be None or a string
        if cpu_info is not None:
            assert isinstance(cpu_info, str)
            assert len(cpu_info) > 0
            
            # Should contain meaningful CPU information
            # Could be "Apple M1", "Intel Core i7", "AMD Ryzen", etc.
    
    @patch('platform.processor')
    def test_get_cpu_type_values(self, mock_processor):
        """Test CPU type detection with known values."""
        test_cases = [
            "Apple M1 Pro",
            "Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz",
            "AMD Ryzen 9 5900X 12-Core Processor",
            "arm",  # Generic ARM
            "",  # Empty processor info
        ]
        
        for processor_info in test_cases:
            mock_processor.return_value = processor_info
            cpu_type = get_cpu_type()
            
            if processor_info:
                assert cpu_type is not None
                # Should clean up the processor string
                if "Intel" in processor_info:
                    assert "Intel" in cpu_type or "Core" in cpu_type
                elif "AMD" in processor_info:
                    assert "AMD" in cpu_type or "Ryzen" in cpu_type
                elif "Apple" in processor_info:
                    assert "Apple" in cpu_type or "M1" in cpu_type
            else:
                # Empty processor info might return None
                assert cpu_type is None or cpu_type == ""
    
    def test_platform_consistency(self):
        """Test that all platform functions return consistent results."""
        # Get all values
        os_name = get_os_name()
        arch_name = get_arch_name()
        platform_str = get_platform_string()
        
        # Platform string should combine OS and arch
        assert platform_str == f"{os_name}_{arch_name}"
        
        # Multiple calls should return same results
        assert get_os_name() == os_name
        assert get_arch_name() == arch_name
        assert get_platform_string() == platform_str
    
    def test_platform_functions_no_exceptions(self):
        """Test that platform functions handle errors gracefully."""
        # All functions should work without raising exceptions
        try:
            os_name = get_os_name()
            assert os_name is not None
            
            arch_name = get_arch_name()
            assert arch_name is not None
            
            platform_str = get_platform_string()
            assert platform_str is not None
            
            # These may return None but shouldn't raise
            os_version = get_os_version()
            cpu_type = get_cpu_type()
            
        except Exception as e:
            pytest.fail(f"Platform function raised exception: {e}")
    
    @patch('platform.system')
    @patch('platform.machine')
    def test_unknown_platform_handling(self, mock_machine, mock_system):
        """Test handling of unknown platform values."""
        # Unknown OS
        mock_system.return_value = "UnknownOS"
        mock_machine.return_value = "x86_64"
        
        os_name = get_os_name()
        # Should return the lowercase version even if unknown
        assert os_name == "unknownos"
        
        # Unknown architecture
        mock_system.return_value = "Linux"
        mock_machine.return_value = "unknown_arch"
        
        arch_name = get_arch_name()
        # Should return the lowercase version even if unknown
        assert arch_name == "unknown_arch"