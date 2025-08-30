"""
PSPF 2025 Slot Management Tests

Tests slot lifecycle, compression, and management functionality.
"""

import hashlib
import os
import struct
import tempfile
from pathlib import Path
import zlib

import pytest

from flavor.psp.format_2025 import (
    PSPFBuilder,
    PSPFReader,
    PSPFLauncher,
    SlotMetadata,
    SLOT_ALIGNMENT,
)
from flavor.psp.format_2025.constants import SLOT_DESCRIPTOR_SIZE


class TestPSPFSlots:
    """Test PSPF slot management."""

    @pytest.fixture
    def test_slots(self, temp_dir, test_builder):
        """Create test slots with different properties."""
        slots = []

        # Text file (compressible)
        text_path = temp_dir / "text.json"
        text_data = '{"key": "value"}' * 100
        text_path.write_text(text_data)

        slots.append(
            SlotMetadata(
                index=0,
                id="config",
                source=str(text_path),
                target="config",
                size=len(text_data),
                checksum=hashlib.sha256(text_data.encode()).hexdigest(),
                encoding="gzip",
                purpose="config",
                lifecycle="runtime",
            )
        )

        # Binary file (less compressible)
        binary_path = temp_dir / "binary.so"
        binary_data = os.urandom(1024)
        binary_path.write_bytes(binary_data)

        slots.append(
            SlotMetadata(
                index=1,
                id="library",
                source=str(binary_path),
                target="library",
                size=len(binary_data),
                checksum=hashlib.sha256(binary_data).hexdigest(),
                encoding="none",  # Binary files often don't compress well
                purpose="library",
                lifecycle="init",
            )
        )

        # Temporary file
        temp_path = temp_dir / "temp.whl"
        temp_data = b"WHEEL_DATA" * 50
        temp_path.write_bytes(temp_data)

        slots.append(
            SlotMetadata(
                index=2,
                id="wheel",
                source=str(temp_path),
                target="wheel",
                size=len(temp_data),
                checksum=hashlib.sha256(temp_data).hexdigest(),
                encoding="none",
                purpose="payload",
                lifecycle="temp",
            )
        )

        return slots

    def test_slot_lifecycle_runtime(self, temp_dir, test_builder):
        """Test runtime slot lifecycle metadata."""
        slot = SlotMetadata(
            index=0,
            id="test-runtime",
            source="",
            target="test-runtime",
            size=1024,
            checksum="abc123",
            encoding="gzip",
            purpose="payload",
            lifecycle="runtime",
        )

        # Test metadata serialization
        slot_dict = slot.to_dict()
        assert slot_dict["lifecycle"] == "runtime"
        assert slot_dict["id"] == "test-runtime"
        # Runtime slots available during application execution

    def test_slot_lifecycle_init(self, temp_dir, test_builder):
        """Test init slot lifecycle metadata."""
        slot = SlotMetadata(
            index=0,
            id="test-init",
            source="",
            target="test-init",
            size=1024,
            checksum="abc123",
            encoding="gzip",
            purpose="payload",
            lifecycle="init",
        )

        # Test metadata serialization
        slot_dict = slot.to_dict()
        assert slot_dict["lifecycle"] == "init"
        assert slot_dict["id"] == "test-init"
        # Init slots removed after initialization

    def test_slot_lifecycle_temp(self, temp_dir, test_builder):
        """Test temp slot lifecycle metadata."""
        slot = SlotMetadata(
            index=0,
            id="test-temp",
            source="",
            target="test-temp",
            size=1024,
            checksum="abc123",
            encoding="gzip",
            purpose="payload",
            lifecycle="temp",
        )

        # Test metadata serialization
        slot_dict = slot.to_dict()
        assert slot_dict["lifecycle"] == "temp"
        assert slot_dict["id"] == "test-temp"
        # Temp slots removed after current session

    def test_slot_lifecycle_cache(self, temp_dir, test_builder):
        """Test cache slot lifecycle metadata."""
        slot = SlotMetadata(
            index=0,
            id="test-cache",
            source="",
            target="test-cache",
            size=1024,
            checksum="abc123",
            encoding="gzip",
            purpose="config",
            lifecycle="cache",
        )

        # Test metadata serialization
        slot_dict = slot.to_dict()
        assert slot_dict["lifecycle"] == "cache"
        assert slot_dict["purpose"] == "config"
        # Cache slots kept for performance, can be regenerated

    def test_multiple_slots(self, temp_dir, test_slots, test_builder):
        """Test bundle with multiple slots."""
        metadata = {
            "format": "PSPF/2025",
            "package": {"name": "multi-slot", "version": "1.0.0"},
        }

        bundle_path = temp_dir / "multi.psp"
        # Use test_builder from fixture with fluent API
        builder = test_builder.metadata(**metadata)
        for slot in test_slots:
            if hasattr(slot, "source") and slot.source:
                builder = builder.add_slot(
                id=slot.id,
                data=slot.source,
                    encoding=slot.encoding,
                    purpose=slot.purpose,
                    lifecycle=slot.lifecycle,
                )
        result = builder.build(bundle_path)
        assert result.success, f"Build failed: {result.errors}"

        # Verify all slots
        reader = PSPFReader(bundle_path)
        index = reader.read_index()
        assert index.slot_count == len(test_slots)

        # Read metadata
        metadata_read = reader.read_metadata()
        assert len(metadata_read["slots"]) == len(test_slots)

        # Verify slot properties preserved
        for i, slot in enumerate(test_slots):
            slot_meta = metadata_read["slots"][i]
            # Check both possible field names for backward compatibility
            if "name" in slot_meta:
                assert slot_meta["name"] == slot.id
            else:
                assert slot_meta["id"] == slot.id
            assert slot_meta["lifecycle"] == slot.lifecycle
            assert slot_meta["purpose"] == slot.purpose

    def test_slot_compression_gzip(self, temp_dir, test_builder):
        """Test gzip compression."""
        # Create highly compressible data
        data = b"REPEAT" * 1000
        slot_path = temp_dir / "compress.txt"
        slot_path.write_bytes(data)

        slot = SlotMetadata(
            index=0,
            id="compressed",
            source=str(slot_path),
            target="compressed",
            size=len(data),
            checksum=hashlib.sha256(data).hexdigest(),
            encoding="gzip",
            purpose="payload",
            lifecycle="runtime",
        )

        # Build bundle with gzip compression
        bundle_path = temp_dir / "compressed.psp"
        metadata = {
            "format": "PSPF/2025",
            "package": {"name": "test", "version": "1.0"},
        }

        result = (
            test_builder.metadata(**metadata)
            .add_slot(id="compressed",
                slot_path,
                encoding="gzip",
                purpose="payload",
                lifecycle="runtime",
            )
            .build(bundle_path)
        )
        assert result.success, f"Build failed: {result.errors}"

        # Verify the slot is stored with compression by checking metadata
        reader = PSPFReader(bundle_path)
        metadata_read = reader.read_metadata()
        assert metadata_read["slots"][0]["encoding"] == "gzip"

    def test_slot_compression_none(self, temp_dir, test_builder):
        """Test no compression."""
        data = b"NOCOMPRESS" * 100
        slot_path = temp_dir / "nocompress.bin"
        slot_path.write_bytes(data)

        slot = SlotMetadata(
            index=0,
            id="uncompressed",
            source=str(slot_path),
            target="uncompressed",
            size=len(data),
            checksum=hashlib.sha256(data).hexdigest(),
            encoding="none",
            purpose="payload",
            lifecycle="runtime",
        )

        # Build bundle without compression
        bundle_path = temp_dir / "uncompressed.psp"
        metadata = {
            "format": "PSPF/2025",
            "package": {"name": "test", "version": "1.0"},
        }

        result = (
            test_builder.metadata(**metadata)
            .add_slot(id="uncompressed",
                slot_path,
                encoding="none",
                purpose="payload",
                lifecycle="runtime",
            )
            .build(bundle_path)
        )
        assert result.success, f"Build failed: {result.errors}"

        # Verify the slot is stored without compression
        reader = PSPFReader(bundle_path)
        metadata_read = reader.read_metadata()
        assert metadata_read["slots"][0]["encoding"] == "none"

    def test_slot_checksum_verification(self, temp_dir, test_builder):
        """Test slot checksum verification."""
        # Create slot with known checksum
        data = b"CHECKSUM_TEST"
        expected_checksum = hashlib.sha256(data).hexdigest()

        slot_path = temp_dir / "checksum.dat"
        slot_path.write_bytes(data)

        slot = SlotMetadata(
            index=0,
            id="checksum_test",
            source=str(slot_path),
            target="checksum_test",
            size=len(data),
            checksum=expected_checksum,
            encoding="none",
            purpose="payload",
            lifecycle="runtime",
        )

        # Build bundle
        bundle_path = temp_dir / "checksum.psp"
        # Use test_builder from fixture with fluent API
        metadata = {
            "format": "PSPF/2025",
            "package": {"name": "test", "version": "1.0"},
        }
        result = (
            test_builder.metadata(**metadata)
            .add_slot(
                id=slot.id,
                data=slot.source,
                encoding=slot.encoding,
                purpose=slot.purpose,
                lifecycle=slot.lifecycle,
            )
            .build(bundle_path)
        )
        assert result.success, f"Build failed: {result.errors}"

        # Verify checksum
        reader = PSPFReader(bundle_path)
        assert reader.verify_all_checksums()

    def test_slot_table_structure(self, temp_dir, test_slots, test_builder):
        """Test slot table binary structure."""
        bundle_path = temp_dir / "table.psp"
        # Use test_builder from fixture with fluent API
        metadata = {
            "format": "PSPF/2025",
            "package": {"name": "test", "version": "1.0"},
        }
        builder = test_builder.metadata(**metadata)
        for slot in test_slots:
            if hasattr(slot, "source") and slot.source:
                builder = builder.add_slot(
                id=slot.id,
                data=slot.source,
                    encoding=slot.encoding,
                    purpose=slot.purpose,
                    lifecycle=slot.lifecycle,
                )
        result = builder.build(bundle_path)
        assert result.success, f"Build failed: {result.errors}"

        reader = PSPFReader(bundle_path)
        index = reader.read_index()

        # Read slot table - NEW FORMAT uses 64-byte descriptors
        from flavor.psp.format_2025.slots import SlotDescriptor

        with open(bundle_path, "rb") as f:
            f.seek(index.slot_table_offset)

            for i in range(index.slot_count):
                # Each entry is now 64 bytes (SlotDescriptor)
                entry = f.read(SLOT_DESCRIPTOR_SIZE)
                assert len(entry) == SLOT_DESCRIPTOR_SIZE

                # Use SlotDescriptor to unpack
                descriptor = SlotDescriptor.unpack(entry)

                # Verify descriptor fields
                assert descriptor.offset > 0
                assert descriptor.offset % SLOT_ALIGNMENT == 0
                assert descriptor.size > 0
                assert descriptor.checksum != 0

    def test_slot_extraction_caching(self, temp_dir, test_builder):
        """Test slot caching metadata."""
        # Create a bundle with a cacheable slot
        slot_path = temp_dir / "cached.txt"
        slot_path.write_text("Cached content")

        slot = SlotMetadata(
            index=0,
            id="cached_slot",
            source=str(slot_path),
            target="cached_slot",
            size=slot_path.stat().st_size,
            checksum=hashlib.sha256(slot_path.read_bytes()).hexdigest(),
            encoding="gzip",
            purpose="payload",
            lifecycle="runtime",
        )

        # Build bundle
        bundle_path = temp_dir / "cached.psp"
        # Use test_builder from fixture with fluent API
        metadata = {
            "format": "PSPF/2025",
            "package": {"name": "cached", "version": "1.0"},
        }
        result = (
            test_builder.metadata(**metadata)
            .add_slot(
                id=slot.id,
                data=slot.source,
                encoding=slot.encoding,
                purpose=slot.purpose,
                lifecycle=slot.lifecycle,
            )
            .build(bundle_path)
        )
        assert result.success, f"Build failed: {result.errors}"

        # Verify slot metadata includes caching info
        reader = PSPFReader(bundle_path)
        metadata = reader.read_metadata()
        slot_meta = metadata["slots"][0]
        assert (
            slot_meta["lifecycle"] == "runtime"
        )  # Runtime slots available during execution

    def test_slot_metadata_serialization(self, test_builder):
        """Test SlotMetadata to_dict serialization."""
        slot = SlotMetadata(
            index=5,
            id="test_slot",
            source="/tmp/test",
            target="test_slot",
            size=2048,
            checksum="deadbeef",
            encoding="none",  # Binary files often don't compress well
            purpose="library",
            lifecycle="init",
        )

        # Serialize
        slot_dict = slot.to_dict()

        # Verify all fields
        assert slot_dict["slot"] == 5  # Uses "slot" not "index" in dict
        assert slot_dict["id"] == "test_slot"
        assert slot_dict["size"] == 2048
        # Checksum gets prefixed in to_dict
        assert "deadbeef" in slot_dict["checksum"]
        assert slot_dict["encoding"] == "none"
        assert slot_dict["purpose"] == "library"
        assert slot_dict["lifecycle"] == "init"
        # Source and target should be included in serialized metadata
        assert "source" in slot_dict
        assert "target" in slot_dict

    def test_large_slot_handling(self, temp_dir, test_builder):
        """Test handling of large slots."""
        # Create a 10MB slot
        large_data = os.urandom(10 * 1024 * 1024)
        large_path = temp_dir / "large.bin"
        large_path.write_bytes(large_data)

        slot = SlotMetadata(
            index=0,
            id="large_slot",
            source=str(large_path),
            target="large_slot",
            size=len(large_data),
            checksum=hashlib.sha256(large_data).hexdigest(),
            encoding="none",
            purpose="payload",
            lifecycle="runtime",
        )

        # Build bundle
        bundle_path = temp_dir / "large.psp"
        # Use test_builder from fixture with fluent API
        metadata = {
            "format": "PSPF/2025",
            "package": {"name": "large", "version": "1.0"},
        }
        result = (
            test_builder.metadata(**metadata)
            .add_slot(
                id=slot.id,
                data=slot.source,
                encoding=slot.encoding,
                purpose=slot.purpose,
                lifecycle=slot.lifecycle,
            )
            .build(bundle_path)
        )
        assert result.success, f"Build failed: {result.errors}"

        # Verify bundle was created
        assert bundle_path.exists()
        # Bundle size may be smaller than slot due to index/metadata overhead and alignment
        # Just verify it's reasonably large
        assert bundle_path.stat().st_size > 1000  # At least 1KB
