"""Tests for PSPF v0.1 metadata models."""

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
        assert meta.format_version == "0.1"
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

        assert data["format_version"] == "0.1"
        assert data["created_by"]["tool"] == "flavor"
        assert data["build_host"]["platform"] == "darwin_arm64"
        assert data["package_info"]["size_bytes"] == 1024
        assert data["created_at"].endswith("Z")

    def test_json_deserialization(self) -> None:
        """Test JSON deserialization."""
        json_str = """{
            "format_version": "0.1",
            "format_name": "Progressive Secure Package Format",
            "created_at": "2024-01-20T10:30:00Z",
            "created_by": {"tool": "flavor", "version": "0.1.0"},
            "build_host": {"platform": "linux_amd64"},
            "package_info": {"compression": "zstd"},
            "flags_interpretation": {"python_included": true},
            "sections": {"uv": {"version": "0.1.18"}}
        }"""

        meta = PSPFMetadata.from_json(json_str)
        assert meta.format_version == "0.1"
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
        # Timestamps should be close but might differ by microseconds
        assert abs((restored.created_at - original.created_at).total_seconds()) < 1


class TestPackageMetadata:
    """Test package metadata model."""

    def test_required_fields(self) -> None:
        """Test that required fields must be provided."""
        with pytest.raises(TypeError):
            PackageMetadata()  # Missing name and version

        meta = PackageMetadata(name="test-provider", version="1.0.0")
        assert meta.name == "test-provider"
        assert meta.version == "1.0.0"
        assert meta.description == ""
        assert meta.author == {}
        assert meta.keywords == []

    def test_full_metadata(self) -> None:
        """Test complete metadata example."""
        meta = PackageMetadata(
            name="terraform-provider-example",
            version="2.3.4",
            description="Example Terraform provider",
            author={"name": "Example Corp", "email": "dev@example.com"},
            license="MPL-2.0",
            homepage="https://example.com",
            repository={"type": "git", "url": "https://github.com/example/provider"},
            keywords=["terraform", "provider", "example"],
            terraform={"protocol_version": 6, "provider_name": "example"},
            supported_platforms=["darwin_arm64", "linux_amd64"],
            requirements={"terraform": ">=1.0", "python": ">=3.9"},
        )

        json_str = meta.to_json()
        data = json.loads(json_str)

        assert data["name"] == "terraform-provider-example"
        assert data["version"] == "2.3.4"
        assert data["author"]["email"] == "dev@example.com"
        assert data["terraform"]["protocol_version"] == 6
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


class TestRuntimeConfig:
    """Test runtime configuration model."""

    def test_minimal_config(self) -> None:
        """Test minimal runtime config."""
        config = RuntimeConfig(entry_point="provider.main:serve")
        assert config.entry_point == "provider.main:serve"
        assert config.working_directory == "."
        assert config.python_executable == "./python/bin/python"
        assert config.python_args == []
        assert config.environment == {}
        assert config.inherit_env == []

    def test_full_config(self) -> None:
        """Test complete runtime config."""
        config = RuntimeConfig(
            entry_point="my_provider:main",
            entry_module="my_provider",
            entry_function="main",
            working_directory="/app",
            python_executable="/usr/bin/python3",
            python_args=["-u", "-O"],
            environment={"PYTHONPATH": "./lib", "DEBUG": "1"},
            inherit_env=["HOME", "USER", "PATH"],
            capabilities={"network": True, "filesystem": {"read_only": True}},
            resource_limits={"max_memory_mb": 512, "timeout_seconds": 300},
            logging={"level": "INFO", "format": "json"},
        )

        data = json.loads(config.to_json())
        assert data["entry_point"] == "my_provider:main"
        assert data["python_args"] == ["-u", "-O"]
        assert data["environment"]["DEBUG"] == "1"
        assert data["capabilities"]["network"] is True
        assert data["resource_limits"]["max_memory_mb"] == 512
        assert data["logging"]["format"] == "json"

    def test_config_with_security_restrictions(self) -> None:
        """Test config with security restrictions."""
        config = RuntimeConfig(
            entry_point="secure_provider:serve",
            capabilities={
                "network": {
                    "allowed": True,
                    "restrictions": {
                        "allowed_domains": ["*.example.com"],
                        "blocked_ports": [25, 587],
                    },
                },
                "filesystem": {
                    "allowed": True,
                    "restrictions": {
                        "read_paths": ["./data", "${HOME}/.config"],
                        "write_paths": ["./tmp"],
                        "blocked_paths": ["/etc", "/usr"],
                    },
                },
                "subprocess": {"allowed": False},
            },
        )

        data = json.loads(config.to_json())
        net_caps = data["capabilities"]["network"]
        assert net_caps["restrictions"]["allowed_domains"] == ["*.example.com"]
        assert 25 in net_caps["restrictions"]["blocked_ports"]

        fs_caps = data["capabilities"]["filesystem"]
        assert "./data" in fs_caps["restrictions"]["read_paths"]
        assert "/etc" in fs_caps["restrictions"]["blocked_paths"]


class TestDependencyInfo:
    """Test dependency information model."""

    def test_minimal_dependencies(self) -> None:
        """Test minimal dependency info."""
        deps = DependencyInfo()
        assert deps.resolver == "uv"
        assert deps.direct_dependencies == []
        assert deps.resolved_packages == {}
        assert deps.total_packages == 0
        assert isinstance(deps.resolution_date, datetime)

    def test_complete_dependencies(self) -> None:
        """Test complete dependency info."""
        deps = DependencyInfo(
            resolver="uv",
            resolver_version="0.1.18",
            python_version="3.13.0",
            platform={"os": "darwin", "arch": "arm64"},
            direct_dependencies=["pyvider>=0.7.0", "boto3>=1.34.0"],
            resolved_packages={
                "pyvider": {
                    "version": "0.7.11",
                    "source": "pypi",
                    "hash": "sha256:abc123...",
                    "size_bytes": 145920,
                },
                "boto3": {
                    "version": "1.34.25",
                    "source": "pypi",
                    "hash": "sha256:def456...",
                    "size_bytes": 3854720,
                },
            },
            dependency_graph={
                "pyvider": ["attrs", "grpcio"],
                "boto3": ["botocore", "s3transfer"],
            },
            total_packages=15,
            total_size_bytes=25000000,
        )

        json_str = deps.to_json()
        data = json.loads(json_str)

        assert data["resolver_version"] == "0.1.18"
        assert data["python_version"] == "3.13.0"
        assert data["platform"]["os"] == "darwin"
        assert len(data["direct_dependencies"]) == 2
        assert data["resolved_packages"]["pyvider"]["version"] == "0.7.11"
        assert data["dependency_graph"]["boto3"] == ["botocore", "s3transfer"]
        assert data["total_packages"] == 15

    def test_vulnerability_info(self) -> None:
        """Test vulnerability check information."""
        deps = DependencyInfo(
            vulnerabilities_check={
                "date": "2024-01-20T10:00:00Z",
                "found": 2,
                "details": [
                    {
                        "package": "urllib3",
                        "severity": "medium",
                        "cve": "CVE-2023-1234",
                    },
                    {"package": "requests", "severity": "low", "cve": "CVE-2023-5678"},
                ],
                "database_version": "2024.01.20",
            }
        )

        data = json.loads(deps.to_json())
        vuln = data["vulnerabilities_check"]
        assert vuln["found"] == 2
        assert len(vuln["details"]) == 2
        assert vuln["details"][0]["package"] == "urllib3"


class TestChecksumInfo:
    """Test checksum information model."""

    def test_minimal_checksums(self) -> None:
        """Test minimal checksum info."""
        checksums = ChecksumInfo()
        assert checksums.algorithm == "sha256"
        assert checksums.sections == {}
        assert checksums.payload_contents == {}
        assert checksums.total_package_checksum is None

    def test_complete_checksums(self) -> None:
        """Test complete checksum info."""
        checksums = ChecksumInfo(
            algorithm="sha256",
            sections={
                "uv": {
                    "size_bytes": 4587520,
                    "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "compressed": True,
                    "compression_algorithm": "zstd",
                },
                "python": {
                    "size_bytes": 89234432,
                    "checksum": "a665a45920422f83a63e5b7e0e5f3d7c8f3e9d2a4c5f8e9b0c1d2e3f4a5b6c7d8e9f0",
                    "compressed": True,
                    "compression_algorithm": "gzip",
                },
            },
            payload_contents={
                "site-packages/provider/__init__.py": "1a2b3c4d",
                "site-packages/provider/main.py": "5e6f7a8b",
            },
            total_package_checksum="sha256:fedcba0987654321fedcba0987654321fedcba0987654321fedcba0987654321",
        )

        data = json.loads(checksums.to_json())
        assert data["algorithm"] == "sha256"
        assert data["sections"]["uv"]["size_bytes"] == 4587520
        assert data["sections"]["python"]["compression_algorithm"] == "gzip"
        assert len(data["payload_contents"]) == 2
        assert data["total_package_checksum"].startswith("sha256:")


class TestMetadataBundle:
    """Test metadata bundle operations."""

    def test_minimal_bundle_creation(self) -> None:
        """Test creating minimal metadata bundle."""
        bundle = create_minimal_metadata(
            name="test-provider", version="1.0.0", entry_point="test_provider:main"
        )

        assert bundle.package.name == "test-provider"
        assert bundle.package.version == "1.0.0"
        assert bundle.package.description == "test-provider Terraform provider"
        assert bundle.runtime.entry_point == "test_provider:main"
        assert bundle.pspf.created_by["tool"] == "flavor"

    def test_bundle_write_to_directory(self) -> None:
        """Test writing bundle to directory with correct permissions."""
        bundle = create_minimal_metadata("test", "1.0", "test:main")

        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_dir = Path(tmpdir) / "metadata"
            bundle.write_to_directory(metadata_dir)

            # Check directory was created with correct permissions
            assert metadata_dir.exists()
            assert metadata_dir.is_dir()
            assert oct(metadata_dir.stat().st_mode)[-3:] == "700"

            # Check all files exist with correct permissions
            expected_files = [
                "pspf.json",
                "package.json",
                "runtime.json",
                "dependencies.json",
                "checksums.json",
            ]

            for filename in expected_files:
                filepath = metadata_dir / filename
                assert filepath.exists()
                assert filepath.is_file()
                assert oct(filepath.stat().st_mode)[-3:] == "600"

                # Verify content is valid JSON
                content = filepath.read_text()
                json.loads(content)  # Should not raise

    def test_bundle_read_from_directory(self) -> None:
        """Test reading bundle from directory."""
        # Create and write a bundle
        original = MetadataBundle(
            pspf=PSPFMetadata(
                created_by={"tool": "test", "version": "2.0"},
                package_info={"test": True},
            ),
            package=PackageMetadata(
                name="read-test", version="3.2.1", keywords=["test", "read"]
            ),
            runtime=RuntimeConfig(
                entry_point="read_test:serve",
                python_args=["-u"],
                environment={"TEST": "1"},
            ),
            dependencies=DependencyInfo(
                resolver_version="0.2.0",
                direct_dependencies=["pyvider>=0.8.0"],
                total_packages=5,
            ),
            checksums=ChecksumInfo(
                sections={"payload": {"size_bytes": 1024}},
                total_package_checksum="sha256:test123",
            ),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_dir = Path(tmpdir) / "metadata"
            original.write_to_directory(metadata_dir)

            # Read it back
            restored = MetadataBundle.read_from_directory(metadata_dir)

            # Verify all data was preserved
            assert restored.pspf.created_by == original.pspf.created_by
            assert restored.pspf.package_info == original.pspf.package_info

            assert restored.package.name == "read-test"
            assert restored.package.version == "3.2.1"
            assert restored.package.keywords == ["test", "read"]

            assert restored.runtime.entry_point == "read_test:serve"
            assert restored.runtime.python_args == ["-u"]
            assert restored.runtime.environment == {"TEST": "1"}

            assert restored.dependencies.resolver_version == "0.2.0"
            assert restored.dependencies.total_packages == 5

            assert restored.checksums.sections["payload"]["size_bytes"] == 1024
            assert restored.checksums.total_package_checksum == "sha256:test123"

    def test_bundle_missing_files_error(self) -> None:
        """Test that reading from directory with missing files raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_dir = Path(tmpdir) / "metadata"
            metadata_dir.mkdir(mode=0o700)

            # Only create some files
            (metadata_dir / "pspf.json").write_text('{"format_version": "0.1"}')
            (metadata_dir / "pspf.json").chmod(0o600)

            # Should raise when trying to read incomplete bundle
            with pytest.raises(FileNotFoundError):
                MetadataBundle.read_from_directory(metadata_dir)


class TestDateTimeSerialization:
    """Test datetime serialization/deserialization."""

    def test_datetime_format(self) -> None:
        """Test that datetimes are serialized in ISO format with Z suffix."""
        # Test with PSPFMetadata
        meta = PSPFMetadata()
        json_str = meta.to_json()
        data = json.loads(json_str)
        assert data["created_at"].endswith("Z")
        assert "T" in data["created_at"]

        # Test with DependencyInfo
        deps = DependencyInfo()
        json_str = deps.to_json()
        data = json.loads(json_str)
        assert data["resolution_date"].endswith("Z")

        # Test with ChecksumInfo
        checksums = ChecksumInfo()
        json_str = checksums.to_json()
        data = json.loads(json_str)
        assert data["generated_at"].endswith("Z")

    def test_datetime_parsing(self) -> None:
        """Test parsing datetime from JSON."""
        # Test various datetime formats
        test_dates = [
            "2024-01-20T10:30:45Z",
            "2024-01-20T10:30:45.123Z",
            "2024-01-20T10:30:45.123456Z",
        ]

        for date_str in test_dates:
            json_str = f'{{"format_version": "0.1", "created_at": "{date_str}"}}'
            meta = PSPFMetadata.from_json(json_str)
            assert isinstance(meta.created_at, datetime)
            assert meta.created_at.year == 2024
            assert meta.created_at.month == 1
            assert meta.created_at.day == 20


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_json_objects(self) -> None:
        """Test handling of empty JSON objects."""
        json_str = "{}"

        # PSPFMetadata should use defaults
        meta = PSPFMetadata.from_json(json_str)
        assert meta.format_version == "0.1"

        # PackageMetadata requires name/version
        with pytest.raises(TypeError):
            PackageMetadata.from_json(json_str)

        # RuntimeConfig requires entry_point
        with pytest.raises(TypeError):
            RuntimeConfig.from_json(json_str)

    def test_extra_fields_ignored(self) -> None:
        """Test that extra fields in JSON are ignored."""
        json_str = """{
            "name": "test",
            "version": "1.0",
            "custom_field": "custom_value",
            "nested": {"extra": "data"}
        }"""

        # Extra fields should be ignored
        meta = PackageMetadata.from_json(json_str)
        assert meta.name == "test"
        assert meta.version == "1.0"
        # Extra fields are not preserved in the model
        assert not hasattr(meta, "custom_field")
        assert not hasattr(meta, "nested")

    def test_unicode_handling(self) -> None:
        """Test Unicode string handling."""
        meta = PackageMetadata(
            name="test-provider",
            version="1.0.0",
            description="Provider with émoji 🚀 support",
            author={"name": "François", "company": "Société"},
        )

        json_str = meta.to_json()
        restored = PackageMetadata.from_json(json_str)

        assert restored.description == "Provider with émoji 🚀 support"
        assert restored.author["name"] == "François"
        assert restored.author["company"] == "Société"


# 📦🍜🧪🪄
