"""Tests for PSPF/2025 metadata models."""

from datetime import datetime
import json
from pathlib import Path
import tempfile

import pytest

from flavor.metadata import (
    ChecksumInfo,
    DependencyInfo,
    MetadataBundle,
    PackageMetadata,
    PSPFMetadata,
    RuntimeConfig,
    create_minimal_metadata,
)


class TestPSPFMetadata:
    """Test PSPF metadata model."""

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        meta = PSPFMetadata()
        assert meta.format_version == "2025"
        assert meta.format_name == "Progressive Secure Package Format"
        assert isinstance(meta.created_at, datetime)
        assert meta.created_by == {}
        assert meta.build_host == {}
        assert meta.package_info == {}
        assert meta.flags_interpretation == {}
        assert meta.sections == {}

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        meta = PSPFMetadata(
            created_by={"tool": "flavor", "version": "0.1.0"},
            build_host={"platform": "darwin_arm64"},
            package_info={"size_bytes": 1024},
        )

        json_str = meta.to_json()
        data = json.loads(json_str)

        assert data["format_version"] == "2025"
        assert data["created_by"]["tool"] == "flavor"
        assert data["build_host"]["platform"] == "darwin_arm64"
        assert data["package_info"]["size_bytes"] == 1024
        assert data["created_at"].endswith("Z")

    def test_json_deserialization(self) -> None:
        """Test JSON deserialization."""
        json_str = """{
            "format_version": "2025",
            "format_name": "Progressive Secure Package Format",
            "created_at": "2024-01-20T10:30:00Z",
            "created_by": {"tool": "flavor", "version": "0.1.0"},
            "build_host": {"platform": "linux_amd64"},
            "package_info": {"compression": "zstd"},
            "flags_interpretation": {"python_included": true},
            "sections": {"uv": {"version": "0.1.18"}}
        }"""

        meta = PSPFMetadata.from_json(json_str)
        assert meta.format_version == "2025"
        assert meta.created_by["tool"] == "flavor"
        assert meta.build_host["platform"] == "linux_amd64"
        assert meta.package_info["compression"] == "zstd"
        assert meta.flags_interpretation["python_included"] is True
        assert meta.sections["uv"]["version"] == "0.1.18"
        assert isinstance(meta.created_at, datetime)

    def test_roundtrip_serialization(self) -> None:
        """Test that serialization/deserialization preserves data."""
        original = PSPFMetadata(
            created_by={"tool": "test", "version": "1.0"},
            flags_interpretation={"dev_mode": True, "flags": 11},
        )

        json_str = original.to_json()
        restored = PSPFMetadata.from_json(json_str)

        assert restored.created_by == original.created_by
        assert restored.flags_interpretation == original.flags_interpretation
        assert abs((restored.created_at - original.created_at).total_seconds()) < 1


class TestPackageMetadata:
    """Test package metadata model."""

    def test_required_fields(self) -> None:
        """Test that required fields must be provided."""
        with pytest.raises(TypeError):
            PackageMetadata()

        meta = PackageMetadata(name="test-package", version="1.0.0")
        assert meta.name == "test-package"
        assert meta.version == "1.0.0"
        assert meta.description == ""
        assert meta.author == {}
        assert meta.keywords == []

    def test_full_metadata(self) -> None:
        """Test complete metadata example."""
        meta = PackageMetadata(
            name="example-package",
            version="2.3.4",
            description="Example package",
            author={"name": "Example Corp", "email": "dev@example.com"},
            license="MPL-2.0",
            homepage="https://example.com",
            repository={"type": "git", "url": "https://github.com/example/package"},
            keywords=["packaging", "example"],
            supported_platforms=["darwin_arm64", "linux_amd64"],
            requirements={"python": ">=3.9"},
        )

        json_str = meta.to_json()
        data = json.loads(json_str)

        assert data["name"] == "example-package"
        assert data["version"] == "2.3.4"
        assert data["author"]["email"] == "dev@example.com"
        assert "darwin_arm64" in data["supported_platforms"]

    def test_metadata_roundtrip(self) -> None:
        """Test serialization roundtrip."""
        original = PackageMetadata(
            name="test",
            version="0.1.0",
            keywords=["test", "demo"],
            metadata={"build_date": "2024-01-20", "git_sha": "abc123"},
        )

        restored = PackageMetadata.from_json(original.to_json())
        assert restored.name == original.name
        assert restored.keywords == original.keywords
        assert restored.metadata == original.metadata


class TestMetadataBundle:
    """Test metadata bundle operations."""

    def test_minimal_bundle_creation(self) -> None:
        """Test creating minimal metadata bundle."""
        bundle = create_minimal_metadata(
            name="test-package", version="1.0.0", entry_point="test_package:main"
        )

        assert bundle.package.name == "test-package"
        assert bundle.package.version == "1.0.0"
        assert "self-contained test-package package" in bundle.package.description
        assert bundle.runtime.entry_point == "test_package:main"
        assert bundle.pspf.created_by["tool"] == "flavor"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_json_objects(self) -> None:
        """Test handling of empty JSON objects."""
        json_str = "{}"

        meta = PSPFMetadata.from_json(json_str)
        assert meta.format_version == "2025"

        with pytest.raises(TypeError):
            PackageMetadata.from_json(json_str)

        with pytest.raises(TypeError):
            RuntimeConfig.from_json(json_str)

    def test_extra_fields_ignored(self) -> None:
        """Test that extra fields in JSON are ignored."""
        json_str = """{
            "name": "test",
            "version": "1.0",
            "custom_field": "custom_value"
        }"""

        meta = PackageMetadata.from_json(json_str)
        assert meta.name == "test"
        assert not hasattr(meta, "custom_field")

# 📦🍜🧪🪄
