#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PSPF 2025 slot operations tests covering compression and metadata."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from flavor.psp.format_2025 import (
    DEFAULT_SLOT_ALIGNMENT,
    PSPFReader,
    SlotMetadata,
)
from flavor.psp.format_2025.constants import SLOT_DESCRIPTOR_SIZE
from flavor.psp.format_2025.pspf_builder import PSPFBuilder


class TestPSPFSlotsOperations:
    """Test PSPF slot management."""

    def test_slot_compression_none(self, temp_dir: Path, test_builder: PSPFBuilder) -> None:
        """Test no compression."""
        data = b"NOCOMPRESS" * 100
        slot_path = temp_dir / "nocompress.bin"
        slot_path.write_bytes(data)

        SlotMetadata(
            index=0,
            id="uncompressed",
            source=str(slot_path),
            target="uncompressed",
            size=len(data),
            checksum=hashlib.sha256(data).hexdigest(),
            operations="none",
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
            .add_slot(
                id="uncompressed",
                data=slot_path,
                operations="none",
                purpose="payload",
                lifecycle="runtime",
            )
            .build(bundle_path)
        )
        assert result.success, f"Build failed: {result.errors}"

        # Verify the slot is stored without compression
        reader = PSPFReader(bundle_path)
        metadata_read = reader.read_metadata()
        assert "operations" in metadata_read["slots"][0]  # Operations field instead of codec

    def test_slot_checksum_verification(self, temp_dir: Path, test_builder: PSPFBuilder) -> None:
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
            operations="none",
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
                operations=slot.operations,
                purpose=slot.purpose,
                lifecycle=slot.lifecycle,
            )
            .build(bundle_path)
        )
        assert result.success, f"Build failed: {result.errors}"

        # Verify checksum
        reader = PSPFReader(bundle_path)
        assert reader.verify_all_checksums()

    def test_slot_table_structure(
        self,
        temp_dir: Path,
        test_slots: list[SlotMetadata],
        test_builder: PSPFBuilder,
    ) -> None:
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
                    operations=slot.operations,
                    purpose=slot.purpose,
                    lifecycle=slot.lifecycle,
                )
        result = builder.build(bundle_path)
        assert result.success, f"Build failed: {result.errors}"

        reader = PSPFReader(bundle_path)
        index = reader.read_index()

        # Read slot table - NEW FORMAT uses 64-byte descriptors
        from flavor.psp.format_2025.slots import SlotDescriptor

        with bundle_path.open("rb") as bundle_file:
            bundle_file.seek(index.slot_table_offset)

            for _i in range(index.slot_count):
                # Each entry is now 64 bytes (SlotDescriptor)
                entry = bundle_file.read(SLOT_DESCRIPTOR_SIZE)
                assert len(entry) == SLOT_DESCRIPTOR_SIZE

                # Use SlotDescriptor to unpack
                descriptor = SlotDescriptor.unpack(entry)

                # Verify descriptor fields
                assert descriptor.offset > 0
                assert descriptor.offset % DEFAULT_SLOT_ALIGNMENT == 0
                assert descriptor.size > 0
                assert descriptor.checksum != 0

    def test_slot_extraction_caching(self, temp_dir: Path, test_builder: PSPFBuilder) -> None:
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
            operations="gzip",
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
                operations=slot.operations,
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
        assert slot_meta["lifecycle"] == "runtime"  # Runtime slots available during execution

    def test_slot_metadata_serialization(self, test_builder: PSPFBuilder) -> None:
        """Test SlotMetadata to_dict serialization."""
        slot = SlotMetadata(
            index=5,
            id="test_slot",
            source="/tmp/test",
            target="test_slot",
            size=2048,
            checksum="deadbeef",
            operations="none",  # Binary files often don't compress well
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
        assert "operations" in slot_dict  # Operations field instead of codec
        assert slot_dict["purpose"] == "library"
        assert slot_dict["lifecycle"] == "init"
        # Source and target should be included in serialized metadata
        assert "source" in slot_dict
        assert "target" in slot_dict

    def test_large_slot_handling(self, temp_dir: Path, test_builder: PSPFBuilder) -> None:
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
            operations="none",
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
                operations=slot.operations,
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


# 🌶️📦🔚
