#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for Foundation-based configuration system."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from flavor.config import (
    BuildConfig,
    ExecutionConfig,
    FlavorConfig,
    MetadataConfig,
    PathsConfig,
    RuntimeRuntimeConfig,
    SecurityConfig,
    SystemConfig,
    UVConfig,
    get_flavor_config,
    set_flavor_config,
)
from flavor.config.defaults import (
    DEFAULT_VALIDATION_LEVEL,
    VALIDATION_MINIMAL,
    VALIDATION_NONE,
    VALIDATION_RELAXED,
    VALIDATION_STANDARD,
    VALIDATION_STRICT,
)
from flavor.exceptions import ValidationError
from flavor.psp.security import ValidationLevel, get_validation_level


class TestSecurityConfig:
    """Test security configuration."""

    def test_default_validation_level(self) -> None:
        """Test default validation level."""
        config = SecurityConfig()
        assert config.validation_level == DEFAULT_VALIDATION_LEVEL

    @patch.dict(os.environ, {"FLAVOR_VALIDATION": "strict"})
    def test_strict_validation_from_env(self) -> None:
        """Test strict validation level from environment."""
        config = SecurityConfig.from_env()
        assert config.validation_level == "strict"

    @patch.dict(os.environ, {"FLAVOR_VALIDATION": "relaxed"})
    def test_relaxed_validation_from_env(self) -> None:
        """Test relaxed validation level from environment."""
        config = SecurityConfig.from_env()
        assert config.validation_level == "relaxed"

    def test_invalid_validation_level(self) -> None:
        """Test that invalid validation levels raise ValidationError."""
        with pytest.raises(ValidationError, match="Invalid validation level 'invalid'"):
            SecurityConfig(validation_level="invalid")

    def test_all_valid_validation_levels(self) -> None:
        """Test all valid validation levels."""
        for level in [
            VALIDATION_STRICT,
            VALIDATION_STANDARD,
            VALIDATION_RELAXED,
            VALIDATION_MINIMAL,
            VALIDATION_NONE,
        ]:
            config = SecurityConfig(validation_level=level)
            assert config.validation_level == level


class TestPathsConfig:
    """Test paths configuration."""

    def test_default_paths(self) -> None:
        """Test default path configuration."""
        config = PathsConfig()
        assert config.builder_bin is None
        assert config.launcher_bin is None
        assert config.workenv_base is None
        assert config.xdg_cache_home is None

    @patch.dict(
        os.environ,
        {
            "FLAVOR_BUILDER_BIN": "/custom/builder",
            "FLAVOR_LAUNCHER_BIN": "/custom/launcher",
            "FLAVOR_WORKENV_BASE": "/custom/workenv",
            "XDG_CACHE_HOME": "/custom/cache",
        },
    )
    def test_paths_from_env(self) -> None:
        """Test paths loaded from environment variables."""
        config = PathsConfig.from_env()
        assert config.builder_bin == "/custom/builder"
        assert config.launcher_bin == "/custom/launcher"
        assert config.workenv_base == "/custom/workenv"
        assert config.xdg_cache_home == "/custom/cache"

    def test_effective_cache_home_with_xdg(self) -> None:
        """Test effective cache home when XDG_CACHE_HOME is set."""
        config = PathsConfig(xdg_cache_home="/custom/cache")
        assert config.effective_cache_home == Path("/custom/cache")

    def test_effective_cache_home_default(self) -> None:
        """Test effective cache home with default fallback."""
        config = PathsConfig()
        expected = Path("~/.cache").expanduser()
        assert config.effective_cache_home == expected

    def test_effective_workenv_base_with_custom(self) -> None:
        """Test effective workenv base when custom path is set."""
        config = PathsConfig(workenv_base="/custom/workenv")
        assert config.effective_workenv_base == Path("/custom/workenv")

    def test_effective_workenv_base_default(self) -> None:
        """Test effective workenv base with default fallback."""
        config = PathsConfig()
        assert config.effective_workenv_base == Path.cwd()


class TestUVConfig:
    """Test UV configuration."""

    def test_default_uv_config(self) -> None:
        """Test default UV configuration."""
        config = UVConfig()
        assert config.cache_dir is None
        assert config.python_install_dir is None
        assert config.system_python is None

    @patch.dict(
        os.environ,
        {
            "UV_CACHE_DIR": "/custom/uv/cache",
            "UV_PYTHON_INSTALL_DIR": "/custom/uv/python",
            "UV_SYSTEM_PYTHON": "1",
        },
    )
    def test_uv_config_from_env(self) -> None:
        """Test UV configuration from environment variables."""
        config = UVConfig.from_env()
        assert config.cache_dir == "/custom/uv/cache"
        assert config.python_install_dir == "/custom/uv/python"
        assert config.system_python == "1"


class TestSystemConfig:
    """Test system configuration aggregation."""

    def test_default_system_config(self) -> None:
        """Test default system configuration."""
        config = SystemConfig()
        assert isinstance(config.uv, UVConfig)
        assert isinstance(config.paths, PathsConfig)
        assert isinstance(config.security, SecurityConfig)

    @patch.dict(
        os.environ,
        {
            "FLAVOR_VALIDATION": "strict",
            "FLAVOR_BUILDER_BIN": "/custom/builder",
            "UV_CACHE_DIR": "/custom/uv/cache",
        },
    )
    def test_system_config_from_env(self) -> None:
        """Test system configuration with environment variables."""
        config = SystemConfig(
            security=SecurityConfig.from_env(),
            paths=PathsConfig.from_env(),
            uv=UVConfig.from_env(),
        )
        assert config.security.validation_level == "strict"
        assert config.paths.builder_bin == "/custom/builder"
        assert config.uv.cache_dir == "/custom/uv/cache"


class TestFlavorConfig:
    """Test main FlavorConfig class."""

    def test_minimal_flavor_config(self) -> None:
        """Test minimal FlavorConfig creation."""
        config = FlavorConfig(name="test-app", version="1.0.0", entry_point="test.main:app")
        assert config.name == "test-app"
        assert config.version == "1.0.0"
        assert config.entry_point == "test.main:app"
        assert isinstance(config.system, SystemConfig)

    @patch.dict(os.environ, {"FLAVOR_VALIDATION": "strict"})
    def test_flavor_config_with_env(self) -> None:
        """Test FlavorConfig with environment variables."""
        # Reset global config to force reload from environment
        set_flavor_config(None)

        config = FlavorConfig(
            name="test-app",
            version="1.0.0",
            entry_point="test.main:app",
            system=SystemConfig(
                security=SecurityConfig.from_env(),
                paths=PathsConfig.from_env(),
                uv=UVConfig.from_env(),
            ),
        )
        assert config.system.security.validation_level == "strict"

    def test_from_pyproject_dict(self) -> None:
        """Test creating FlavorConfig from pyproject.toml data."""
        project_data = {
            "name": "test-app",
            "version": "1.0.0",
        }
        flavor_data = {
            "entry_point": "test.main:app",
        }

        config = FlavorConfig.from_pyproject_dict(flavor_data, project_data)
        assert config.name == "test-app"
        assert config.version == "1.0.0"
        assert config.entry_point == "test.main:app"

    def test_from_pyproject_dict_missing_name(self) -> None:
        """Test error when name is missing."""
        with pytest.raises(ValidationError, match="Project name must be defined"):
            FlavorConfig.from_pyproject_dict({}, {})

    def test_from_pyproject_dict_missing_version(self) -> None:
        """Test error when version is missing."""
        with pytest.raises(ValidationError, match="Project version must be defined"):
            FlavorConfig.from_pyproject_dict({}, {"name": "test"})

    def test_from_pyproject_dict_missing_entry_point(self) -> None:
        """Test error when entry_point is missing."""
        with pytest.raises(ValidationError, match="Project entry_point must be defined"):
            FlavorConfig.from_pyproject_dict({}, {"name": "test", "version": "1.0.0"})


class TestGlobalConfig:
    """Test global configuration management."""

    def test_get_flavor_config_default(self) -> None:
        """Test getting default flavor config."""
        # Reset global config
        set_flavor_config(None)

        config = get_flavor_config()
        assert config.name == "flavor"
        assert config.version == "0.0.0"
        assert config.entry_point == "flavor.cli:main"
        assert isinstance(config.system, SystemConfig)

    def test_set_flavor_config(self) -> None:
        """Test setting custom flavor config."""
        custom_config = FlavorConfig(name="custom-app", version="2.0.0", entry_point="custom.main:app")

        set_flavor_config(custom_config)
        retrieved_config = get_flavor_config()

        assert retrieved_config.name == "custom-app"
        assert retrieved_config.version == "2.0.0"
        assert retrieved_config.entry_point == "custom.main:app"

    @patch.dict(os.environ, {"FLAVOR_VALIDATION": "none"})
    def test_global_config_with_env_vars(self) -> None:
        """Test that global config picks up environment variables."""
        # Reset global config to force reload
        set_flavor_config(None)

        config = get_flavor_config()
        assert config.system.security.validation_level == "none"


class TestSecurityIntegration:
    """Test integration between config system and security module."""

    @patch.dict(os.environ, {"FLAVOR_VALIDATION": "strict"})
    def test_validation_level_strict(self) -> None:
        """Test strict validation level integration."""
        # Reset global config
        set_flavor_config(None)

        level = get_validation_level()
        assert level == ValidationLevel.STRICT

    @patch.dict(os.environ, {"FLAVOR_VALIDATION": "relaxed"})
    def test_validation_level_relaxed(self) -> None:
        """Test relaxed validation level integration."""
        # Reset global config
        set_flavor_config(None)

        level = get_validation_level()
        assert level == ValidationLevel.RELAXED

    @patch.dict(os.environ, {"FLAVOR_VALIDATION": "minimal"})
    def test_validation_level_minimal(self) -> None:
        """Test minimal validation level integration."""
        # Reset global config
        set_flavor_config(None)

        level = get_validation_level()
        assert level == ValidationLevel.MINIMAL

    @patch.dict(os.environ, {"FLAVOR_VALIDATION": "none"})
    def test_validation_level_none_with_warning(self) -> None:
        """Test none validation level with warning."""
        # Reset global config
        set_flavor_config(None)

        level = get_validation_level()
        assert level == ValidationLevel.NONE

        # Note: Warning is logged but not captured by caplog due to Foundation's structured logging

    @patch.dict(os.environ, {"FLAVOR_VALIDATION": "standard"})
    def test_validation_level_standard(self) -> None:
        """Test standard validation level."""
        # Reset global config
        set_flavor_config(None)

        level = get_validation_level()
        assert level == ValidationLevel.STANDARD

    @patch.dict(os.environ, {"FLAVOR_VALIDATION": "unknown"})
    def test_validation_level_unknown_raises_error(self) -> None:
        """Test unknown validation level raises ValidationError."""
        # Reset global config
        set_flavor_config(None)

        with pytest.raises(ValidationError, match="Invalid validation level 'unknown'"):
            get_validation_level()

    def test_validation_level_with_custom_config(self) -> None:
        """Test validation level with custom configuration."""
        custom_config = FlavorConfig(
            name="test-app",
            version="1.0.0",
            entry_point="test.main:app",
            system=SystemConfig(security=SecurityConfig(validation_level="strict")),
        )

        set_flavor_config(custom_config)
        level = get_validation_level()
        assert level == ValidationLevel.STRICT


class TestRuntimeRuntimeConfig:
    """Test runtime environment configuration."""

    def test_default_runtime_config(self) -> None:
        """Test default runtime configuration."""
        config = RuntimeRuntimeConfig()
        assert config.unset == []
        assert config.passthrough == []
        assert config.set_vars == {}
        assert config.map_vars == {}

    def test_runtime_config_with_values(self) -> None:
        """Test runtime configuration with custom values."""
        config = RuntimeRuntimeConfig(
            unset=["VAR1", "VAR2"],
            passthrough=["PATH", "HOME"],
            set_vars={"DEBUG": True, "PORT": 8080},
            map_vars={"OLD_VAR": "NEW_VAR"},
        )
        assert config.unset == ["VAR1", "VAR2"]
        assert config.passthrough == ["PATH", "HOME"]
        assert config.set_vars == {"DEBUG": True, "PORT": 8080}
        assert config.map_vars == {"OLD_VAR": "NEW_VAR"}


class TestBuildConfig:
    """Test build configuration."""

    def test_default_build_config(self) -> None:
        """Test default build configuration."""
        config = BuildConfig()
        assert config.dependencies == []

    def test_build_config_with_dependencies(self) -> None:
        """Test build configuration with dependencies."""
        config = BuildConfig(dependencies=["setuptools", "wheel"])
        assert config.dependencies == ["setuptools", "wheel"]


class TestMetadataConfig:
    """Test metadata configuration."""

    def test_default_metadata_config(self) -> None:
        """Test default metadata configuration."""
        config = MetadataConfig()
        assert config.package_name is None

    @patch.dict(os.environ, {"FLAVOR_METADATA_PACKAGE_NAME": "custom-name"})
    def test_metadata_config_from_env(self) -> None:
        """Test metadata configuration from environment."""
        config = MetadataConfig.from_env()
        assert config.package_name == "custom-name"

    def test_metadata_config_with_custom_name(self) -> None:
        """Test metadata configuration with custom package name."""
        config = MetadataConfig(package_name="custom-app")
        assert config.package_name == "custom-app"


class TestExecutionConfig:
    """Test execution configuration."""

    def test_default_execution_config(self) -> None:
        """Test default execution configuration."""
        config = ExecutionConfig()
        assert isinstance(config.runtime_env, RuntimeRuntimeConfig)
        assert config.runtime_env.unset == []
        assert config.runtime_env.passthrough == []
        assert config.runtime_env.set_vars == {}
        assert config.runtime_env.map_vars == {}

    def test_execution_config_with_custom_runtime(self) -> None:
        """Test execution configuration with custom runtime environment."""
        runtime_env = RuntimeRuntimeConfig(unset=["DEBUG"], passthrough=["PATH"])
        config = ExecutionConfig(runtime_env=runtime_env)
        assert config.runtime_env.unset == ["DEBUG"]
        assert config.runtime_env.passthrough == ["PATH"]


# 🌶️📦🔚
