#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test-driven development tests for the new PSPF builder API."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import tempfile

import pytest

from flavor.psp.format_2025.builder import build_package
from flavor.psp.format_2025.pspf_builder import PSPFBuilder
from flavor.psp.format_2025.slots import SlotMetadata

# Import the new API
from flavor.psp.format_2025.spec import BuildResult, BuildSpec, KeyConfig

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

    return BuildSpec(
        metadata={"package": {"name": "test", "version": "1.0"}},
        slots=[sample_slot],
        keys=KeyConfig(key_seed="test-deterministic"),  # Use deterministic keys
    )


# =============================================================================
# Core Data Structure Tests
# =============================================================================


class TestPSPFBuilder:
    """Test the fluent builder interface."""

    def test_builder_create(self) -> None:
        """Should create new builder."""
        if not PSPFBuilder:
            pytest.skip("PSPFBuilder not implemented yet")

        builder = PSPFBuilder.create()
        assert builder is not None
        assert isinstance(builder, PSPFBuilder)

    def test_builder_fluent_interface(self, temp_dir: Path) -> None:
        """Should support fluent/chainable interface."""
        if not PSPFBuilder:
            pytest.skip("PSPFBuilder not implemented yet")

        output = temp_dir / "fluent.psp"

        result = (
            PSPFBuilder.create()
            .metadata(name="app", version="1.0")
            .add_slot(id="main", data=b"print('hello')")
            .add_slot(id="config", data=b'{"key": "value"}')
            .with_keys(seed="test123")
            .build(output)
        )

        assert result.success
        assert output.exists()

    def test_builder_incremental(self, temp_dir: Path) -> None:
        """Should support incremental building."""
        if not PSPFBuilder:
            pytest.skip("PSPFBuilder not implemented yet")

        builder = PSPFBuilder.create()

        # Add metadata
        builder = builder.metadata(name="incremental", version="2.0")

        # Add slots one by one
        for i in range(3):
            builder = builder.add_slot(id=f"file{i}", data=f"data{i}".encode())

        # Set keys
        builder = builder.with_keys(seed="incremental")

        # Build
        output = temp_dir / "incremental.psp"
        result = builder.build(output)

        assert result.success
        assert output.exists()

    def test_builder_immutable_chaining(self) -> None:
        """Each builder method should return new instance."""
        if not PSPFBuilder:
            pytest.skip("PSPFBuilder not implemented yet")

        builder1 = PSPFBuilder.create()
        builder2 = builder1.metadata(name="test")
        builder3 = builder2.add_slot(id="data", data=b"content")

        # Each should be different instance
        assert builder1 is not builder2
        assert builder2 is not builder3

        # Original should be unchanged
        assert builder1._spec.metadata == {}
        assert builder2._spec.metadata == {"name": "test"}
        assert len(builder3._spec.slots) == 1

    def test_builder_with_path_slots(self, temp_dir: Path) -> None:
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
            .add_slot(id="data", data=file1)
            .add_slot(id="config", data=file2)
            .build(output)
        )

        assert result.success
        assert output.exists()


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """End-to-end integration tests."""

    def test_full_build_pipeline(self, temp_dir: Path) -> None:
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
            .add_slot(id="main", data=main_file)
            .add_slot(id="config", data=config_file)
            .with_keys(seed="integration_test")
            .with_options(compression="gzip", enable_mmap=True, page_aligned=True)
            .build(output)
        )

        assert result.success
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
        # Check both possible field names for backward compatibility
        assert any(s.get("name", s.get("id")) == "main" for s in slots_metadata)
        assert any(s.get("name", s.get("id")) == "config" for s in slots_metadata)

    def test_error_handling(self, temp_dir: Path) -> None:
        """Test comprehensive error handling."""
        if not all([PSPFBuilder, BuildResult]):
            pytest.skip("Not all components implemented yet")

        # Missing required metadata
        result = PSPFBuilder.create().add_slot(id="data", data=b"content").build(temp_dir / "invalid.psp")

        assert not result.success
        assert len(result.errors) > 0

        # Invalid slot
        result = (
            PSPFBuilder.create()
            .metadata(name="test")
            .add_slot("", b"")  # Empty name and data
            .build(temp_dir / "invalid2.psp")
        )

        assert not result.success
        assert len(result.errors) > 0

        # Non-existent file
        result = (
            PSPFBuilder.create()
            .metadata(name="test")
            .add_slot(id="missing", data=Path("/does/not/exist"))
            .build(temp_dir / "invalid3.psp")
        )

        assert not result.success
        assert any("not found" in e.lower() or "exist" in e.lower() for e in result.errors)


# =============================================================================
# Performance Tests
# =============================================================================


class TestPerformance:
    """Test performance characteristics."""

    @pytest.mark.slow
    def test_large_package_build(self, temp_dir: Path) -> None:
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
            .add_slot(id="bigfile", data=large_file)
            .build(output)
        )

        elapsed = time.time() - start

        assert result.success
        assert elapsed < 5.0  # Should complete in reasonable time

    @pytest.mark.slow
    def test_many_slots_build(self, temp_dir: Path) -> None:
        """Should handle many slots efficiently."""
        if not PSPFBuilder:
            pytest.skip("PSPFBuilder not implemented yet")

        builder = PSPFBuilder.create().metadata(name="many-slots")

        # Add 100 small slots
        for i in range(100):
            builder = builder.add_slot(id=f"slot{i}", data=f"data{i}".encode())

        output = temp_dir / "many_slots.psp"

        import time

        start = time.time()
        result = builder.build(output)
        elapsed = time.time() - start

        assert result.success
        assert elapsed < 2.0  # Should be fast even with many slots


if __name__ == "__main__":
    # Run tests to show RED phase
    pytest.main([__file__, "-v", "--tb=short"])

# 🌶️📦🔚
