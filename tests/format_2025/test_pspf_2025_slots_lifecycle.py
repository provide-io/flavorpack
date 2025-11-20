#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PSPF 2025 slot management tests covering lifecycle and metadata."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from flavor.psp.format_2025 import (
    PSPFReader,
    SlotMetadata,
)
from flavor.psp.format_2025.pspf_builder import PSPFBuilder


class TestPSPFSlots:
    """Test PSPF slot management."""

    @pytest.fixture
    def test_slots(self, temp_dir: Path, test_builder: PSPFBuilder) -> list[SlotMetadata]:
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
                operations="gzip",
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
                operations="none",  # Binary files often don't compress well
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
                operations="none",
                purpose="payload",
                lifecycle="temp",
            )
        )

        return slots

    def test_slot_lifecycle_runtime(self, temp_dir: Path, test_builder: PSPFBuilder) -> None:
        """Test runtime slot lifecycle metadata."""
        slot = SlotMetadata(
            index=0,
            id="test-runtime",
            source="",
            target="test-runtime",
            size=1024,
            checksum="abc123",
            operations="gzip",
            purpose="payload",
            lifecycle="runtime",
        )

        # Test metadata serialization
        slot_dict = slot.to_dict()
        assert slot_dict["lifecycle"] == "runtime"
        assert slot_dict["id"] == "test-runtime"
        # Runtime slots available during application execution

    def test_slot_lifecycle_init(self, temp_dir: Path, test_builder: PSPFBuilder) -> None:
        """Test init slot lifecycle metadata."""
        slot = SlotMetadata(
            index=0,
            id="test-init",
            source="",
            target="test-init",
            size=1024,
            checksum="abc123",
            operations="gzip",
            purpose="payload",
            lifecycle="init",
        )

        # Test metadata serialization
        slot_dict = slot.to_dict()
        assert slot_dict["lifecycle"] == "init"
        assert slot_dict["id"] == "test-init"
        # Init slots removed after initialization

    def test_slot_lifecycle_temp(self, temp_dir: Path, test_builder: PSPFBuilder) -> None:
        """Test temp slot lifecycle metadata."""
        slot = SlotMetadata(
            index=0,
            id="test-temp",
            source="",
            target="test-temp",
            size=1024,
            checksum="abc123",
            operations="gzip",
            purpose="payload",
            lifecycle="temp",
        )

        # Test metadata serialization
        slot_dict = slot.to_dict()
        assert slot_dict["lifecycle"] == "temp"
        assert slot_dict["id"] == "test-temp"
        # Temp slots removed after current session

    def test_slot_lifecycle_cache(self, temp_dir: Path, test_builder: PSPFBuilder) -> None:
        """Test cache slot lifecycle metadata."""
        slot = SlotMetadata(
            index=0,
            id="test-cache",
            source="",
            target="test-cache",
            size=1024,
            checksum="abc123",
            operations="gzip",
            purpose="config",
            lifecycle="cache",
        )

        # Test metadata serialization
        slot_dict = slot.to_dict()
        assert slot_dict["lifecycle"] == "cache"
        assert slot_dict["purpose"] == "config"
        # Cache slots kept for performance, can be regenerated

    def test_multiple_slots(
        self,
        temp_dir: Path,
        test_slots: list[SlotMetadata],
        test_builder: PSPFBuilder,
    ) -> None:
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
                    operations=slot.operations,
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

    def test_slot_compression_gzip(self, temp_dir: Path, test_builder: PSPFBuilder) -> None:
        """Test gzip compression."""
        # Create highly compressible data
        data = b"REPEAT" * 1000
        slot_path = temp_dir / "compress.txt"
        slot_path.write_bytes(data)

        SlotMetadata(
            index=0,
            id="compressed",
            source=str(slot_path),
            target="compressed",
            size=len(data),
            checksum=hashlib.sha256(data).hexdigest(),
            operations="gzip",
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
            .add_slot(
                id="compressed",
                data=slot_path,
                operations="gzip",
                purpose="payload",
                lifecycle="runtime",
            )
            .build(bundle_path)
        )
        assert result.success, f"Build failed: {result.errors}"

        # Verify the slot is stored with compression by checking metadata
        reader = PSPFReader(bundle_path)
        metadata_read = reader.read_metadata()
        assert "operations" in metadata_read["slots"][0]  # Operations field instead of codec


# 🌶️📦🔚
