"""
Tests for the new ArchiveChain/ChainProcessor architecture.
"""

from pathlib import Path
import tempfile

import pytest

from flavor.archive import ArchiveChain, ChainProcessor, Operation
from flavor.archive.operations import pack_operations


class TestArchiveChain:
    """Test ArchiveChain data structure."""

    def test_chain_creation_from_list(self):
        """Test creating chain from list of operations."""
        chain = ArchiveChain([Operation.BUNDLE_TAR, Operation.COMPRESS_GZIP])
        assert len(chain) == 2
        assert not chain.is_empty
        assert chain.operations == [Operation.BUNDLE_TAR, Operation.COMPRESS_GZIP]

    def test_chain_creation_from_packed(self):
        """Test creating chain from packed integer."""
        packed = pack_operations([Operation.BUNDLE_TAR, Operation.COMPRESS_GZIP])
        chain = ArchiveChain(packed)
        assert len(chain) == 2
        assert chain.operations == [Operation.BUNDLE_TAR, Operation.COMPRESS_GZIP]

    def test_empty_chain(self):
        """Test empty chain handling."""
        chain = ArchiveChain([])
        assert chain.is_empty
        assert len(chain) == 0
        assert chain.packed == 0

    def test_chain_packed_representation(self):
        """Test packed integer representation."""
        chain = ArchiveChain([Operation.BUNDLE_TAR, Operation.COMPRESS_GZIP])
        expected_packed = pack_operations(
            [Operation.BUNDLE_TAR, Operation.COMPRESS_GZIP]
        )
        assert chain.packed == expected_packed

    def test_chain_string_representation(self):
        """Test human-readable string representation."""
        chain = ArchiveChain([Operation.BUNDLE_TAR, Operation.COMPRESS_GZIP])
        assert str(chain) == "TAR -> GZIP"

    def test_chain_operations_immutable(self):
        """Test that operations list is read-only."""
        chain = ArchiveChain([Operation.BUNDLE_TAR])
        ops = chain.operations
        ops.append(Operation.COMPRESS_GZIP)  # This should not affect the chain
        assert len(chain) == 1
        assert chain.operations == [Operation.BUNDLE_TAR]

    def test_add_operation_returns_new_chain(self):
        """Test that add_operation returns new chain (immutable)."""
        original = ArchiveChain([Operation.BUNDLE_TAR])
        new_chain = original.add_operation(Operation.COMPRESS_GZIP)

        assert len(original) == 1
        assert len(new_chain) == 2
        assert new_chain.operations == [Operation.BUNDLE_TAR, Operation.COMPRESS_GZIP]

    def test_remove_operation_returns_new_chain(self):
        """Test that remove_operation returns new chain (immutable)."""
        original = ArchiveChain([Operation.BUNDLE_TAR, Operation.COMPRESS_GZIP])
        new_chain = original.remove_operation(0)

        assert len(original) == 2
        assert len(new_chain) == 1
        assert new_chain.operations == [Operation.COMPRESS_GZIP]

    def test_chain_reversal(self):
        """Test chain reversal for extraction."""
        original = ArchiveChain([Operation.BUNDLE_TAR, Operation.COMPRESS_GZIP])
        reversed_chain = original.reverse()

        assert reversed_chain.operations == [
            Operation.COMPRESS_GZIP,
            Operation.BUNDLE_TAR,
        ]
        assert len(original) == len(reversed_chain)

    def test_chain_optimization(self):
        """Test chain optimization removes duplicates."""
        # Create chain with duplicates using direct values to bypass validation
        import flavor.archive.chain

        # Temporarily bypass validation to test optimization
        original_chain = flavor.archive.chain.ArchiveChain.__new__(
            flavor.archive.chain.ArchiveChain
        )
        original_chain._operations = [
            Operation.BUNDLE_TAR,
            Operation.BUNDLE_TAR,
            Operation.COMPRESS_GZIP,
        ]

        optimized = original_chain.optimize()
        assert optimized.operations == [Operation.BUNDLE_TAR, Operation.COMPRESS_GZIP]

    def test_chain_categories(self):
        """Test getting operation categories."""
        chain = ArchiveChain([Operation.BUNDLE_TAR, Operation.COMPRESS_GZIP])
        categories = chain.get_categories()

        assert "bundle" in categories
        assert "compress" in categories
        assert chain.has_category("bundle")
        assert chain.has_category("compress")
        assert not chain.has_category("encrypt")

    def test_invalid_chain_validation(self):
        """Test that invalid chains raise errors."""
        # Too many operations (>8)
        with pytest.raises(ValueError, match="Chain exceeds 8 operations"):
            ArchiveChain([1, 2, 3, 4, 5, 6, 7, 8, 9])

    def test_chain_equality(self):
        """Test chain equality comparison."""
        chain1 = ArchiveChain([Operation.BUNDLE_TAR, Operation.COMPRESS_GZIP])
        chain2 = ArchiveChain([Operation.BUNDLE_TAR, Operation.COMPRESS_GZIP])
        chain3 = ArchiveChain([Operation.BUNDLE_TAR])

        assert chain1 == chain2
        assert chain1 != chain3


class TestChainProcessor:
    """Test ChainProcessor execution engine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = ChainProcessor()

    def test_processor_initialization(self):
        """Test processor initializes correctly."""
        assert self.processor is not None
        supported_ops = self.processor.get_supported_operations()
        assert len(supported_ops) > 0
        assert Operation.BUNDLE_TAR in supported_ops
        assert Operation.COMPRESS_GZIP in supported_ops

    def test_empty_chain_validation(self):
        """Test empty chain validation."""
        empty_chain = ArchiveChain([])
        is_valid, msg = self.processor.validate_chain(empty_chain)
        assert is_valid
        assert "Empty chain" in msg

    def test_valid_chain_validation(self):
        """Test valid chain validation."""
        chain = ArchiveChain([Operation.BUNDLE_TAR, Operation.COMPRESS_GZIP])
        is_valid, msg = self.processor.validate_chain(chain)
        assert is_valid
        assert "Valid chain" in msg

    def test_unsupported_operation_validation(self):
        """Test validation of unsupported operations."""
        # Use a custom operation that won't be supported
        unsupported_chain = ArchiveChain([0xFF])  # Custom operation
        is_valid, msg = self.processor.validate_chain(unsupported_chain)
        assert not is_valid
        assert "Unsupported operations" in msg

    def test_supported_operations_list(self):
        """Test getting supported operations."""
        supported = self.processor.get_supported_operations()

        # Check that basic operations are supported
        basic_ops = {
            Operation.BUNDLE_TAR,
            Operation.COMPRESS_GZIP,
            Operation.COMPRESS_BZIP2,
            Operation.COMPRESS_XZ,
            Operation.COMPRESS_ZSTD,
        }

        assert basic_ops.issubset(supported)

    def test_process_empty_chain(self):
        """Test processing empty chain (pass-through)."""
        empty_chain = ArchiveChain([])
        test_file = Path(tempfile.mktemp())
        test_file.write_text("test content")

        try:
            result = self.processor.process(test_file, empty_chain)
            assert result == test_file  # Should pass through unchanged
        finally:
            test_file.unlink()

    @pytest.mark.skip(reason="Requires actual file operations - integration test")
    def test_process_chain_integration(self):
        """Integration test for processing actual files."""
        # This would require actual file operations
        # Skip for unit tests, but could be enabled for integration tests
        pass


class TestArchiveChainIntegration:
    """Integration tests with the archive system."""

    def test_archive_imports_work(self):
        """Test that all archive imports work correctly."""
        from flavor.archive import ArchiveChain, ChainProcessor, Operation

        # Basic smoke test
        chain = ArchiveChain([Operation.BUNDLE_TAR])
        processor = ChainProcessor()
        assert processor.validate_chain(chain)[0]

    def test_operations_compatible_with_pspf(self):
        """Test that archive operations are compatible with PSPF operations."""
        # Our archive operations should have the same values as PSPF operations
        from flavor.archive.operations import Operation as ArchiveOp
        from flavor.psp.format_2025.operations import OP_GZIP, OP_TAR

        # The values should match
        assert ArchiveOp.BUNDLE_TAR == OP_TAR
        assert ArchiveOp.COMPRESS_GZIP == OP_GZIP

    def test_pack_unpack_compatibility(self):
        """Test that pack/unpack functions are compatible."""
        from flavor.archive.operations import pack_operations as archive_pack
        from flavor.psp.format_2025.operations import pack_operations as pspf_pack

        ops = [1, 16]  # TAR, GZIP

        # Both should produce the same result
        archive_packed = archive_pack(ops)
        pspf_packed = pspf_pack(ops)

        assert archive_packed == pspf_packed
