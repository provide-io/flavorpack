#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test platform detection utilities."""

import platform
from unittest.mock import MagicMock, patch

import pytest

from flavor.utils import (
    get_arch_name,
    get_cpu_type,
    get_os_name,
    get_os_version,
    get_platform_string,
)


class TestPlatformDetection:
    """Test platform detection utility functions."""

    def test_get_os_name(self) -> None:
        """Test OS name detection and normalization."""
        from provide.foundation.platform.detection import get_os_name as foundation_get_os_name

        # Clear cache to ensure we get fresh values
        foundation_get_os_name.cache_clear()

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

    @patch("provide.foundation.platform.detection.platform.system")
    def test_get_os_name_normalization(self, mock_system: MagicMock) -> None:
        """Test OS name normalization for various inputs."""
        from provide.foundation.platform.detection import get_os_name as foundation_get_os_name

        test_cases = [
            ("Darwin", "darwin"),
            ("Linux", "linux"),
            ("Windows", "windows"),
            ("darwin", "darwin"),
            ("LINUX", "linux"),
            ("MacOS", "darwin"),  # Alternative name
        ]

        for input_os, expected_os in test_cases:
            foundation_get_os_name.cache_clear()  # Clear cached values before each test
            mock_system.return_value = input_os
            assert get_os_name() == expected_os

    def test_get_arch_name(self) -> None:
        """Test architecture detection and normalization."""
        from provide.foundation.platform.detection import get_arch_name as foundation_get_arch_name

        # Clear cache to ensure we get fresh values
        foundation_get_arch_name.cache_clear()

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

    @patch("provide.foundation.platform.detection.platform.machine")
    def test_get_arch_name_normalization(self, mock_machine: MagicMock) -> None:
        """Test architecture normalization for various inputs."""
        from provide.foundation.platform.detection import get_arch_name as foundation_get_arch_name

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
            foundation_get_arch_name.cache_clear()  # Clear cached values before each test
            mock_machine.return_value = input_arch
            assert get_arch_name() == expected_arch

    def test_get_platform_string(self) -> None:
        """Test platform string generation."""
        from provide.foundation.platform.detection import (
            get_arch_name as foundation_get_arch_name,
            get_os_name as foundation_get_os_name,
            get_platform_string as foundation_get_platform_string,
        )

        # Clear cache to ensure we get fresh values
        foundation_get_os_name.cache_clear()
        foundation_get_arch_name.cache_clear()
        foundation_get_platform_string.cache_clear()

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

    @patch("provide.foundation.platform.detection.platform.system")
    @patch("provide.foundation.platform.detection.platform.machine")
    def test_get_platform_string_combinations(self, mock_machine: MagicMock, mock_system: MagicMock) -> None:
        """Test various platform string combinations."""
        from provide.foundation.platform.detection import (
            get_arch_name as foundation_get_arch_name,
            get_os_name as foundation_get_os_name,
            get_platform_string as foundation_get_platform_string,
        )

        test_cases = [
            ("Darwin", "x86_64", "darwin_amd64"),
            ("Darwin", "arm64", "darwin_arm64"),
            ("Linux", "x86_64", "linux_amd64"),
            ("Linux", "aarch64", "linux_arm64"),
            ("Windows", "AMD64", "windows_amd64"),
            ("Windows", "x86", "windows_x86"),
        ]

        for os_name, arch_name, expected_platform in test_cases:
            # Clear all cached values before each test
            foundation_get_os_name.cache_clear()
            foundation_get_arch_name.cache_clear()
            foundation_get_platform_string.cache_clear()
            mock_system.return_value = os_name
            mock_machine.return_value = arch_name
            assert get_platform_string() == expected_platform

    def test_get_os_version(self) -> None:
        """Test OS version detection."""
        version = get_os_version()

        # Version may be None or a string
        if version is not None:
            assert isinstance(version, str)
            assert len(version) > 0

            # Basic validation - should contain numbers
            has_number = any(c.isdigit() for c in version)
            assert has_number, f"Version string should contain numbers: {version}"

    @patch("provide.foundation.platform.detection.platform.system")
    @patch("provide.foundation.platform.detection.platform.release")
    @patch("provide.foundation.platform.detection.platform.version")
    @patch("provide.foundation.platform.detection.platform.mac_ver")
    def test_get_os_version_by_system(
        self,
        mock_mac_ver: MagicMock,
        mock_version: MagicMock,
        mock_release: MagicMock,
        mock_system: MagicMock,
    ) -> None:
        """Test OS version detection for different systems."""
        from provide.foundation.platform.detection import get_os_version as foundation_get_os_version

        # macOS
        foundation_get_os_version.cache_clear()
        mock_system.return_value = "Darwin"
        mock_mac_ver.return_value = ("14.6", "", "")
        mock_release.return_value = "23.6.0"
        mock_version.return_value = "Darwin Kernel Version 23.6.0"

        version = get_os_version()
        assert version is not None
        # Should extract meaningful version (e.g., "14.6" for macOS Sonoma)
        assert version == "14.6"

        # Linux
        foundation_get_os_version.cache_clear()
        mock_system.return_value = "Linux"
        mock_release.return_value = "5.15.0-88-generic"
        mock_version.return_value = "#98-Ubuntu SMP Mon Oct 2 15:18:56 UTC 2023"

        version = get_os_version()
        assert version is not None
        assert "5.15" in version or "5.15.0" in version

        # Windows
        foundation_get_os_version.cache_clear()
        mock_system.return_value = "Windows"
        mock_release.return_value = "10"
        mock_version.return_value = "10.0.19045"

        version = get_os_version()
        assert version is not None
        assert "10" in version

    def test_get_cpu_type(self) -> None:
        """Test CPU information detection."""
        cpu_info = get_cpu_type()

        # CPU info may be None or a string
        if cpu_info is not None:
            assert isinstance(cpu_info, str)
            assert len(cpu_info) > 0

            # Should contain meaningful CPU information
            # Could be "Apple M1", "Intel Core i7", "AMD Ryzen", etc.

    @patch("provide.foundation.platform.detection.platform.processor")
    def test_get_cpu_type_values(self, mock_processor: MagicMock) -> None:
        """Test CPU type detection with known values."""
        from provide.foundation.platform.detection import get_cpu_type as foundation_get_cpu_type

        test_cases = [
            ("Apple M1 Pro", lambda cpu: "Apple" in cpu and "M1" in cpu),
            ("Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz", lambda cpu: "Intel" in cpu and "Core" in cpu),
            ("AMD Ryzen 9 5900X 12-Core Processor", lambda cpu: "AMD" in cpu and "Ryzen" in cpu),
            ("arm", lambda cpu: cpu == "arm"),  # Generic ARM
            ("", lambda cpu: cpu is None or cpu == ""),  # Empty processor info
        ]

        for processor_info, validator in test_cases:
            foundation_get_cpu_type.cache_clear()
            mock_processor.return_value = processor_info
            cpu_type = get_cpu_type()

            if processor_info:
                assert cpu_type is not None
                assert validator(cpu_type), f"Expected validator to pass for {processor_info}, got {cpu_type}"
            else:
                # Empty processor info might return None
                assert cpu_type is None or cpu_type == ""

    def test_platform_consistency(self) -> None:
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

    def test_platform_functions_no_exceptions(self) -> None:
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
            get_os_version()
            get_cpu_type()

        except Exception as e:
            pytest.fail(f"Platform function raised exception: {e}")

    @patch("provide.foundation.platform.detection.platform.system")
    @patch("provide.foundation.platform.detection.platform.machine")
    def test_unknown_platform_handling(self, mock_machine: MagicMock, mock_system: MagicMock) -> None:
        """Test handling of unknown platform values."""
        from provide.foundation.platform.detection import (
            get_arch_name as foundation_get_arch_name,
            get_os_name as foundation_get_os_name,
        )

        # Unknown OS
        foundation_get_os_name.cache_clear()
        mock_system.return_value = "UnknownOS"
        mock_machine.return_value = "x86_64"

        os_name = get_os_name()
        # Should return the lowercase version even if unknown
        assert os_name == "unknownos"

        # Unknown architecture
        foundation_get_arch_name.cache_clear()
        mock_system.return_value = "Linux"
        mock_machine.return_value = "unknown_arch"

        arch_name = get_arch_name()
        # Should return the lowercase version even if unknown
        assert arch_name == "unknown_arch"


# 🌶️📦🔚
