#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test placeholder substitution for platform variables."""

from pathlib import Path

import pytest

from flavor.psp.metadata.paths import substitute_placeholders


@pytest.mark.unit
class TestPlatformPlaceholders:
    """Test platform-specific placeholder substitution."""

    def test_substitute_workenv_placeholder(self) -> None:
        """Test that {workenv} placeholder is correctly substituted."""
        workenv_path = Path("/test/workenv")

        # Basic workenv substitution
        result = substitute_placeholders("{workenv}/tmp", workenv_path)
        assert result == "/test/workenv/tmp"

        # Multiple workenv references
        result = substitute_placeholders("{workenv}/var/{workenv}/log", workenv_path)
        assert result == "/test/workenv/var//test/workenv/log"

    def test_substitute_os_placeholder(self) -> None:
        """Test that {os} placeholder is correctly substituted."""
        workenv_path = Path("/test/workenv")

        # OS placeholder
        result = substitute_placeholders("{os}", workenv_path)
        # Should be normalized OS name
        assert result in ["darwin", "linux", "windows"]

        # Combined with path
        result = substitute_placeholders("/path/{os}/bin", workenv_path)
        assert "darwin" in result or "linux" in result or "windows" in result

    def test_substitute_arch_placeholder(self) -> None:
        """Test that {arch} placeholder is correctly substituted."""
        workenv_path = Path("/test/workenv")

        # Architecture placeholder
        result = substitute_placeholders("{arch}", workenv_path)
        # Should be normalized architecture
        assert result in ["amd64", "arm64", "x86", "i386"]

        # Combined with path
        result = substitute_placeholders("/path/{arch}/lib", workenv_path)
        assert "amd64" in result or "arm64" in result or "x86" in result

    def test_substitute_platform_placeholder(self) -> None:
        """Test that {platform} placeholder is correctly substituted."""
        workenv_path = Path("/test/workenv")

        # Platform placeholder (os_arch)
        result = substitute_placeholders("{platform}", workenv_path)
        # Should contain an underscore
        assert "_" in result
        # Should contain OS and arch parts
        parts = result.split("_")
        assert len(parts) == 2
        assert parts[0] in ["darwin", "linux", "windows"]
        assert parts[1] in ["amd64", "arm64", "x86", "i386"]

    def test_nested_placeholders(self) -> None:
        """Test nested and combined placeholders."""
        workenv_path = Path("/test/workenv")

        # Complex nested path
        result = substitute_placeholders("{workenv}/{os}/{arch}/bin", workenv_path)
        assert result.startswith("/test/workenv/")
        assert "/bin" in result
        # Should have OS and arch in path
        parts = result.split("/")
        assert len(parts) >= 5  # /test/workenv/os/arch/bin

        # Platform in cache path
        result = substitute_placeholders("{workenv}/cache/{platform}", workenv_path)
        assert result.startswith("/test/workenv/cache/")
        assert "_" in result.split("/")[-1]  # platform should have underscore

    def test_invalid_placeholders(self) -> None:
        """Test that invalid placeholders are left as-is."""
        workenv_path = Path("/test/workenv")

        # Unknown placeholder
        result = substitute_placeholders("{unknown}/path", workenv_path)
        assert result == "{unknown}/path"

        # Malformed placeholder
        result = substitute_placeholders("{not-closed/path", workenv_path)
        assert result == "{not-closed/path"

        # Empty placeholder
        result = substitute_placeholders("{}/path", workenv_path)
        assert result == "{}/path"

    def test_mixed_placeholders(self) -> None:
        """Test mixing valid and invalid placeholders."""
        workenv_path = Path("/test/workenv")

        # Mix of valid and invalid
        result = substitute_placeholders("{workenv}/{unknown}/{os}", workenv_path)
        # workenv and os should be substituted, unknown left as-is
        assert result.startswith("/test/workenv/{unknown}/")
        assert not result.endswith("{os}")

    def test_environment_variable_placeholders(self) -> None:
        """Test placeholders in environment variable values."""
        workenv_path = Path("/test/workenv")

        # Common environment patterns
        env_vars = {
            "TMPDIR": "{workenv}/tmp",
            "XDG_CACHE_HOME": "{workenv}/cache",
            "PLATFORM_CACHE": "{workenv}/cache/{platform}",
            "OS_SPECIFIC": "/opt/{os}/lib",
            "ARCH_BIN": "/usr/local/{arch}/bin",
        }

        for _var, value in env_vars.items():
            result = substitute_placeholders(value, workenv_path)
            # Should not contain unsubstituted valid placeholders
            if "{workenv}" in value:
                assert "{workenv}" not in result
            if "{os}" in value:
                assert "{os}" not in result
            if "{arch}" in value:
                assert "{arch}" not in result
            if "{platform}" in value:
                assert "{platform}" not in result

    def test_windows_path_placeholders(self) -> None:
        """Test placeholders with Windows-style paths."""
        workenv_path = Path("C:\\test\\workenv")

        # Windows paths with placeholders
        result = substitute_placeholders("{workenv}\\tmp", workenv_path)
        # Should handle both forward and backslashes
        assert "test" in result and "workenv" in result and "tmp" in result

        # Mixed separators
        result = substitute_placeholders("{workenv}/cache\\{platform}", workenv_path)
        assert "cache" in result
        assert "_" in result  # platform should have underscore


# 🌶️📦🔚
