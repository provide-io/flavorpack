#
# flavor/metadata.py
#
"""Metadata models for Flavor PSPF/2025 packages."""

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from attrs import asdict, define, field, fields


@define
class PSPFMetadata:
    """Core PSPF metadata (pspf.json)."""

    format_version: str = "2025"
    format_name: str = "Progressive Secure Package Format"
    created_at: datetime = field(factory=lambda: datetime.now(UTC))
    created_by: dict[str, str] = field(factory=dict)
    build_host: dict[str, str] = field(factory=dict)
    package_info: dict[str, Any] = field(factory=dict)
    flags_interpretation: dict[str, Any] = field(factory=dict)
    sections: dict[str, dict[str, Any]] = field(factory=dict)

    def to_json(self) -> str:
        """Serialize to JSON."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat() + "Z"
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "PSPFMetadata":
        """Deserialize from JSON."""
        data = json.loads(json_str)
        if "created_at" in data:
            data["created_at"] = datetime.fromisoformat(data["created_at"].rstrip("Z"))
        return cls(**data)


@define
class PackageMetadata:
    """Package information (package.json)."""

    name: str
    version: str
    description: str = ""
    author: dict[str, str] = field(factory=dict)
    license: str = ""
    homepage: str | None = None
    repository: dict[str, str | None] | None = None
    bugs: dict[str, str | None] | None = None
    keywords: list[str] = field(factory=list)
    terraform: dict[str, Any] = field(factory=dict)
    supported_platforms: list[str] = field(factory=list)
    requirements: dict[str, str] = field(factory=dict)
    metadata: dict[str, Any] = field(factory=dict)

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "PackageMetadata":
        """Deserialize from JSON."""
        data = json.loads(json_str)
        # Filter to only known fields
        known_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered_data)


@define
class RuntimeConfig:
    """Runtime configuration (runtime.json)."""

    entry_point: str
    entry_module: str | None = None
    entry_function: str | None = None
    working_directory: str = "."
    python_executable: str = "./python/bin/python"
    python_args: list[str] = field(factory=list)
    environment: dict[str, str] = field(factory=dict)
    inherit_env: list[str] = field(factory=list)
    capabilities: dict[str, Any] = field(factory=dict)
    resource_limits: dict[str, Any] = field(factory=dict)
    logging: dict[str, Any] = field(factory=dict)

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "RuntimeConfig":
        """Deserialize from JSON."""
        data = json.loads(json_str)
        # Filter to only known fields
        known_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered_data)


@define
class DependencyInfo:
    """Dependency information (dependencies.json)."""

    resolver: str = "uv"
    resolver_version: str = ""
    resolution_date: datetime = field(factory=lambda: datetime.now(UTC))
    python_version: str = ""
    platform: dict[str, Any] = field(factory=dict)
    direct_dependencies: list[str] = field(factory=list)
    resolved_packages: dict[str, dict[str, Any]] = field(factory=dict)
    dependency_graph: dict[str, list[str]] = field(factory=dict)
    total_packages: int = 0
    total_size_bytes: int = 0
    vulnerabilities_check: dict[str, Any] = field(factory=dict)

    def to_json(self) -> str:
        """Serialize to JSON."""
        data = asdict(self)
        data["resolution_date"] = self.resolution_date.isoformat() + "Z"
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "DependencyInfo":
        """Deserialize from JSON."""
        data = json.loads(json_str)
        if "resolution_date" in data:
            data["resolution_date"] = datetime.fromisoformat(
                data["resolution_date"].rstrip("Z")
            )
        return cls(**data)


@define
class ChecksumInfo:
    """Checksum information (checksums.json)."""

    algorithm: str = "sha256"
    generated_at: datetime = field(factory=lambda: datetime.now(UTC))
    sections: dict[str, dict[str, Any]] = field(factory=dict)
    payload_contents: dict[str, str] = field(factory=dict)
    total_package_checksum: str | None = None

    def to_json(self) -> str:
        """Serialize to JSON."""
        data = asdict(self)
        data["generated_at"] = self.generated_at.isoformat() + "Z"
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "ChecksumInfo":
        """Deserialize from JSON."""
        data = json.loads(json_str)
        if "generated_at" in data:
            data["generated_at"] = datetime.fromisoformat(
                data["generated_at"].rstrip("Z")
            )
        # Filter to only known fields
        known_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered_data)


class MetadataBundle:
    """Container for all metadata files."""

    def __init__(
        self,
        pspf: PSPFMetadata,
        package: PackageMetadata,
        runtime: RuntimeConfig,
        dependencies: DependencyInfo,
        checksums: ChecksumInfo,
    ) -> None:
        self.pspf = pspf
        self.package = package
        self.runtime = runtime
        self.dependencies = dependencies
        self.checksums = checksums

    def write_to_directory(self, metadata_dir: Path) -> None:
        """Write all metadata files to a directory."""
        metadata_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

        files = {
            "pspf.json": self.pspf.to_json(),
            "package.json": self.package.to_json(),
            "runtime.json": self.runtime.to_json(),
            "dependencies.json": self.dependencies.to_json(),
            "checksums.json": self.checksums.to_json(),
        }

        for filename, content in files.items():
            filepath = metadata_dir / filename
            filepath.write_text(content)
            filepath.chmod(0o600)

    @classmethod
    def read_from_directory(cls, metadata_dir: Path) -> "MetadataBundle":
        """Read all metadata files from a directory."""
        return cls(
            pspf=PSPFMetadata.from_json((metadata_dir / "pspf.json").read_text()),
            package=PackageMetadata.from_json(
                (metadata_dir / "package.json").read_text()
            ),
            runtime=RuntimeConfig.from_json(
                (metadata_dir / "runtime.json").read_text()
            ),
            dependencies=DependencyInfo.from_json(
                (metadata_dir / "dependencies.json").read_text()
            ),
            checksums=ChecksumInfo.from_json(
                (metadata_dir / "checksums.json").read_text()
            ),
        )


def create_minimal_metadata(
    name: str, version: str, entry_point: str
) -> MetadataBundle:
    """Create minimal metadata for a package."""
    return MetadataBundle(
        pspf=PSPFMetadata(created_by={"tool": "flavor", "version": "2025.0.0"}),
        package=PackageMetadata(
            name=name, version=version, description=f"{name} Terraform provider"
        ),
        runtime=RuntimeConfig(entry_point=entry_point),
        dependencies=DependencyInfo(),
        checksums=ChecksumInfo(),
    )


# ⚡ 🎨 🏃


# 📦🍜📄🪄
