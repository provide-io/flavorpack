#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test suite for the new PSPF/2025 operation chain system."""

from __future__ import annotations

from pathlib import Path
import tempfile

from flavor.psp.format_2025.operations import (
    OP_BZIP2,
    OP_GZIP,
    OP_TAR,
    OP_ZSTD,
    operations_to_string,
    pack_operations,
    string_to_operations,
    unpack_operations,
)
from flavor.psp.format_2025.pspf_builder import PSPFBuilder
from flavor.psp.format_2025.reader import PSPFReader
from flavor.psp.format_2025.slots import SlotDescriptor, SlotMetadata


class TestOperationChains:
    """Test the operation chain packing system."""

    def test_pack_unpack_operations(self) -> None:
        """Test packing and unpacking operation chains."""
        # Single operation
        ops1 = [OP_TAR]
        packed1 = pack_operations(ops1)
        assert packed1 == 0x01
        assert unpack_operations(packed1) == ops1

        # Two operations
        ops2 = [OP_TAR, OP_GZIP]
        packed2 = pack_operations(ops2)
        assert packed2 == 0x1001  # 0x01 | (0x10 << 8)
        assert unpack_operations(packed2) == ops2

        # Three operations
        ops3 = [OP_TAR, OP_GZIP, OP_BZIP2]
        packed3 = pack_operations(ops3)
        assert packed3 == 0x131001  # 0x01 | (0x10 << 8) | (0x13 << 16)
        assert unpack_operations(packed3) == ops3

        # Maximum 8 operations
        ops8 = [OP_TAR, OP_GZIP, OP_BZIP2, OP_ZSTD, OP_TAR, OP_GZIP, OP_BZIP2, OP_ZSTD]
        packed8 = pack_operations(ops8)
        assert unpack_operations(packed8) == ops8

    def test_operations_to_string(self) -> None:
        """Test converting operations to human-readable strings."""
        assert operations_to_string(0) == "raw"
        assert operations_to_string(pack_operations([OP_TAR])) == "tar"
        assert operations_to_string(pack_operations([OP_TAR, OP_GZIP])) == "tar.gz"  # Common chain
        assert operations_to_string(pack_operations([OP_TAR, OP_BZIP2])) == "tar.bz2"  # Common chain

    def test_string_to_operations(self) -> None:
        """Test parsing operation strings."""
        assert string_to_operations("RAW") == 0
        assert string_to_operations("TAR") == pack_operations([OP_TAR])
        assert string_to_operations("TAR|GZIP") == pack_operations([OP_TAR, OP_GZIP])
        assert string_to_operations("tar.gz") == pack_operations([OP_TAR, OP_GZIP])
        assert string_to_operations("tar.bz2") == pack_operations([OP_TAR, OP_BZIP2])

    def test_common_operation_chains(self) -> None:
        """Test common operation chain patterns."""
        # RAW (no operations)
        assert pack_operations([]) == 0
        # Single operations
        assert pack_operations([OP_TAR]) == 0x01
        assert pack_operations([OP_GZIP]) == 0x10
        # Common combinations
        assert pack_operations([OP_TAR, OP_GZIP]) == 0x1001  # tar.gz

    def test_slot_descriptor_with_operations(self) -> None:
        """Test SlotDescriptor handles operations correctly."""
        # Create with operations
        slot1 = SlotDescriptor(id=1, name="test", operations=pack_operations([OP_TAR, OP_GZIP]), size=1024)
        # Verify operations are stored correctly
        assert slot1.operations == pack_operations([OP_TAR, OP_GZIP])

        # Create with different operations
        slot2 = SlotDescriptor(
            id=2,
            name="test2",
            operations=pack_operations([OP_TAR, OP_BZIP2]),
            size=2048,
        )
        # Verify operations
        assert slot2.operations == pack_operations([OP_TAR, OP_BZIP2])

        # Pack and unpack
        packed = slot1.pack()
        assert len(packed) == 64  # Correct size

        unpacked = SlotDescriptor.unpack(packed)
        assert unpacked.id == slot1.id
        assert unpacked.operations == slot1.operations

    def test_builder_with_operations(self, test_builder: PSPFBuilder) -> None:
        """Test that PSPFBuilder works with operation chains."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create test file
            test_file = tmpdir / "test.txt"
            test_file.write_text("Hello, operations!")

            # Build package with operation chain using test_builder
            builder = test_builder.metadata(package={"name": "test", "version": "2025.1"}).add_slot(
                id="test.txt",
                data=str(test_file),
                operations="tar.gz",  # Operation chain string
            )

            # Build package
            output = tmpdir / "test.psp"
            result = builder.build(output_path=output)
            assert result.success

            # Read package and verify operations
            reader = PSPFReader(output)
            reader.open()

            # Read index and metadata
            reader.read_index()
            metadata = reader.read_metadata()

            # Check metadata exists
            assert metadata is not None

            # Read slot descriptors
            reader.read_slot_descriptors()

            # The slot descriptor should have operations set
            if reader._slot_descriptors:
                desc = reader._slot_descriptors[0]
                # Operations are handled internally now
                assert desc.operations == pack_operations([OP_TAR, OP_GZIP])

    def test_operation_chain_validation(self) -> None:
        """Test that operation chains are valid."""
        # Test valid operation chains
        ops1 = pack_operations([OP_TAR, OP_GZIP])
        assert ops1 == 0x1001

        ops2 = pack_operations([OP_TAR])
        assert ops2 == 0x01

        # Test operations to string conversion
        assert operations_to_string(ops1) == "tar.gz"  # Common chain
        assert operations_to_string(ops2) == "tar"

    def test_metadata_with_operations(self) -> None:
        """Test SlotMetadata handles operation descriptions."""
        meta = SlotMetadata(
            index=0,
            id="test",
            source="source/",
            target="target/",
            size=1024,
            checksum="abc123",
            operations="tar.gz",  # String representation
            purpose="data",
            lifecycle="runtime",
        )

        # Should be able to describe operations
        assert meta.operations == "tar.gz"

        # Convert to dict for JSON
        data = meta.to_dict()
        assert data["operations"] == "tar.gz"


# 🌶️📦🔚
