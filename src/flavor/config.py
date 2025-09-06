"""
Structured configuration models for the `[tool.flavor]` section of `pyproject.toml`.

This module uses the `attrs` library to define typed, immutable classes that
represent the configuration for building a Flavor package. This approach provides
type safety, default values, and clearer code compared to using unstructured
dictionaries.
"""

from typing import Any

from attrs import define, field
from provide.foundation.config import BaseConfig, field as config_field

from flavor.exceptions import ValidationError


@define(frozen=True, kw_only=True)
class RuntimeRuntimeConfig:
    """Configuration for the sandboxed runtime environment variables."""

    unset: list[str] = config_field(
        factory=list,
        description="Environment variables to unset",
        env_var="FLAVOR_RUNTIME_ENV_UNSET"
    )
    passthrough: list[str] = config_field(
        factory=list,
        description="Environment variables to pass through",
        env_var="FLAVOR_RUNTIME_ENV_PASSTHROUGH"
    )
    set_vars: dict[str, str | int | bool] = config_field(
        factory=dict,
        description="Environment variables to set"
    )
    map_vars: dict[str, str] = config_field(
        factory=dict,
        description="Environment variable mappings"
    )


@define(frozen=True, kw_only=True)
class ExecutionConfig:
    """Execution-related configuration from the manifest."""

    runtime_env: RuntimeRuntimeConfig = field(factory=RuntimeRuntimeConfig)


@define(frozen=True, kw_only=True)
class BuildConfig:
    """Build-related configuration from the manifest."""

    dependencies: list[str] = config_field(
        factory=list,
        description="Build dependencies",
        env_var="FLAVOR_BUILD_DEPENDENCIES"
    )


@define(frozen=True, kw_only=True)
class MetadataConfig:
    """Metadata-related configuration from the manifest."""

    package_name: str | None = config_field(
        default=None,
        description="Override package name",
        env_var="FLAVOR_METADATA_PACKAGE_NAME"
    )


@define(frozen=True, kw_only=True)
class FlavorConfig(BaseConfig):
    """Top-level structured configuration for the `[tool.flavor]` section."""

    name: str = config_field(
        description="Package name",
        env_var="FLAVOR_PACKAGE_NAME"
    )
    version: str = config_field(
        description="Package version", 
        env_var="FLAVOR_VERSION"
    )
    entry_point: str = config_field(
        description="Application entry point",
        env_var="FLAVOR_ENTRY_POINT"
    )
    metadata: MetadataConfig = field(factory=MetadataConfig)
    build: BuildConfig = field(factory=BuildConfig)
    execution: ExecutionConfig = field(factory=ExecutionConfig)

    @classmethod
    def from_dict(
        cls, config: dict[str, Any], project_defaults: dict[str, Any]
    ) -> "FlavorConfig":
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
            raise ValidationError(
                "Project name must be defined in [project].name or [tool.flavor].name"
            )

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

        return cls(
            name=name,
            version=version,
            entry_point=entry_point,
            metadata=metadata,
            build=build,
            execution=execution,
        )
