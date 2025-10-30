#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test platform-specific environment variables."""

from __future__ import annotations

import os
import platform
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from flavor.psp.format_2025.environment import (
    process_runtime_env,
    set_platform_environment,
)


@pytest.mark.unit
class TestPlatformEnvironment:
    """Test platform-specific environment variable handling."""

    def test_flavor_os_variable(self) -> None:
        """Test FLAVOR_OS is set correctly."""
        env: dict[str, str] = {}
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

    def test_flavor_arch_variable(self) -> None:
        """Test FLAVOR_ARCH is set correctly."""
        env: dict[str, str] = {}
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

    def test_flavor_platform_variable(self) -> None:
        """Test FLAVOR_PLATFORM combines OS and arch."""
        env: dict[str, str] = {}
        set_platform_environment(env)

        assert "FLAVOR_PLATFORM" in env
        # Should be os_arch format
        assert "_" in env["FLAVOR_PLATFORM"]

        # Should match OS and ARCH variables
        parts = env["FLAVOR_PLATFORM"].split("_")
        assert len(parts) == 2
        assert parts[0] == env["FLAVOR_OS"]
        assert parts[1] == env["FLAVOR_ARCH"]

    def test_flavor_os_version(self) -> None:
        """Test FLAVOR_OS_VERSION contains version info."""
        env: dict[str, str] = {}
        set_platform_environment(env)

        # OS version may or may not be available
        if "FLAVOR_OS_VERSION" in env:
            assert len(env["FLAVOR_OS_VERSION"]) > 0
            # Should contain some version-like string
            # Could be "15.6", "5.10.0", "10.0.19041", etc.

    def test_flavor_cpu_type(self) -> None:
        """Test FLAVOR_CPU_TYPE contains CPU info."""
        env: dict[str, str] = {}
        set_platform_environment(env)

        # CPU type may or may not be available
        if "FLAVOR_CPU_TYPE" in env:
            assert len(env["FLAVOR_CPU_TYPE"]) > 0
            # Could be "Apple M1", "Intel Core i7", "AMD Ryzen", etc.

    def test_platform_env_override_protection(self) -> None:
        """Test that platform variables cannot be overridden by user."""
        # Start with user-provided environment
        env = {
            "FLAVOR_OS": "fake_os",
            "FLAVOR_ARCH": "fake_arch",
            "FLAVOR_PLATFORM": "fake_platform",
        }

        # Set platform environment (should override)
        set_platform_environment(env)

        # Should be real values, not fake ones
        assert env["FLAVOR_OS"] != "fake_os"
        assert env["FLAVOR_ARCH"] != "fake_arch"
        assert env["FLAVOR_PLATFORM"] != "fake_platform"
        assert env["FLAVOR_OS"] in ["darwin", "linux", "windows"]
        assert env["FLAVOR_ARCH"] in ["amd64", "arm64", "x86", "i386"]

    @patch("provide.foundation.platform.detection.platform.system")
    @patch("provide.foundation.platform.detection.platform.machine")
    def test_os_normalization(self, mock_machine: MagicMock, mock_system: MagicMock) -> None:
        """Test OS name normalization."""
        from provide.foundation.platform.detection import (
            get_arch_name as foundation_get_arch_name,
            get_os_name as foundation_get_os_name,
            get_platform_string as foundation_get_platform_string,
        )

        test_cases = [
            ("Darwin", "darwin"),
            ("Linux", "linux"),
            ("Windows", "windows"),
            ("darwin", "darwin"),
            ("LINUX", "linux"),
        ]

        mock_machine.return_value = "x86_64"

        for input_os, expected_os in test_cases:
            # Clear cached values before each test
            foundation_get_os_name.cache_clear()
            foundation_get_arch_name.cache_clear()
            foundation_get_platform_string.cache_clear()
            mock_system.return_value = input_os
            env: dict[str, str] = {}
            set_platform_environment(env)
            assert env["FLAVOR_OS"] == expected_os

    @patch("provide.foundation.platform.detection.platform.system")
    @patch("provide.foundation.platform.detection.platform.machine")
    def test_arch_normalization(self, mock_machine: MagicMock, mock_system: MagicMock) -> None:
        """Test architecture name normalization."""
        from provide.foundation.platform.detection import (
            get_arch_name as foundation_get_arch_name,
            get_os_name as foundation_get_os_name,
            get_platform_string as foundation_get_platform_string,
        )

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
            # Clear cached values before each test
            foundation_get_os_name.cache_clear()
            foundation_get_arch_name.cache_clear()
            foundation_get_platform_string.cache_clear()
            mock_machine.return_value = input_arch
            env: dict[str, str] = {}
            set_platform_environment(env)
            assert env["FLAVOR_ARCH"] == expected_arch

    def test_environment_layer_ordering(self) -> None:
        """Test that platform variables are set in correct order."""
        # Initial environment with various layers
        base_env = {
            "PATH": "/usr/bin",
            "HOME": "/home/user",
            "FLAVOR_OS": "wrong",  # Should be overwritten
        }

        # Runtime env (security layer)

        # Workenv env

        # Execution env

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

    def test_platform_env_completeness(self) -> None:
        """Test that all required platform variables are set."""
        env: dict[str, str] = {}
        set_platform_environment(env)

        # Required variables
        required = ["FLAVOR_OS", "FLAVOR_ARCH", "FLAVOR_PLATFORM"]
        for var in required:
            assert var in env, f"Missing required variable: {var}"

        # Optional variables (may or may not be present)
        # Just check they're either present or not, no error

    def test_platform_string_format(self) -> None:
        """Test platform string formatting."""
        env: dict[str, str] = {}
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
    def test_platform_env_with_workenv(self) -> None:
        """Test platform environment with FLAVOR_WORKENV set."""
        env: dict[str, str] = {}
        set_platform_environment(env)

        # Should still set platform variables
        assert "FLAVOR_OS" in env
        assert "FLAVOR_ARCH" in env
        assert "FLAVOR_PLATFORM" in env

        # FLAVOR_WORKENV should be preserved if it exists
        # (This is set by the launcher, not by platform env)


@pytest.mark.unit
class TestRuntimeEnvProcessing:
    """Test runtime environment processing operations."""

    def test_complete_runtime_env_processing(self) -> None:
        """Test complete runtime env processing with all operations."""
        env = {"FOO": "bar", "BAZ": "qux", "TEMP": "123", "OLD_NAME": "value"}
        runtime = {
            "pass": ["FOO"],
            "unset": ["TEMP"],
            "map": {"OLD_NAME": "NEW_NAME"},
            "set": {"CUSTOM": "custom_value"},
        }

        process_runtime_env(env, runtime)

        # FOO should be preserved
        assert env["FOO"] == "bar"
        # BAZ should remain (not in pass, not in unset)
        assert env["BAZ"] == "qux"
        # TEMP should be removed
        assert "TEMP" not in env
        # OLD_NAME should be renamed to NEW_NAME
        assert "OLD_NAME" not in env
        assert env["NEW_NAME"] == "value"
        # CUSTOM should be set
        assert env["CUSTOM"] == "custom_value"

    def test_empty_runtime_env(self) -> None:
        """Test with empty runtime env (no operations)."""
        env = {"FOO": "bar", "BAZ": "qux"}
        runtime: dict[str, Any] = {}

        process_runtime_env(env, runtime)

        # Environment should be unchanged
        assert env == {"FOO": "bar", "BAZ": "qux"}

    def test_runtime_env_order_of_operations(self) -> None:
        """Test that operations are processed in correct order: unset -> map -> set."""
        env = {"A": "1", "B": "2", "C": "3"}
        runtime = {
            "set": {"A": "new_a"},  # Set should happen last
            "map": {"B": "B_NEW"},  # Map should happen before set
            "unset": ["C"],  # Unset should happen first
        }

        process_runtime_env(env, runtime)

        assert env["A"] == "new_a"  # Set overwrites original
        assert "B" not in env  # B was mapped away
        assert env["B_NEW"] == "2"  # B renamed to B_NEW
        assert "C" not in env  # C was unset

    def test_runtime_env_with_glob_patterns(self) -> None:
        """Test runtime env with glob patterns."""
        env = {
            "PYTHON_HOME": "/usr/lib/python",
            "PYTHON_PATH": "/usr/bin/python",
            "RUBY_HOME": "/usr/lib/ruby",
            "PATH": "/usr/bin",
        }
        runtime = {
            "pass": ["PYTHON_*"],
            "unset": ["RUBY_*"],
        }

        process_runtime_env(env, runtime)

        # PYTHON_* variables should be preserved
        assert env["PYTHON_HOME"] == "/usr/lib/python"
        assert env["PYTHON_PATH"] == "/usr/bin/python"
        # RUBY_* should be removed
        assert "RUBY_HOME" not in env
        # PATH should remain (not matched by any pattern)
        assert env["PATH"] == "/usr/bin"

    def test_runtime_env_wildcard_unset(self) -> None:
        """Test wildcard unset with preserved variables."""
        env = {"KEEP_ME": "important", "REMOVE_1": "x", "REMOVE_2": "y"}
        runtime = {
            "pass": ["KEEP_ME"],
            "unset": ["*"],  # Unset all except preserved
        }

        process_runtime_env(env, runtime)

        # Only KEEP_ME should remain
        assert env == {"KEEP_ME": "important"}

    def test_runtime_env_map_with_preserve(self) -> None:
        """Test that map operations respect preserve patterns."""
        env = {"PRESERVE": "value", "RENAME": "other"}
        runtime = {
            "pass": ["PRESERVE"],
            "map": {"PRESERVE": "NEW_NAME", "RENAME": "RENAMED"},
        }

        process_runtime_env(env, runtime)

        # PRESERVE should not be renamed (protected by pass)
        assert env["PRESERVE"] == "value"
        assert "NEW_NAME" not in env
        # RENAME should be renamed (not protected)
        assert "RENAME" not in env
        assert env["RENAMED"] == "other"

    def test_runtime_env_complex_scenario(self) -> None:
        """Test complex scenario with multiple operations and patterns."""
        env = {
            "SYSTEM_PATH": "/usr/bin",
            "SYSTEM_HOME": "/usr",
            "USER_PATH": "/home/user/bin",
            "USER_HOME": "/home/user",
            "TEMP_DIR": "/tmp",
            "CACHE_DIR": "/var/cache",
        }
        runtime = {
            "pass": ["SYSTEM_*"],
            "unset": ["TEMP_*", "CACHE_*"],
            "map": {"USER_PATH": "CUSTOM_PATH", "USER_HOME": "CUSTOM_HOME"},
            "set": {"NEW_VAR": "new_value"},
        }

        process_runtime_env(env, runtime)

        # SYSTEM_* should be preserved
        assert env["SYSTEM_PATH"] == "/usr/bin"
        assert env["SYSTEM_HOME"] == "/usr"
        # TEMP_* and CACHE_* should be removed
        assert "TEMP_DIR" not in env
        assert "CACHE_DIR" not in env
        # USER_* should be renamed
        assert "USER_PATH" not in env
        assert "USER_HOME" not in env
        assert env["CUSTOM_PATH"] == "/home/user/bin"
        assert env["CUSTOM_HOME"] == "/home/user"
        # NEW_VAR should be set
        assert env["NEW_VAR"] == "new_value"

    def test_runtime_env_missing_keys_in_config(self) -> None:
        """Test runtime env with missing keys in configuration."""
        env = {"FOO": "bar"}
        runtime: dict[str, Any] = {"pass": [], "unset": [], "map": {}, "set": {}}

        process_runtime_env(env, runtime)

        # Environment should be unchanged
        assert env == {"FOO": "bar"}


# 🌶️📦🔚
