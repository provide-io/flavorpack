"""Test platform-specific environment variables."""

import os
import platform
from unittest.mock import patch

import pytest

from flavor.psp.format_2025.environment import (
    apply_environment_layers,
    process_runtime_env,
    set_platform_environment,
)


@pytest.mark.unit
class TestPlatformEnvironment:
    """Test platform-specific environment variable handling."""

    def test_flavor_os_variable(self) -> None:
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

    def test_flavor_arch_variable(self) -> None:
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

    def test_flavor_platform_variable(self) -> None:
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

    def test_flavor_os_version(self) -> None:
        """Test FLAVOR_OS_VERSION contains version info."""
        env = {}
        set_platform_environment(env)

        # OS version may or may not be available
        if "FLAVOR_OS_VERSION" in env:
            assert len(env["FLAVOR_OS_VERSION"]) > 0
            # Should contain some version-like string
            # Could be "15.6", "5.10.0", "10.0.19041", etc.

    def test_flavor_cpu_type(self) -> None:
        """Test FLAVOR_CPU_TYPE contains CPU info."""
        env = {}
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
    def test_os_normalization(self, mock_machine, mock_system) -> None:
        """Test OS name normalization."""
        from provide.foundation.platform.detection import (
            get_os_name as foundation_get_os_name,
            get_arch_name as foundation_get_arch_name,
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
            env = {}
            set_platform_environment(env)
            assert env["FLAVOR_OS"] == expected_os

    @patch("provide.foundation.platform.detection.platform.system")
    @patch("provide.foundation.platform.detection.platform.machine")
    def test_arch_normalization(self, mock_machine, mock_system) -> None:
        """Test architecture name normalization."""
        from provide.foundation.platform.detection import (
            get_os_name as foundation_get_os_name,
            get_arch_name as foundation_get_arch_name,
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
            env = {}
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
        env = {}
        set_platform_environment(env)

        # Required variables
        required = ["FLAVOR_OS", "FLAVOR_ARCH", "FLAVOR_PLATFORM"]
        for var in required:
            assert var in env, f"Missing required variable: {var}"

        # Optional variables (may or may not be present)
        # Just check they're either present or not, no error

    def test_platform_string_format(self) -> None:
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
    def test_platform_env_with_workenv(self) -> None:
        """Test platform environment with FLAVOR_WORKENV set."""
        env = {}
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
        runtime = {}

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
        runtime = {"pass": [], "unset": [], "map": {}, "set": {}}

        process_runtime_env(env, runtime)

        # Environment should be unchanged
        assert env == {"FOO": "bar"}


@pytest.mark.unit
class TestPreservePatterns:
    """Test preserve pattern matching functionality."""

    def test_exact_match_preservation(self) -> None:
        """Test exact match pattern preservation."""
        env = {"EXACT": "value", "OTHER": "other"}
        runtime = {"pass": ["EXACT"], "unset": ["*"]}

        process_runtime_env(env, runtime)

        assert env == {"EXACT": "value"}

    def test_glob_pattern_matching(self) -> None:
        """Test glob pattern matching."""
        env = {
            "PYTHON_HOME": "1",
            "PYTHON_PATH": "2",
            "PYTHON_VERSION": "3",
            "RUBY_HOME": "4",
        }
        runtime = {"pass": ["PYTHON_*"], "unset": ["*"]}

        process_runtime_env(env, runtime)

        assert "PYTHON_HOME" in env
        assert "PYTHON_PATH" in env
        assert "PYTHON_VERSION" in env
        assert "RUBY_HOME" not in env

    def test_wildcard_matches_all(self) -> None:
        """Test wildcard * matches all variables."""
        env = {"A": "1", "B": "2", "C": "3"}
        runtime = {"pass": ["*"], "unset": ["*"]}

        process_runtime_env(env, runtime)

        # All variables should be preserved (pass has higher priority)
        assert env == {"A": "1", "B": "2", "C": "3"}

    def test_multiple_patterns(self) -> None:
        """Test multiple preserve patterns."""
        env = {"KEEP_A": "a", "KEEP_B": "b", "PYTHON_X": "x", "REMOVE": "r"}
        runtime = {"pass": ["KEEP_*", "PYTHON_*"], "unset": ["*"]}

        process_runtime_env(env, runtime)

        assert "KEEP_A" in env
        assert "KEEP_B" in env
        assert "PYTHON_X" in env
        assert "REMOVE" not in env

    def test_no_matches_empty_list(self) -> None:
        """Test with empty pass list (no preservation)."""
        env = {"A": "1", "B": "2"}
        runtime = {"pass": [], "unset": ["*"]}

        process_runtime_env(env, runtime)

        # All should be removed
        assert env == {}

    def test_mixed_exact_and_glob(self) -> None:
        """Test mixed exact and glob patterns."""
        env = {"EXACT": "e", "GLOB_A": "ga", "GLOB_B": "gb", "OTHER": "o"}
        runtime = {"pass": ["EXACT", "GLOB_*"], "unset": ["*"]}

        process_runtime_env(env, runtime)

        assert env == {"EXACT": "e", "GLOB_A": "ga", "GLOB_B": "gb"}


@pytest.mark.unit
class TestUnsetOperations:
    """Test unset operations for environment variables."""

    def test_unset_exact_match(self) -> None:
        """Test unsetting exact variable match."""
        env = {"REMOVE": "value", "KEEP": "keep"}
        runtime = {"unset": ["REMOVE"]}

        process_runtime_env(env, runtime)

        assert "REMOVE" not in env
        assert env["KEEP"] == "keep"

    def test_unset_glob_pattern(self) -> None:
        """Test unsetting variables with glob pattern."""
        env = {"TEMP_A": "a", "TEMP_B": "b", "KEEP": "keep"}
        runtime = {"unset": ["TEMP_*"]}

        process_runtime_env(env, runtime)

        assert "TEMP_A" not in env
        assert "TEMP_B" not in env
        assert env["KEEP"] == "keep"

    def test_unset_wildcard_all(self) -> None:
        """Test unsetting all variables with wildcard."""
        env = {"A": "1", "B": "2", "C": "3"}
        runtime = {"unset": ["*"]}

        process_runtime_env(env, runtime)

        assert env == {}

    def test_unset_with_preserve_protection(self) -> None:
        """Test that unset respects preserve protection."""
        env = {"PROTECT": "protected", "REMOVE": "removed"}
        runtime = {"pass": ["PROTECT"], "unset": ["*"]}

        process_runtime_env(env, runtime)

        assert env == {"PROTECT": "protected"}

    def test_unset_nonexistent_variable(self) -> None:
        """Test unsetting non-existent variable (no-op)."""
        env = {"KEEP": "keep"}
        runtime = {"unset": ["NONEXISTENT"]}

        process_runtime_env(env, runtime)

        assert env == {"KEEP": "keep"}

    def test_multiple_unset_operations(self) -> None:
        """Test multiple unset operations."""
        env = {"A": "1", "B": "2", "C": "3", "D": "4"}
        runtime = {"unset": ["A", "C"]}

        process_runtime_env(env, runtime)

        assert env == {"B": "2", "D": "4"}

    def test_empty_unset_list(self) -> None:
        """Test with empty unset list (no-op)."""
        env = {"A": "1", "B": "2"}
        runtime = {"unset": []}

        process_runtime_env(env, runtime)

        assert env == {"A": "1", "B": "2"}

    def test_unset_glob_question_mark(self) -> None:
        """Test unset with ? wildcard (single character)."""
        env = {"FILE_A": "a", "FILE_B": "b", "FILE_ABC": "abc", "KEEP": "keep"}
        runtime = {"unset": ["FILE_?"]}

        process_runtime_env(env, runtime)

        # FILE_A and FILE_B match FILE_? (single char after FILE_)
        assert "FILE_A" not in env
        assert "FILE_B" not in env
        # FILE_ABC doesn't match FILE_? (multiple chars)
        assert env["FILE_ABC"] == "abc"
        assert env["KEEP"] == "keep"


@pytest.mark.unit
class TestMapOperations:
    """Test map operations for variable renaming."""

    def test_map_single_variable(self) -> None:
        """Test mapping a single variable."""
        env = {"OLD": "value", "KEEP": "keep"}
        runtime = {"map": {"OLD": "NEW"}}

        process_runtime_env(env, runtime)

        assert "OLD" not in env
        assert env["NEW"] == "value"
        assert env["KEEP"] == "keep"

    def test_map_multiple_variables(self) -> None:
        """Test mapping multiple variables."""
        env = {"OLD_A": "a", "OLD_B": "b", "KEEP": "keep"}
        runtime = {"map": {"OLD_A": "NEW_A", "OLD_B": "NEW_B"}}

        process_runtime_env(env, runtime)

        assert "OLD_A" not in env
        assert "OLD_B" not in env
        assert env["NEW_A"] == "a"
        assert env["NEW_B"] == "b"
        assert env["KEEP"] == "keep"

    def test_map_with_preserve_protection(self) -> None:
        """Test that map operations respect preserve protection."""
        env = {"PROTECTED": "protected", "RENAME": "rename"}
        runtime = {"pass": ["PROTECTED"], "map": {"PROTECTED": "NEW", "RENAME": "RENAMED"}}

        process_runtime_env(env, runtime)

        # PROTECTED should not be renamed
        assert env["PROTECTED"] == "protected"
        assert "NEW" not in env
        # RENAME should be renamed
        assert "RENAME" not in env
        assert env["RENAMED"] == "rename"

    def test_map_nonexistent_variable(self) -> None:
        """Test mapping non-existent variable (no-op)."""
        env = {"KEEP": "keep"}
        runtime = {"map": {"NONEXISTENT": "NEW"}}

        process_runtime_env(env, runtime)

        assert env == {"KEEP": "keep"}
        assert "NEW" not in env

    def test_map_to_existing_variable(self) -> None:
        """Test mapping to existing variable name (override)."""
        env = {"OLD": "old_value", "EXISTING": "existing_value"}
        runtime = {"map": {"OLD": "EXISTING"}}

        process_runtime_env(env, runtime)

        # OLD should be removed, EXISTING should have OLD's value
        assert "OLD" not in env
        assert env["EXISTING"] == "old_value"

    def test_empty_map_dict(self) -> None:
        """Test with empty map dict (no-op)."""
        env = {"A": "1", "B": "2"}
        runtime = {"map": {}}

        process_runtime_env(env, runtime)

        assert env == {"A": "1", "B": "2"}


@pytest.mark.unit
class TestSetOperations:
    """Test set operations for environment variables."""

    def test_set_new_variable(self) -> None:
        """Test setting a new variable."""
        env = {"EXISTING": "existing"}
        runtime = {"set": {"NEW": "new_value"}}

        process_runtime_env(env, runtime)

        assert env["EXISTING"] == "existing"
        assert env["NEW"] == "new_value"

    def test_override_existing_variable(self) -> None:
        """Test overriding an existing variable."""
        env = {"VAR": "old_value"}
        runtime = {"set": {"VAR": "new_value"}}

        process_runtime_env(env, runtime)

        assert env["VAR"] == "new_value"

    def test_set_multiple_variables(self) -> None:
        """Test setting multiple variables."""
        env = {}
        runtime = {"set": {"A": "1", "B": "2", "C": "3"}}

        process_runtime_env(env, runtime)

        assert env == {"A": "1", "B": "2", "C": "3"}

    def test_empty_set_dict(self) -> None:
        """Test with empty set dict (no-op)."""
        env = {"A": "1", "B": "2"}
        runtime = {"set": {}}

        process_runtime_env(env, runtime)

        assert env == {"A": "1", "B": "2"}


@pytest.mark.unit
class TestPassVerification:
    """Test pass requirement verification."""

    def test_required_exact_match_exists(self) -> None:
        """Test required exact match exists (no warning)."""
        env = {"REQUIRED": "value"}
        runtime = {"pass": ["REQUIRED"]}

        # Should not raise, just process
        process_runtime_env(env, runtime)

        assert env["REQUIRED"] == "value"

    def test_required_exact_match_missing(self) -> None:
        """Test required exact match missing (warning logged)."""
        env = {"OTHER": "value"}
        runtime = {"pass": ["REQUIRED"]}

        # Should log warning but not raise
        process_runtime_env(env, runtime)

        assert "REQUIRED" not in env
        assert env["OTHER"] == "value"

    def test_glob_patterns_not_checked_as_requirements(self) -> None:
        """Test that glob patterns are not checked as requirements."""
        env = {"OTHER": "value"}
        runtime = {"pass": ["PYTHON_*"]}

        # Glob patterns don't generate warnings, they're for filtering
        process_runtime_env(env, runtime)

        # No error, just continues
        assert env == {"OTHER": "value"}

    def test_multiple_requirements(self) -> None:
        """Test multiple required variables."""
        env = {"REQ_A": "a", "REQ_B": "b"}
        runtime = {"pass": ["REQ_A", "REQ_B", "REQ_C"]}

        # Should warn about REQ_C but not raise
        process_runtime_env(env, runtime)

        assert env["REQ_A"] == "a"
        assert env["REQ_B"] == "b"
        assert "REQ_C" not in env

    def test_empty_pass_list(self) -> None:
        """Test with empty pass list (no requirements)."""
        env = {"A": "1"}
        runtime = {"pass": []}

        process_runtime_env(env, runtime)

        assert env == {"A": "1"}


@pytest.mark.unit
class TestEnvironmentLayers:
    """Test layered environment application."""

    def test_all_four_layers_applied(self) -> None:
        """Test that all four layers are applied in correct order."""
        base_env = {"BASE": "base_value"}
        runtime_env = {"set": {"RUNTIME": "runtime_value"}}
        workenv_env = {"WORKENV": "workenv_value"}
        execution_env = {"EXECUTION": "execution_value"}

        result = apply_environment_layers(
            base_env=base_env,
            runtime_env=runtime_env,
            workenv_env=workenv_env,
            execution_env=execution_env,
        )

        # All layers should be present
        assert result["BASE"] == "base_value"
        assert result["RUNTIME"] == "runtime_value"
        assert result["WORKENV"] == "workenv_value"
        assert result["EXECUTION"] == "execution_value"
        # Platform variables should be added
        assert "FLAVOR_OS" in result
        assert "FLAVOR_ARCH" in result
        assert "FLAVOR_PLATFORM" in result

    def test_only_base_env(self) -> None:
        """Test with only base environment (no layers)."""
        base_env = {"BASE": "base_value"}

        result = apply_environment_layers(base_env=base_env)

        assert result["BASE"] == "base_value"
        # Platform variables should still be added
        assert "FLAVOR_OS" in result

    def test_runtime_layer_only(self) -> None:
        """Test with runtime layer only."""
        base_env = {"VAR": "original"}
        runtime_env = {"set": {"VAR": "overridden"}}

        result = apply_environment_layers(base_env=base_env, runtime_env=runtime_env)

        assert result["VAR"] == "overridden"

    def test_workenv_layer_only(self) -> None:
        """Test with workenv layer only."""
        base_env = {"BASE": "base"}
        workenv_env = {"WORKENV": "workenv"}

        result = apply_environment_layers(base_env=base_env, workenv_env=workenv_env)

        assert result["BASE"] == "base"
        assert result["WORKENV"] == "workenv"

    def test_execution_layer_only(self) -> None:
        """Test with execution layer only."""
        base_env = {"BASE": "base"}
        execution_env = {"EXEC": "exec"}

        result = apply_environment_layers(base_env=base_env, execution_env=execution_env)

        assert result["BASE"] == "base"
        assert result["EXEC"] == "exec"

    def test_platform_layer_always_last(self) -> None:
        """Test that platform layer is always applied last (override protection)."""
        base_env = {"FLAVOR_OS": "fake"}
        workenv_env = {"FLAVOR_ARCH": "fake"}
        execution_env = {"FLAVOR_PLATFORM": "fake"}

        result = apply_environment_layers(
            base_env=base_env, workenv_env=workenv_env, execution_env=execution_env
        )

        # Platform variables should override all previous layers
        assert result["FLAVOR_OS"] != "fake"
        assert result["FLAVOR_ARCH"] != "fake"
        assert result["FLAVOR_PLATFORM"] != "fake"
        assert result["FLAVOR_OS"] in ["darwin", "linux", "windows"]

    def test_layer_override_behavior(self) -> None:
        """Test layer override behavior (later layers override earlier)."""
        base_env = {"VAR": "base"}
        workenv_env = {"VAR": "workenv"}
        execution_env = {"VAR": "execution"}

        result = apply_environment_layers(
            base_env=base_env, workenv_env=workenv_env, execution_env=execution_env
        )

        # Execution layer should override workenv, which overrides base
        assert result["VAR"] == "execution"

    def test_complete_integration_scenario(self) -> None:
        """Test complete integration with all layers and operations."""
        base_env = {
            "PATH": "/usr/bin",
            "HOME": "/home/user",
            "TEMP": "/tmp",
            "OLD_VAR": "old",
        }
        runtime_env = {
            "pass": ["PATH", "HOME"],
            "unset": ["TEMP"],
            "map": {"OLD_VAR": "NEW_VAR"},
            "set": {"RUNTIME_VAR": "runtime"},
        }
        workenv_env = {"WORKENV_PATH": "/workenv/bin"}
        execution_env = {"APP_CONFIG": "/app/config"}

        result = apply_environment_layers(
            base_env=base_env,
            runtime_env=runtime_env,
            workenv_env=workenv_env,
            execution_env=execution_env,
        )

        # Runtime operations applied
        assert result["PATH"] == "/usr/bin"  # Preserved
        assert result["HOME"] == "/home/user"  # Preserved
        assert "TEMP" not in result  # Unset
        assert "OLD_VAR" not in result  # Mapped
        assert result["NEW_VAR"] == "old"  # Mapped to NEW_VAR
        assert result["RUNTIME_VAR"] == "runtime"  # Set
        # Workenv layer
        assert result["WORKENV_PATH"] == "/workenv/bin"
        # Execution layer
        assert result["APP_CONFIG"] == "/app/config"
        # Platform layer
        assert "FLAVOR_OS" in result
        assert "FLAVOR_ARCH" in result
        assert "FLAVOR_PLATFORM" in result
