"""
Attrs models for metadata structures.

These models provide immutable, validated data structures for
package metadata with automatic conversion and validation.
"""

from attrs import define, field, validators, Factory
from typing import Any

from flavor.psp.metadata.converters import (
    ensure_workenv_prefix,
    parse_octal_mode,
    normalize_env_dict,
    to_list,
)
from flavor.psp.metadata.validators import (
    validate_workenv_path,
    validate_mode,
    validate_format_version,
)


@define(frozen=True, slots=True)
class DirectorySpec:
    """Immutable directory specification."""
    
    path: str = field(
        converter=ensure_workenv_prefix,
        validator=validate_workenv_path
    )
    mode: int = field(
        default=0o755,
        converter=parse_octal_mode,
        validator=validate_mode
    )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "path": self.path,
            "mode": oct(self.mode)[2:]  # Remove '0o' prefix
        }


@define(frozen=True, slots=True)
class WorkenvSpec:
    """Workenv configuration specification."""
    
    directories: list[DirectorySpec] = field(factory=list)
    env: dict[str, str] = field(
        factory=dict,
        converter=normalize_env_dict
    )
    umask: int = field(
        default=0o077,
        converter=parse_octal_mode,
        validator=validate_mode
    )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        result = {}
        if self.directories:
            result["directories"] = [d.to_dict() for d in self.directories]
        if self.env:
            result["env"] = self.env
        if self.umask != 0o077:
            result["umask"] = oct(self.umask)[2:]
        return result
    
    def validate(self) -> None:
        """Validate the workenv specification."""
        # All directories must have {workenv} prefix
        for dir_spec in self.directories:
            if not dir_spec.path.startswith("{workenv}"):
                raise ValueError(f"Directory path must start with {{workenv}}: {dir_spec.path}")


@define(frozen=True, slots=True)
class RuntimeEnvOps:
    """Runtime environment operations."""
    
    unset: list[str] = field(
        factory=list,
        converter=to_list
    )
    pass_vars: list[str] = field(  # 'pass' is a keyword
        factory=list,
        converter=to_list
    )
    map_vars: dict[str, str] = field(
        factory=dict,
        converter=normalize_env_dict
    )
    set_vars: dict[str, str] = field(
        factory=dict,
        converter=normalize_env_dict
    )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        result = {}
        if self.unset:
            result["unset"] = self.unset
        if self.pass_vars:
            result["pass"] = self.pass_vars
        if self.map_vars:
            result["map"] = self.map_vars
        if self.set_vars:
            result["set"] = self.set_vars
        return result
    
    def apply(self, env: dict[str, str]) -> dict[str, str]:
        """Apply operations to an environment dictionary.
        
        Args:
            env: Input environment
            
        Returns:
            Processed environment
        """
        result = env.copy()
        
        # Unset variables
        for var in self.unset:
            result.pop(var, None)
        
        # Pass (whitelist) variables
        if self.pass_vars:
            passed = {}
            for var in self.pass_vars:
                if var in result:
                    passed[var] = result[var]
            result = passed
        
        # Map (rename) variables
        for old_name, new_name in self.map_vars.items():
            if old_name in result:
                result[new_name] = result.pop(old_name)
        
        # Set variables
        result.update(self.set_vars)
        
        return result


@define(frozen=True, slots=True)
class RuntimeSpec:
    """Runtime configuration specification."""
    
    env: RuntimeEnvOps = field(factory=RuntimeEnvOps)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        env_dict = self.env.to_dict()
        if env_dict:
            return {"env": env_dict}
        return {}


@define(frozen=True, slots=True)
class ExecutionSpec:
    """Execution configuration specification."""
    
    command: str | None = field(default=None)
    args: list[str] = field(factory=list)
    env: dict[str, str] = field(
        factory=dict,
        converter=normalize_env_dict
    )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        result = {}
        if self.command:
            result["command"] = self.command
        if self.args:
            result["args"] = self.args
        if self.env:
            result["env"] = self.env
        return result


@define(frozen=True, slots=True)
class PackageInfo:
    """Package information."""
    
    name: str = field(validator=validators.instance_of(str))
    version: str = field(validator=validators.instance_of(str))
    description: str = field(default="")
    authors: list[str] = field(factory=list)
    license: str = field(default="")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "name": self.name,
            "version": self.version,
        }
        if self.description:
            result["description"] = self.description
        if self.authors:
            result["authors"] = self.authors
        if self.license:
            result["license"] = self.license
        return result


@define(frozen=True, slots=True)
class PSPFMetadata:
    """Complete PSPF/2025 metadata structure."""
    
    format_version: str = field(
        default="PSPF/2025",
        validator=validate_format_version
    )
    package: PackageInfo | None = field(default=None)
    runtime: RuntimeSpec = field(factory=RuntimeSpec)
    workenv: WorkenvSpec = field(factory=WorkenvSpec)
    execution: ExecutionSpec = field(factory=ExecutionSpec)
    slots: list[dict[str, Any]] = field(factory=list)
    
    def validate(self) -> None:
        """Validate the complete metadata structure."""
        # Validate format
        if self.format_version != "PSPF/2025":
            raise ValueError(f"Unsupported format: {self.format_version}")
        
        # Validate workenv
        if self.workenv:
            self.workenv.validate()
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        result = {"format": self.format_version}
        
        if self.package:
            result["package"] = self.package.to_dict()
        
        runtime_dict = self.runtime.to_dict()
        if runtime_dict:
            result["runtime"] = runtime_dict
        
        workenv_dict = self.workenv.to_dict()
        if workenv_dict:
            result["workenv"] = workenv_dict
        
        execution_dict = self.execution.to_dict()
        if execution_dict:
            result["execution"] = execution_dict
        
        if self.slots:
            result["slots"] = self.slots
        
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PSPFMetadata":
        """Create from dictionary representation.
        
        Args:
            data: Dictionary representation
            
        Returns:
            PSPFMetadata instance
            
        Raises:
            ValidationError: If data is invalid
        """
        from flavor.psp.metadata.validators import ValidationError
        
        # Parse package info
        package = None
        if "package" in data:
            package = PackageInfo(**data["package"])
        
        # Parse runtime
        runtime = RuntimeSpec()
        if "runtime" in data and "env" in data["runtime"]:
            env_ops = RuntimeEnvOps(
                unset=data["runtime"]["env"].get("unset", []),
                pass_vars=data["runtime"]["env"].get("pass", []),
                map_vars=data["runtime"]["env"].get("map", {}),
                set_vars=data["runtime"]["env"].get("set", {})
            )
            runtime = RuntimeSpec(env=env_ops)
        
        # Parse workenv
        workenv = WorkenvSpec()
        if "workenv" in data:
            dirs = []
            if "directories" in data["workenv"]:
                # Validate paths before creating DirectorySpec
                for d in data["workenv"]["directories"]:
                    if "path" in d and not d["path"].startswith("{workenv}"):
                        raise ValidationError(
                            field="workenv.directories.path",
                            value=d["path"],
                            reason="must start with {workenv}"
                        )
                dirs = [DirectorySpec(**d) for d in data["workenv"]["directories"]]
            
            workenv = WorkenvSpec(
                directories=dirs,
                env=data["workenv"].get("env", {}),
                umask=data["workenv"].get("umask", "0077")
            )
        
        # Parse execution
        execution = ExecutionSpec()
        if "execution" in data:
            execution = ExecutionSpec(
                command=data["execution"].get("command"),
                args=data["execution"].get("args", []),
                env=data["execution"].get("env", {})
            )
        
        return cls(
            format_version=data.get("format", "PSPF/2025"),
            package=package,
            runtime=runtime,
            workenv=workenv,
            execution=execution,
            slots=data.get("slots", [])
        )