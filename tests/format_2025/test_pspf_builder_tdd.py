#!/usr/bin/env python3
"""
Test-Driven Development tests for the new PSPF builder API.
Written BEFORE implementation to drive the design.
"""

import tempfile
from pathlib import Path
from typing import Tuple
import pytest
import attrs

# Import the new API
from flavor.psp.format_2025.spec import BuildSpec, KeyConfig, BuildOptions, BuildResult
from flavor.psp.format_2025.builder import build_package, PSPFBuilder
from flavor.psp.format_2025.validation import validate_spec
from flavor.psp.format_2025.keys import resolve_keys

from flavor.psp.format_2025.slots import SlotMetadata


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def temp_dir():
    """Temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_slot(temp_dir):
    """Create a sample slot for testing."""
    test_file = temp_dir / "test.txt"
    test_file.write_text("Hello, World!")

    return SlotMetadata(
        index=0,
        id="test",
        source=str(test_file),
        target="test",
        size=len("Hello, World!"),
        checksum="abc123",
        encoding="none",
        purpose="data",
        lifecycle="runtime",
    )


@pytest.fixture
def minimal_spec(sample_slot):
    """Create minimal valid BuildSpec."""
    from flavor.psp.format_2025.spec import KeyConfig

    return BuildSpec(
        metadata={"package": {"name": "test", "version": "1.0"}},
        slots=[sample_slot],
        keys=KeyConfig(key_seed="test-deterministic"),  # Use deterministic keys
    )


# =============================================================================
# Core Data Structure Tests
# =============================================================================


class TestBuildSpec:
    """Test the immutable BuildSpec data structure."""

    def test_build_spec_is_immutable(self):
        """BuildSpec should be truly immutable."""
        if not BuildSpec:
            pytest.skip("BuildSpec not implemented yet")

        spec = BuildSpec(metadata={"name": "app"})

        # Should not be able to modify attributes
        with pytest.raises((AttributeError, attrs.exceptions.FrozenInstanceError)):
            spec.metadata = {"name": "other"}

        # Should not be able to modify nested structures
        original_metadata = spec.metadata
        spec.metadata["name"] = "modified"  # This modifies the dict

        # But a proper implementation should have made a copy
        new_spec = BuildSpec(metadata={"name": "app"})
        assert new_spec.metadata["name"] == "app"

    def test_build_spec_with_methods_return_new_instances(self):
        """with_* methods should return new instances."""
        if not BuildSpec:
            pytest.skip("BuildSpec not implemented yet")

        spec = BuildSpec(metadata={"name": "app"})

        # with_metadata should return new instance
        new_spec = spec.with_metadata(version="1.0")
        assert spec is not new_spec
        assert spec.metadata == {"name": "app"}
        assert new_spec.metadata == {"name": "app", "version": "1.0"}

        # with_slot should return new instance
        slot = SlotMetadata(
            index=0,
            id="test",
            source="",
            target="test",
            size=10,
            checksum="abc",
            encoding="none",
            purpose="data",
            lifecycle="runtime",
        )
        newer_spec = new_spec.with_slot(slot)
        assert new_spec is not newer_spec
        assert len(new_spec.slots) == 0
        assert len(newer_spec.slots) == 1

    def test_build_spec_with_keys(self):
        """BuildSpec should support key configuration."""
        if not BuildSpec or not KeyConfig:
            pytest.skip("BuildSpec/KeyConfig not implemented yet")

        spec = BuildSpec()
        key_config = KeyConfig(key_seed="test123")

        new_spec = spec.with_keys(key_config)
        assert spec.keys.key_seed is None
        assert new_spec.keys.key_seed == "test123"


class TestKeyConfig:
    """Test the KeyConfig data structure."""

    def test_key_config_options(self):
        """KeyConfig should support all key options."""
        if not KeyConfig:
            pytest.skip("KeyConfig not implemented yet")

        # Default should have no keys
        config = KeyConfig()
        assert config.private_key is None
        assert config.public_key is None
        assert config.key_seed is None
        assert config.key_path is None

        # Should support explicit keys
        config = KeyConfig(private_key=b"private", public_key=b"public")
        assert config.private_key == b"private"
        assert config.public_key == b"public"

        # Should support seed
        config = KeyConfig(key_seed="deterministic")
        assert config.key_seed == "deterministic"

        # Should support key path
        config = KeyConfig(key_path=Path("/path/to/keys"))
        assert config.key_path == Path("/path/to/keys")


class TestBuildOptions:
    """Test the BuildOptions data structure."""

    def test_build_options_defaults(self):
        """BuildOptions should have sensible defaults."""
        if not BuildOptions:
            pytest.skip("BuildOptions not implemented yet")

        options = BuildOptions()
        assert options.enable_mmap == True
        assert options.page_aligned == True
        assert options.strip_binaries == False
        assert options.compression == "gzip"
        assert options.launcher_bin == None

    def test_build_options_customization(self):
        """BuildOptions should be customizable."""
        if not BuildOptions:
            pytest.skip("BuildOptions not implemented yet")

        options = BuildOptions(enable_mmap=False, compression="none")
        assert options.enable_mmap == False
        assert options.compression == "none"
        # launcher_type removed, using launcher_bin instead


# =============================================================================
# Core Function Tests
# =============================================================================


class TestBuildPackageFunction:
    """Test the pure build_package function."""

    def test_build_package_is_pure_function(self, temp_dir, minimal_spec):
        """build_package should be a pure function with no side effects."""
        if not build_package:
            pytest.skip("build_package not implemented yet")

        output1 = temp_dir / "out1.psp"
        output2 = temp_dir / "out2.psp"

        # Same input should produce consistent results
        result1 = build_package(minimal_spec, output1)
        result2 = build_package(minimal_spec, output2)

        assert result1.success == result2.success
        assert result1.errors == result2.errors

        # Files should have same structure (not necessarily byte-identical due to timestamps)
        if result1.success:
            assert output1.stat().st_size == output2.stat().st_size

    def test_build_package_validates_spec(self, temp_dir):
        """build_package should validate the spec before building."""
        if not build_package or not BuildSpec:
            pytest.skip("build_package/BuildSpec not implemented yet")

        # Invalid spec (missing package name)
        invalid_spec = BuildSpec(metadata={})
        result = build_package(invalid_spec, temp_dir / "invalid.psp")

        assert result.success == False
        assert len(result.errors) > 0
        assert "name" in str(result.errors).lower()

    def test_build_package_creates_output(self, temp_dir, minimal_spec):
        """build_package should create the output file."""
        if not build_package:
            pytest.skip("build_package not implemented yet")

        output = temp_dir / "test.psp"
        result = build_package(minimal_spec, output)

        assert result.success == True
        assert output.exists()
        assert output.stat().st_size > 0


class TestValidateSpec:
    """Test the validate_spec function."""

    def test_validate_missing_package_name(self):
        """Should detect missing package name."""
        if not validate_spec or not BuildSpec:
            pytest.skip("validate_spec/BuildSpec not implemented yet")

        spec = BuildSpec(metadata={})
        errors = validate_spec(spec)

        assert len(errors) > 0
        assert any("name" in e.lower() for e in errors)

    def test_validate_invalid_slots(self):
        """Should detect invalid slots."""
        if not validate_spec or not BuildSpec:
            pytest.skip("validate_spec/BuildSpec not implemented yet")

        with pytest.raises(ValueError):
            SlotMetadata(
                index=0,
                id="",  # Invalid: empty id
                source="",
                target="",
                size=-1,  # Invalid: negative size
                checksum="",
                encoding="invalid",  # Invalid encoding
                purpose="data",
                lifecycle="runtime",
            )

    def test_validate_valid_spec(self, minimal_spec):
        """Should accept valid spec."""
        if not validate_spec:
            pytest.skip("validate_spec not implemented yet")

        errors = validate_spec(minimal_spec)
        assert len(errors) == 0


class TestResolveKeys:
    """Test the resolve_keys function."""

    def test_resolve_explicit_keys(self):
        """Should use explicit keys when provided."""
        if not resolve_keys or not KeyConfig:
            pytest.skip("resolve_keys/KeyConfig not implemented yet")

        config = KeyConfig(
            private_key=b"explicit_private", public_key=b"explicit_public"
        )

        private, public = resolve_keys(config)
        assert private == b"explicit_private"
        assert public == b"explicit_public"

    def test_resolve_deterministic_keys(self):
        """Should generate deterministic keys from seed."""
        if not resolve_keys or not KeyConfig:
            pytest.skip("resolve_keys/KeyConfig not implemented yet")

        config = KeyConfig(key_seed="test_seed")

        # Same seed should produce same keys
        private1, public1 = resolve_keys(config)
        private2, public2 = resolve_keys(config)

        assert private1 == private2
        assert public1 == public2
        assert len(private1) == 32  # Ed25519 private key size
        assert len(public1) == 32  # Ed25519 public key size

    def test_resolve_ephemeral_keys(self):
        """Should generate ephemeral keys when no config."""
        if not resolve_keys or not KeyConfig:
            pytest.skip("resolve_keys/KeyConfig not implemented yet")

        config = KeyConfig()  # No keys specified

        # Should generate different keys each time
        private1, public1 = resolve_keys(config)
        private2, public2 = resolve_keys(config)

        assert private1 != private2
        assert public1 != public2
        assert len(private1) == 32
        assert len(public1) == 32

    def test_resolve_keys_priority(self):
        """Should respect key priority: explicit > seed > path > ephemeral."""
        if not resolve_keys or not KeyConfig:
            pytest.skip("resolve_keys/KeyConfig not implemented yet")

        # When both explicit and seed, explicit wins
        config = KeyConfig(
            private_key=b"explicit", public_key=b"public", key_seed="ignored"
        )
        private, public = resolve_keys(config)
        assert private == b"explicit"


# =============================================================================
# Builder Pattern Tests
# =============================================================================


class TestPSPFBuilder:
    """Test the fluent builder interface."""

    def test_builder_create(self):
        """Should create new builder."""
        if not PSPFBuilder:
            pytest.skip("PSPFBuilder not implemented yet")

        builder = PSPFBuilder.create()
        assert builder is not None
        assert isinstance(builder, PSPFBuilder)

    def test_builder_fluent_interface(self, temp_dir):
        """Should support fluent/chainable interface."""
        if not PSPFBuilder:
            pytest.skip("PSPFBuilder not implemented yet")

        output = temp_dir / "fluent.psp"

        result = (
            PSPFBuilder.create()
            .metadata(name="app", version="1.0")
            .add_slot("main", b"print('hello')")
            .add_slot("config", b'{"key": "value"}')
            .with_keys(seed="test123")
            .build(output)
        )

        assert result.success == True
        assert output.exists()

    def test_builder_incremental(self, temp_dir):
        """Should support incremental building."""
        if not PSPFBuilder:
            pytest.skip("PSPFBuilder not implemented yet")

        builder = PSPFBuilder.create()

        # Add metadata
        builder = builder.metadata(name="incremental", version="2.0")

        # Add slots one by one
        for i in range(3):
            builder = builder.add_slot(f"file{i}", f"data{i}".encode())

        # Set keys
        builder = builder.with_keys(seed="incremental")

        # Build
        output = temp_dir / "incremental.psp"
        result = builder.build(output)

        assert result.success == True
        assert output.exists()

    def test_builder_immutable_chaining(self):
        """Each builder method should return new instance."""
        if not PSPFBuilder:
            pytest.skip("PSPFBuilder not implemented yet")

        builder1 = PSPFBuilder.create()
        builder2 = builder1.metadata(name="test")
        builder3 = builder2.add_slot("data", b"content")

        # Each should be different instance
        assert builder1 is not builder2
        assert builder2 is not builder3

        # Original should be unchanged
        assert builder1._spec.metadata == {}
        assert builder2._spec.metadata == {"name": "test"}
        assert len(builder3._spec.slots) == 1

    def test_builder_with_path_slots(self, temp_dir):
        """Should support adding slots from file paths."""
        if not PSPFBuilder:
            pytest.skip("PSPFBuilder not implemented yet")

        # Create test files
        file1 = temp_dir / "data.txt"
        file1.write_text("file content")

        file2 = temp_dir / "config.json"
        file2.write_text('{"setting": "value"}')

        output = temp_dir / "with_files.psp"

        result = (
            PSPFBuilder.create()
            .metadata(name="files", version="1.0")
            .add_slot("data", file1)
            .add_slot("config", file2)
            .build(output)
        )

        assert result.success == True
        assert output.exists()


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """End-to-end integration tests."""

    def test_full_build_pipeline(self, temp_dir):
        """Test complete build pipeline."""
        if not all([BuildSpec, build_package, PSPFBuilder]):
            pytest.skip("Not all components implemented yet")

        # Create test data
        main_file = temp_dir / "main.py"
        main_file.write_text("print('Hello from PSPF!')")

        config_file = temp_dir / "config.json"
        config_file.write_text('{"debug": true}')

        # Build using new API
        output = temp_dir / "complete.psp"

        result = (
            PSPFBuilder.create()
            .metadata(
                format="PSPF/2025",
                package={
                    "name": "complete-app",
                    "version": "1.0.0",
                    "description": "A complete test application",
                },
            )
            .add_slot("main", main_file)
            .add_slot("config", config_file)
            .with_keys(seed="integration_test")
            .with_options(compression="gzip", enable_mmap=True, page_aligned=True)
            .build(output)
        )

        assert result.success == True
        assert output.exists()

        # Verify the package can be read
        from flavor.psp.format_2025.reader import PSPFReader

        reader = PSPFReader(output)

        # Should have correct metadata
        metadata = reader.read_metadata()
        assert metadata["package"]["name"] == "complete-app"
        assert metadata["package"]["version"] == "1.0.0"

        # Should have correct slots
        metadata = reader.read_metadata()
        slots_metadata = metadata.get("slots", [])
        assert len(slots_metadata) == 2
        assert any(s["name"] == "main" for s in slots_metadata)
        assert any(s["name"] == "config" for s in slots_metadata)

    def test_error_handling(self, temp_dir):
        """Test comprehensive error handling."""
        if not all([PSPFBuilder, BuildResult]):
            pytest.skip("Not all components implemented yet")

        # Missing required metadata
        result = (
            PSPFBuilder.create()
            .add_slot("data", b"content")
            .build(temp_dir / "invalid.psp")
        )

        assert result.success == False
        assert len(result.errors) > 0

        # Invalid slot
        result = (
            PSPFBuilder.create()
            .metadata(name="test")
            .add_slot("", b"")  # Empty name and data
            .build(temp_dir / "invalid2.psp")
        )

        assert result.success == False
        assert len(result.errors) > 0

        # Non-existent file
        result = (
            PSPFBuilder.create()
            .metadata(name="test")
            .add_slot("missing", Path("/does/not/exist"))
            .build(temp_dir / "invalid3.psp")
        )

        assert result.success == False
        assert any(
            "not found" in e.lower() or "exist" in e.lower() for e in result.errors
        )


# =============================================================================
# Performance Tests
# =============================================================================


class TestPerformance:
    """Test performance characteristics."""

    @pytest.mark.slow
    def test_large_package_build(self, temp_dir):
        """Should handle large packages efficiently."""
        if not PSPFBuilder:
            pytest.skip("PSPFBuilder not implemented yet")

        # Create a large file (10MB)
        large_file = temp_dir / "large.bin"
        large_file.write_bytes(b"X" * (10 * 1024 * 1024))

        output = temp_dir / "large.psp"

        import time

        start = time.time()

        result = (
            PSPFBuilder.create()
            .metadata(name="large-package")
            .add_slot("bigfile", large_file)
            .build(output)
        )

        elapsed = time.time() - start

        assert result.success == True
        assert elapsed < 5.0  # Should complete in reasonable time

    @pytest.mark.slow
    def test_many_slots_build(self, temp_dir):
        """Should handle many slots efficiently."""
        if not PSPFBuilder:
            pytest.skip("PSPFBuilder not implemented yet")

        builder = PSPFBuilder.create().metadata(name="many-slots")

        # Add 100 small slots
        for i in range(100):
            builder = builder.add_slot(f"slot{i}", f"data{i}".encode())

        output = temp_dir / "many_slots.psp"

        import time

        start = time.time()
        result = builder.build(output)
        elapsed = time.time() - start

        assert result.success == True
        assert elapsed < 2.0  # Should be fast even with many slots


if __name__ == "__main__":
    # Run tests to show RED phase
    pytest.main([__file__, "-v", "--tb=short"])
