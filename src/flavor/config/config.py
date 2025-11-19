#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Structured configuration models for the `[tool.flavor]` section of `pyproject.toml`.

Uses `attrs` to provide typed, immutable classes with sensible defaults.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from attrs import define, field
from provide.foundation.config import BaseConfig, field as config_field
from provide.foundation.config.env import RuntimeConfig

from flavor.config.defaults import (
    DEFAULT_VALIDATION_LEVEL,
    VALIDATION_LEVELS,
)
from flavor.exceptions import ValidationError


@define(frozen=True, kw_only=True)
class RuntimeRuntimeConfig:
    """Configuration for the sandboxed runtime environment variables."""

    unset: list[str] = field(factory=list)
    passthrough: list[str] = field(factory=list)
    set_vars: dict[str, str | int | bool] = field(factory=dict)
    map_vars: dict[str, str] = field(factory=dict)


@define(frozen=True, kw_only=True)
class ExecutionConfig:
    """Execution-related configuration from the manifest."""

    runtime_env: RuntimeRuntimeConfig = field(factory=RuntimeRuntimeConfig)


@define(frozen=True, kw_only=True)
class BuildConfig:
    """Build-related configuration from the manifest."""

    dependencies: list[str] = field(factory=list)


@define(frozen=True, kw_only=True)
class SecurityConfig(RuntimeConfig):
    """Security and validation configuration."""

    validation_level: str = config_field(
        default=DEFAULT_VALIDATION_LEVEL,
        description="Package validation level (strict/standard/relaxed/minimal/none)",
        env_var="FLAVOR_VALIDATION",
    )

    def __attrs_post_init__(self) -> None:
        """Validate the security configuration after initialization."""
        if self.validation_level not in VALIDATION_LEVELS:
            valid_levels = ", ".join(VALIDATION_LEVELS.keys())
            raise ValidationError(
                f"Invalid validation level '{self.validation_level}'. Must be one of: {valid_levels}"
            )


@define(frozen=True, kw_only=True)
class PathsConfig(RuntimeConfig):
    """Path and directory configuration."""

    builder_bin: str | None = config_field(
        default=None,
        description="Path to custom builder binary",
        env_var="FLAVOR_BUILDER_BIN",
    )
    launcher_bin: str | None = config_field(
        default=None,
        description="Path to custom launcher binary",
        env_var="FLAVOR_LAUNCHER_BIN",
    )
    workenv_base: str | None = config_field(
        default=None,
        description="Base directory for work environment",
        env_var="FLAVOR_WORKENV_BASE",
    )
    xdg_cache_home: str | None = config_field(
        default=None,
        description="XDG cache directory",
        env_var="XDG_CACHE_HOME",
    )

    @property
    def effective_cache_home(self) -> Path:
        """Get effective cache home directory with fallback."""
        if self.xdg_cache_home:
            return Path(self.xdg_cache_home)
        return Path("~/.cache").expanduser()

    @property
    def effective_workenv_base(self) -> Path:
        """Get effective work environment base with fallback."""
        if self.workenv_base:
            return Path(self.workenv_base)
        return Path.cwd()


@define(frozen=True, kw_only=True)
class UVConfig(RuntimeConfig):
    """UV (Python package manager) configuration."""

    cache_dir: str | None = config_field(
        default=None,
        description="UV cache directory",
        env_var="UV_CACHE_DIR",
    )
    python_install_dir: str | None = config_field(
        default=None,
        description="UV Python installation directory",
        env_var="UV_PYTHON_INSTALL_DIR",
    )
    system_python: str | None = config_field(
        default=None,
        description="UV system Python setting",
        env_var="UV_SYSTEM_PYTHON",
    )


@define(frozen=True, kw_only=True)
class SystemConfig:
    """System and environment configuration."""

    uv: UVConfig = field(factory=UVConfig)
    paths: PathsConfig = field(factory=PathsConfig)
    security: SecurityConfig = field(factory=SecurityConfig)


@define(frozen=True, kw_only=True)
class MetadataConfig(RuntimeConfig):
    """Metadata-related configuration from the manifest."""

    package_name: str | None = config_field(
        default=None,
        description="Override package name",
        env_var="FLAVOR_METADATA_PACKAGE_NAME",
    )


@define(frozen=True, kw_only=True)
class FlavorConfig(BaseConfig):
    """Top-level structured configuration for the `[tool.flavor]` section."""

    name: str = config_field(description="Package name", env_var="FLAVOR_PACKAGE_NAME")
    version: str = config_field(description="Package version", env_var="FLAVOR_VERSION")
    entry_point: str = config_field(description="Application entry point", env_var="FLAVOR_ENTRY_POINT")
    metadata: MetadataConfig = field(factory=MetadataConfig)
    build: BuildConfig = field(factory=BuildConfig)
    execution: ExecutionConfig = field(factory=ExecutionConfig)
    system: SystemConfig = field(factory=SystemConfig)

    @classmethod
    def from_pyproject_dict(cls, config: dict[str, Any], project_defaults: dict[str, Any]) -> FlavorConfig:
        """
        Factory method to create a validated FlavorConfig from a dictionary.

        Args:
            config: The dictionary from the `[tool.flavor]` section of pyproject.toml.
            project_defaults: A dictionary with fallback values from the `[project]` section.

        Returns:
            A validated, immutable FlavorConfig instance.

        Raises:
            ValidationError: If the configuration is invalid.
        """
        name = config.get("name") or project_defaults.get("name")
        if not name:
            raise ValidationError("Project name must be defined in [project].name or [tool.flavor].name")

        version = config.get("version") or project_defaults.get("version")
        if not version:
            raise ValidationError(
                "Project version must be defined in [project].version or [tool.flavor].version"
            )

        entry_point = config.get("entry_point") or project_defaults.get("entry_point")
        if not entry_point:
            raise ValidationError(
                "Project entry_point must be defined in [project].scripts or [tool.flavor].entry_point"
            )

        # Metadata
        meta_conf = config.get("metadata", {})
        metadata = MetadataConfig(package_name=meta_conf.get("package_name"))

        # Build
        build_conf = config.get("build", {})
        build = BuildConfig(dependencies=build_conf.get("dependencies", []))

        # Execution
        exec_conf = config.get("execution", {})
        runtime_conf = exec_conf.get("runtime", {}).get("env", {})
        runtime_env = RuntimeRuntimeConfig(
            unset=runtime_conf.get("unset", []),
            passthrough=runtime_conf.get("pass", []),  # 'pass' is the key in TOML
            set_vars=runtime_conf.get("set", {}),
            map_vars=runtime_conf.get("map", {}),
        )
        execution = ExecutionConfig(runtime_env=runtime_env)

        # System configuration (loaded from environment variables)
        system = SystemConfig()

        return cls(
            name=name,
            version=version,
            entry_point=entry_point,
            metadata=metadata,
            build=build,
            execution=execution,
            system=system,
        )


# 🌶️📦🔚
