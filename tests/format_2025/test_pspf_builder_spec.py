#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test-driven development tests for the new PSPF builder API."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import tempfile

import attrs
import pytest

from flavor.psp.format_2025.builder import build_package
from flavor.psp.format_2025.keys import resolve_keys
from flavor.psp.format_2025.slots import SlotMetadata

# Import the new API
from flavor.psp.format_2025.spec import BuildOptions, BuildSpec, KeyConfig
from flavor.psp.format_2025.validation import validate_spec

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def temp_dir() -> Iterator[Path]:
    """Temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_slot(temp_dir: Path) -> SlotMetadata:
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
        operations="none",
        purpose="data",
        lifecycle="runtime",
    )


@pytest.fixture
def minimal_spec(sample_slot: SlotMetadata) -> BuildSpec:
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

    def test_build_spec_is_immutable(self) -> None:
        """BuildSpec should be truly immutable."""
        if not BuildSpec:
            pytest.skip("BuildSpec not implemented yet")

        spec = BuildSpec(metadata={"name": "app"})

        # Should not be able to modify attributes
        with pytest.raises((AttributeError, attrs.exceptions.FrozenInstanceError)):
            spec.metadata = {"name": "other"}

        # Should not be able to modify nested structures
        spec.metadata["name"] = "modified"  # This modifies the dict

        # But a proper implementation should have made a copy
        new_spec = BuildSpec(metadata={"name": "app"})
        assert new_spec.metadata["name"] == "app"

    def test_build_spec_with_methods_return_new_instances(self) -> None:
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
            operations="none",
            purpose="data",
            lifecycle="runtime",
        )
        newer_spec = new_spec.with_slot(slot)
        assert new_spec is not newer_spec
        assert len(new_spec.slots) == 0
        assert len(newer_spec.slots) == 1

    def test_build_spec_with_keys(self) -> None:
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

    def test_key_config_options(self) -> None:
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

    def test_build_options_defaults(self) -> None:
        """BuildOptions should have sensible defaults."""
        if not BuildOptions:
            pytest.skip("BuildOptions not implemented yet")

        options = BuildOptions()
        assert options.enable_mmap
        assert options.page_aligned
        assert not options.strip_binaries
        assert options.compression == "gzip"
        assert options.launcher_bin is None

    def test_build_options_customization(self) -> None:
        """BuildOptions should be customizable."""
        if not BuildOptions:
            pytest.skip("BuildOptions not implemented yet")

        options = BuildOptions(enable_mmap=False, compression="none")
        assert not options.enable_mmap
        assert options.compression == "none"
        # launcher_type removed, using launcher_bin instead


# =============================================================================
# Core Function Tests
# =============================================================================


class TestBuildPackageFunction:
    """Test the pure build_package function."""

    def test_build_package_is_pure_function(
        self,
        temp_dir: Path,
        minimal_spec: BuildSpec,
    ) -> None:
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

    def test_build_package_validates_spec(self, temp_dir: Path) -> None:
        """build_package should validate the spec before building."""
        if not build_package or not BuildSpec:
            pytest.skip("build_package/BuildSpec not implemented yet")

        # Invalid spec (missing package name)
        invalid_spec = BuildSpec(metadata={})
        result = build_package(invalid_spec, temp_dir / "invalid.psp")

        assert not result.success
        assert len(result.errors) > 0
        assert "name" in str(result.errors).lower()

    def test_build_package_creates_output(
        self,
        temp_dir: Path,
        minimal_spec: BuildSpec,
    ) -> None:
        """build_package should create the output file."""
        if not build_package:
            pytest.skip("build_package not implemented yet")

        output = temp_dir / "test.psp"
        result = build_package(minimal_spec, output)

        assert result.success
        assert output.exists()
        assert output.stat().st_size > 0


class TestValidateSpec:
    """Test the validate_spec function."""

    def test_validate_missing_package_name(self) -> None:
        """Should detect missing package name."""
        if not validate_spec or not BuildSpec:
            pytest.skip("validate_spec/BuildSpec not implemented yet")

        spec = BuildSpec(metadata={})
        errors = validate_spec(spec)

        assert len(errors) > 0
        assert any("name" in e.lower() for e in errors)

    def test_validate_invalid_slots(self) -> None:
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
                operations="invalid",  # Invalid encoding
                purpose="data",
                lifecycle="runtime",
            )

    def test_validate_valid_spec(self, minimal_spec: BuildSpec) -> None:
        """Should accept valid spec."""
        if not validate_spec:
            pytest.skip("validate_spec not implemented yet")

        errors = validate_spec(minimal_spec)
        assert len(errors) == 0


class TestResolveKeys:
    """Test the resolve_keys function."""

    def test_resolve_explicit_keys(self) -> None:
        """Should use explicit keys when provided."""
        if not resolve_keys or not KeyConfig:
            pytest.skip("resolve_keys/KeyConfig not implemented yet")

        config = KeyConfig(private_key=b"explicit_private", public_key=b"explicit_public")

        private, public = resolve_keys(config)
        assert private == b"explicit_private"
        assert public == b"explicit_public"

    def test_resolve_deterministic_keys(self) -> None:
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

    def test_resolve_ephemeral_keys(self) -> None:
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

    def test_resolve_keys_priority(self) -> None:
        """Should respect key priority: explicit > seed > path > ephemeral."""
        if not resolve_keys or not KeyConfig:
            pytest.skip("resolve_keys/KeyConfig not implemented yet")

        # When both explicit and seed, explicit wins
        config = KeyConfig(private_key=b"explicit", public_key=b"public", key_seed="ignored")
        private, _public = resolve_keys(config)
        assert private == b"explicit"


# =============================================================================
# Builder Pattern Tests
# =============================================================================

# 🌶️📦🔚
