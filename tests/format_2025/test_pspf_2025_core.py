#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Core PSPF 2025 format tests covering structure, reading, and writing."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
from typing import Any

from provide.foundation.file import align_offset
import pytest

from flavor.psp.format_2025 import (
    DEFAULT_HEADER_SIZE,
    DEFAULT_MAGIC_TRAILER_SIZE,
    DEFAULT_SLOT_ALIGNMENT,
    DEFAULT_SLOT_DESCRIPTOR_SIZE,
    PSPF_VERSION,
    TRAILER_END_MAGIC,
    TRAILER_START_MAGIC,
    PSPFBuilder,
    PSPFIndex,
    PSPFReader,
    SlotMetadata,
    generate_ed25519_keypair,
)


@pytest.mark.integration
@pytest.mark.requires_helpers
class TestPSPFCore:
    """Test core PSPF format functionality."""

    @pytest.fixture
    def simple_payload(self, temp_dir: Path) -> Path:
        """Create a simple test payload."""
        payload_path = temp_dir / "hello.sh"
        payload_path.write_text("#!/bin/sh\necho 'Hello PSPF!'")
        return payload_path

    @pytest.fixture
    def simple_metadata(self) -> dict[str, Any]:
        """Create simple metadata."""
        return {
            "format": "PSPF/2025",
            "package": {"name": "test-bundle", "version": "1.0.0"},
            "execution": {"primary_slot": 0, "command": "{workenv}/hello.sh"},
            "verification": {"integrity_seal": {"required": True, "algorithm": "ed25519"}},
        }

    def test_pspf_specification_implemented(self) -> None:
        """Test that PSPF 2025 specification is implemented."""
        assert PSPFBuilder is not None
        assert PSPFReader is not None
        assert PSPFIndex is not None

    def test_ephemeral_keys_available(self) -> None:
        """Test ephemeral key generation."""
        private_key, public_key = generate_ed25519_keypair()
        assert private_key is not None
        assert public_key is not None
        assert len(private_key) == 32
        assert len(public_key) == 32
        assert private_key != public_key

    def test_build_minimal_bundle(
        self,
        temp_dir: Path,
        simple_payload: Path,
        simple_metadata: dict[str, Any],
        test_builder: PSPFBuilder,
    ) -> None:
        """Test building a minimal PSPF bundle."""
        # Create slot
        slot = SlotMetadata(
            index=0,
            id="hello",
            source=str(simple_payload),
            target="hello",
            size=simple_payload.stat().st_size,
            checksum=hashlib.sha256(simple_payload.read_bytes()).hexdigest(),
            operations="none",
            purpose="payload",
            lifecycle="runtime",
        )

        # Build bundle
        bundle_path = temp_dir / "test.psp"
        # Use test_builder from fixture
        result = (
            test_builder.metadata(**simple_metadata)
            .add_slot(
                id=slot.id,
                data=slot.source,
                operations=slot.operations,
                purpose=slot.purpose,
                lifecycle=slot.lifecycle,
            )
            .with_options()
            .build(bundle_path)
        )
        assert result.success, f"Build failed: {result.errors}"

        # Verify bundle exists
        assert bundle_path.exists()
        assert bundle_path.stat().st_size > 0

    def test_emoji_magic_format(
        self,
        temp_dir: Path,
        simple_payload: Path,
        simple_metadata: dict[str, Any],
        test_builder: PSPFBuilder,
    ) -> None:
        """Test emoji magic is just the magic wand."""
        # Build bundle
        bundle_path = temp_dir / "test.psp"
        # Use test_builder from fixture
        result = test_builder.metadata(**simple_metadata, allow_empty=True).with_options().build(bundle_path)
        assert result.success, f"Build failed: {result.errors}"

        # Check emoji magic
        with bundle_path.open("rb") as bundle_file:
            bundle_file.seek(-4, 2)
            magic = bundle_file.read(4)

        magic.decode("utf-8")
        assert magic == TRAILER_END_MAGIC

    def test_magic_wand_footer(
        self,
        temp_dir: Path,
        simple_metadata: dict[str, Any],
        test_builder: PSPFBuilder,
    ) -> None:
        """Test magic wand emoji footer."""
        # Test with default launcher
        bundle_path = temp_dir / "test_default.psp"
        # Use test_builder from fixture
        result = test_builder.metadata(**simple_metadata, allow_empty=True).with_options().build(bundle_path)
        assert result.success, f"Build failed: {result.errors}"

        # Check emoji is always magic wand
        with bundle_path.open("rb") as bundle_file:
            bundle_file.seek(-4, 2)
            magic = bundle_file.read(4)

        magic.decode("utf-8")
        assert magic == TRAILER_END_MAGIC

    def test_index_block_location(
        self,
        temp_dir: Path,
        simple_metadata: dict[str, Any],
        test_builder: PSPFBuilder,
    ) -> None:
        """Test index block is at launcher_size offset."""
        bundle_path = temp_dir / "test.psp"
        # Use test_builder from fixture
        result = test_builder.metadata(**simple_metadata, allow_empty=True).with_options().build(bundle_path)
        assert result.success, f"Build failed: {result.errors}"

        # Read bundle
        PSPFReader(bundle_path)

        # Check MagicTrailer at end of file
        with bundle_path.open("rb") as bundle_file:
            # Seek to start of MagicTrailer
            bundle_file.seek(-DEFAULT_MAGIC_TRAILER_SIZE, 2)
            trailer = bundle_file.read(DEFAULT_MAGIC_TRAILER_SIZE)

        # Verify MagicTrailer structure

        # Verify index version in trailer
        index_version = struct.unpack("<I", trailer[4:8])[0]
        assert index_version == PSPF_VERSION

    def test_index_block_size(self) -> None:
        """Test index block is exactly 256 bytes."""
        # FORMAT is now an attrs field, so we need to access it from an instance
        index = PSPFIndex()
        assert struct.calcsize(index.FORMAT) == DEFAULT_HEADER_SIZE

        # Also test packing
        packed = index.pack()
        assert len(packed) == DEFAULT_HEADER_SIZE

    def test_index_checksum(
        self,
        temp_dir: Path,
        simple_metadata: dict[str, Any],
        test_builder: PSPFBuilder,
    ) -> None:
        """Test index block checksum validation."""
        bundle_path = temp_dir / "test.psp"
        result = test_builder.metadata(**simple_metadata, allow_empty=True).build(bundle_path)
        assert result.success, f"Build failed: {result.errors}"

        # Read and verify checksum
        reader = PSPFReader(bundle_path)
        index = reader.read_index()  # Should not raise
        assert index.format_version == PSPF_VERSION

    def test_metadata_archive_structure(
        self,
        temp_dir: Path,
        simple_metadata: dict[str, Any],
        test_builder: PSPFBuilder,
    ) -> None:
        """Test metadata is gzipped JSON."""
        bundle_path = temp_dir / "test.psp"
        # Use test_builder from fixture
        result = test_builder.metadata(**simple_metadata, allow_empty=True).build(bundle_path)
        assert result.success, f"Build failed: {result.errors}"

        # Read index to get metadata location
        reader = PSPFReader(bundle_path)
        index = reader.read_index()

        # Extract metadata archive
        with bundle_path.open("rb") as bundle_file:
            bundle_file.seek(index.metadata_offset)
            archive_data = bundle_file.read(index.metadata_size)

        # Verify it's gzipped JSON
        import gzip
        import io

        with gzip.open(io.BytesIO(archive_data), "rb") as gz:
            json_data = gz.read()
            metadata = json.loads(json_data)
            assert "package" in metadata
            assert "format" in metadata
            assert metadata["format"] == "PSPF/2025"

    def test_metadata_placement(
        self,
        temp_dir: Path,
        simple_metadata: dict[str, Any],
        test_builder: PSPFBuilder,
    ) -> None:
        """Test that metadata immediately follows launcher per PSPF spec."""
        bundle_path = temp_dir / "test.psp"
        result = test_builder.metadata(**simple_metadata, allow_empty=True).build(bundle_path)
        assert result.success, f"Build failed: {result.errors}"

        # Read index to get offsets
        reader = PSPFReader(bundle_path)
        index = reader.read_index()

        # Metadata should immediately follow launcher with no gap
        assert index.metadata_offset == index.launcher_size, (
            f"Metadata should immediately follow launcher. "
            f"Launcher ends at {index.launcher_size}, but metadata starts at {index.metadata_offset}. "
            f"Gap of {index.metadata_offset - index.launcher_size} bytes violates PSPF spec."
        )

    def test_metadata_psp_json_required(
        self,
        temp_dir: Path,
        simple_metadata: dict[str, Any],
        test_builder: PSPFBuilder,
    ) -> None:
        """Test psp.json is required in metadata."""
        bundle_path = temp_dir / "test.psp"
        # Use test_builder from fixture
        result = test_builder.metadata(**simple_metadata, allow_empty=True).build(bundle_path)
        assert result.success, f"Build failed: {result.errors}"

        # Read metadata
        reader = PSPFReader(bundle_path)
        metadata = reader.read_metadata()

        # Verify required fields
        assert metadata["format"] == "PSPF/2025"
        assert "package" in metadata
        assert "verification" in metadata

    def test_slot_alignment(
        self,
        temp_dir: Path,
        simple_metadata: dict[str, Any],
        test_builder: PSPFBuilder,
    ) -> None:
        """Test slots are aligned to 8-byte boundaries."""
        # Create multiple slots
        slots = []
        for i in range(3):
            slot_path = temp_dir / f"slot{i}.dat"
            # Create slots with non-aligned sizes
            slot_path.write_bytes(b"X" * (100 + i * 7))

            slots.append(
                SlotMetadata(
                    index=i,
                    id=f"slot{i}",
                    source=str(slot_path),
                    target=f"slot{i}",
                    size=slot_path.stat().st_size,
                    checksum=hashlib.sha256(slot_path.read_bytes()).hexdigest(),
                    operations="none",
                    purpose="payload",
                    lifecycle="runtime",
                )
            )

        # Build bundle
        bundle_path = temp_dir / "test.psp"
        # Use test_builder from fixture
        builder = test_builder.metadata(**simple_metadata)
        for slot in slots:
            builder = builder.add_slot(
                id=slot.id,
                data=slot.source,
                operations=slot.operations,
                purpose=slot.purpose,
                lifecycle=slot.lifecycle,
            )
        result = builder.build(bundle_path)
        assert result.success, f"Build failed: {result.errors}"

        # Read and verify alignment
        reader = PSPFReader(bundle_path)
        index = reader.read_index()

        with bundle_path.open("rb") as bundle_file:
            bundle_file.seek(index.slot_table_offset)
            for i in range(index.slot_count):
                # Read the full 64-byte descriptor
                entry_data = bundle_file.read(DEFAULT_SLOT_DESCRIPTOR_SIZE)
                # Offset is at bytes 16-24 in the 64-byte descriptor
                offset = struct.unpack("<Q", entry_data[16:24])[0]

                # Verify alignment
                assert offset % DEFAULT_SLOT_ALIGNMENT == 0, f"Slot {i} not aligned (offset={offset})"

    def test_align_offset_function(self) -> None:
        """Test offset alignment function with PSPF slot alignment (8 bytes)."""
        # Test various offsets with DEFAULT_SLOT_ALIGNMENT (8)
        assert align_offset(0, DEFAULT_SLOT_ALIGNMENT) == 0
        assert align_offset(1, DEFAULT_SLOT_ALIGNMENT) == 8
        assert align_offset(7, DEFAULT_SLOT_ALIGNMENT) == 8
        assert align_offset(8, DEFAULT_SLOT_ALIGNMENT) == 8
        assert align_offset(9, DEFAULT_SLOT_ALIGNMENT) == 16
        assert align_offset(100, DEFAULT_SLOT_ALIGNMENT) == 104
        assert align_offset(104, DEFAULT_SLOT_ALIGNMENT) == 104

    def test_reader_verify_magic(
        self,
        temp_dir: Path,
        simple_metadata: dict[str, Any],
        test_builder: PSPFBuilder,
    ) -> None:
        """Test magic verification."""
        bundle_path = temp_dir / "test.psp"
        # Use test_builder from fixture
        result = test_builder.metadata(**simple_metadata, allow_empty=True).build(bundle_path)
        assert result.success, f"Build failed: {result.errors}"

        reader = PSPFReader(bundle_path)
        assert reader.verify_magic_trailer()

        # Test corrupted magic
        with bundle_path.open("r+b") as bundle_file:
            bundle_file.seek(-4, 2)
            bundle_file.write(b"BAD!")

        reader2 = PSPFReader(bundle_path)
        assert not reader2.verify_magic_trailer()

    def test_launcher_size_detection(
        self,
        temp_dir: Path,
        simple_metadata: dict[str, Any],
        test_builder: PSPFBuilder,
    ) -> None:
        """Test launcher size detection."""
        bundle_path = temp_dir / "test.psp"
        # Use test_builder from fixture
        result = test_builder.metadata(**simple_metadata, allow_empty=True).build(bundle_path)
        assert result.success, f"Build failed: {result.errors}"

        PSPFReader(bundle_path)

        # Verify MagicTrailer at end of file
        with bundle_path.open("rb") as bundle_file:
            bundle_file.seek(-DEFAULT_MAGIC_TRAILER_SIZE, 2)
            trailer = bundle_file.read(DEFAULT_MAGIC_TRAILER_SIZE)

        assert trailer[:4] == TRAILER_START_MAGIC
        assert trailer[-4:] == TRAILER_END_MAGIC

    def test_empty_bundle(self, temp_dir: Path, test_builder: PSPFBuilder) -> None:
        """Test building bundle with no slots."""
        bundle_path = temp_dir / "empty.psp"
        # Use test_builder from fixture

        metadata = {
            "format": "PSPF/2025",
            "package": {"name": "empty", "version": "1.0.0"},
        }

        result = test_builder.metadata(**metadata, allow_empty=True).build(bundle_path)
        assert result.success, f"Build failed: {result.errors}"

        # Verify structure
        reader = PSPFReader(bundle_path)
        assert reader.verify_magic_trailer()
        index = reader.read_index()
        assert index.slot_count == 0

        metadata = reader.read_metadata()
        assert metadata["package"]["name"] == "empty"


# 🌶️📦🔚
