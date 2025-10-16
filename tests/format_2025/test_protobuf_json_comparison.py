"""
Test suite for PSPF/2025 protobuf and JSON format comparison
Validates the new packed operation chain format vs old string-based format
"""

import json
from pathlib import Path
import sys

# Add generated proto modules to path
gen_path = Path(__file__).parent.parent.parent / "src/flavor/psp/format_2025/generated"
sys.path.insert(0, str(gen_path))

from google.protobuf import json_format
from modules import crypto_pb2, index_pb2, metadata_pb2, operations_pb2, slots_pb2
import pspf_2025_pb2


class TestProtobufFormat:
    """Test the new protobuf-based PSPF/2025 format"""

    def test_operation_packing(self) -> None:
        """Test packing operations into 64-bit integers"""

        def pack_operations(ops):
            packed = 0
            for i, op in enumerate(ops[:8]):
                packed |= (op & 0xFF) << (i * 8)
            return packed

        def unpack_operations(packed):
            ops = []
            for i in range(8):
                op = (packed >> (i * 8)) & 0xFF
                if op == 0 or op == 0xFF:
                    break
                ops.append(op)
            return ops

        # Test TAR + GZIP
        ops1 = [operations_pb2.OP_TAR, operations_pb2.OP_GZIP]
        packed1 = pack_operations(ops1)
        assert packed1 == 0x1001  # 0x01 | (0x10 << 8)
        assert unpack_operations(packed1) == ops1

        # Test TAR + GZIP + AES256
        ops2 = [
            operations_pb2.OP_TAR,
            operations_pb2.OP_GZIP,
            operations_pb2.OP_AES256_GCM,
        ]
        packed2 = pack_operations(ops2)
        assert packed2 == 0x311001  # 0x01 | (0x10 << 8) | (0x31 << 16)
        assert unpack_operations(packed2) == ops2

        # Test max 8 operations
        ops3 = [
            operations_pb2.OP_TAR,
            operations_pb2.OP_GZIP,
            operations_pb2.OP_BASE64,
            operations_pb2.OP_SHA256,
            operations_pb2.OP_ED25519_SIGN,
            operations_pb2.OP_SPLIT,
            operations_pb2.OP_MERGE,
            operations_pb2.OP_TERMINAL,
        ]
        packed3 = pack_operations(ops3)
        unpacked3 = unpack_operations(packed3)
        assert unpacked3[:7] == ops3[:7]  # Terminal stops unpacking

    def test_slot_entry_creation(self) -> None:
        """Test creating slot entries with packed operations"""

        def pack_operations(ops):
            packed = 0
            for i, op in enumerate(ops[:8]):
                packed |= (op & 0xFF) << (i * 8)
            return packed

        # Create a slot entry
        ops = pack_operations([operations_pb2.OP_TAR, operations_pb2.OP_ZSTD])
        slot = slots_pb2.SlotEntry(
            id=0,
            name_hash=0x123456789ABCDEF0,
            offset=1024,
            size=4096,
            operations=ops,
            checksum=0x12345678,
            purpose=slots_pb2.PURPOSE_CODE,
            lifecycle=slots_pb2.LIFECYCLE_EAGER,
            platform=slots_pb2.PLATFORM_LINUX,
            permissions=0o755,
        )

        assert slot.id == 0
        assert slot.operations == 0x1B01  # TAR | ZSTD
        assert slot.purpose == slots_pb2.PURPOSE_CODE
        assert slot.lifecycle == slots_pb2.LIFECYCLE_EAGER
        assert slot.permissions == 0o755

    def test_metadata_with_features(self) -> None:
        """Test metadata with SPA and JIT features"""

        metadata = metadata_pb2.PackageMetadata(name="test-package", version="1.0.0", format_version="2025.1")

        # Enable SPA
        metadata.spa.enabled = True
        metadata.spa.pvp_slot = 0
        metadata.spa.pvp_timeout_ms = 5000
        metadata.spa.pvp_max_memory = 104857600

        # Enable JIT
        metadata.jit.enabled = True
        metadata.jit.strategy = "aggressive"
        metadata.jit.cache_dir = "/tmp/jit_cache"
        metadata.jit.max_cache_size = 1073741824

        assert metadata.spa.enabled is True
        assert metadata.spa.pvp_timeout_ms == 5000
        assert metadata.jit.enabled is True
        assert metadata.jit.strategy == "aggressive"

    def test_index_block_flags(self) -> None:
        """Test index block with feature flags"""

        index = index_pb2.IndexBlock(
            format_version=0x20250001,
            index_checksum=0xABCDEF00,
            package_size=1000000,
            launcher_size=500000,
            slot_count=5,
            flags=(
                index_pb2.FLAG_SIGNED
                | index_pb2.FLAG_COMPRESSED
                | index_pb2.FLAG_SPA_ENABLED
                | index_pb2.FLAG_JIT_ENABLED
            ),
        )

        assert index.format_version == 0x20250001
        assert index.flags & index_pb2.FLAG_SIGNED
        assert index.flags & index_pb2.FLAG_SPA_ENABLED
        assert index.flags & index_pb2.FLAG_JIT_ENABLED

    def test_crypto_info(self) -> None:
        """Test cryptographic information"""

        crypto = crypto_pb2.CryptoInfo()
        crypto.signature.algorithm = crypto_pb2.SIGNATURE_ED25519
        crypto.signature.public_key = b"A" * 32  # Ed25519 public key
        crypto.signature.signature = b"B" * 64  # Ed25519 signature
        crypto.signature.timestamp = 1735344000
        crypto.signature.key_id = "test-key"

        assert crypto.signature.algorithm == crypto_pb2.SIGNATURE_ED25519
        assert len(crypto.signature.public_key) == 32
        assert len(crypto.signature.signature) == 64
        assert crypto.signature.key_id == "test-key"

    def test_full_package_creation(self) -> None:
        """Test creating a complete PSPF package with all components"""

        def pack_operations(ops):
            packed = 0
            for i, op in enumerate(ops[:8]):
                packed |= (op & 0xFF) << (i * 8)
            return packed

        # Create package
        package = pspf_2025_pb2.PSPFPackage()

        # Set index
        package.index.format_version = 0x20250001
        package.index.slot_count = 2
        package.index.flags = index_pb2.FLAG_SIGNED | index_pb2.FLAG_COMPRESSED

        # Set metadata
        package.metadata.name = "test-app"
        package.metadata.version = "2.0.0"
        package.metadata.format_version = "2025.1"

        # Add slots
        slot1 = slots_pb2.SlotEntry(
            id=0,
            operations=pack_operations([operations_pb2.OP_TAR, operations_pb2.OP_GZIP]),
            purpose=slots_pb2.PURPOSE_CODE,
        )
        slot2 = slots_pb2.SlotEntry(
            id=1,
            operations=pack_operations([operations_pb2.OP_TAR, operations_pb2.OP_BZIP2]),
            purpose=slots_pb2.PURPOSE_DATA,
        )
        package.slots.extend([slot1, slot2])

        # Set crypto
        package.crypto.signature.algorithm = crypto_pb2.SIGNATURE_ED25519

        # Verify
        assert package.index.format_version == 0x20250001
        assert package.metadata.name == "test-app"
        assert len(package.slots) == 2
        assert package.slots[0].operations == 0x1001  # TAR | GZIP
        assert package.slots[1].operations == 0x1301  # TAR | BZIP2

    def test_json_serialization(self) -> None:
        """Test protobuf to JSON serialization"""

        # Create a simple metadata
        metadata = metadata_pb2.PackageMetadata(name="json-test", version="1.0.0", format_version="2025.1")

        # Add a slot
        slot = metadata_pb2.SlotMetadata(slot=0, id="test-slot", size=1024, operations="TAR|GZIP")
        metadata.slots.append(slot)

        # Convert to JSON
        json_str = json_format.MessageToJson(
            metadata, preserving_proto_field_name=True, use_integers_for_enums=False
        )

        json_obj = json.loads(json_str)

        assert json_obj["name"] == "json-test"
        assert json_obj["version"] == "1.0.0"
        assert json_obj["slots"][0]["id"] == "test-slot"
        assert json_obj["slots"][0]["operations"] == "TAR|GZIP"


class TestFormatComparison:
    """Test comparison between old and new formats"""

    def test_old_format_structure(self) -> None:
        """Verify old format structure"""

        old_format = {
            "format_version": "2024.1",
            "package": {"name": "test", "version": "1.0.0"},
            "slots": [
                {
                    "slot": 0,
                    "codec": "tar.gz",  # String-based
                    "purpose": "code",
                }
            ],
        }

        # Verify structure
        assert old_format["format_version"] == "2024.1"
        assert old_format["slots"][0]["codec"] == "tar.gz"
        assert "operations" not in old_format["slots"][0]

    def test_new_format_advantages(self) -> None:
        """Test advantages of new format"""

        def pack_operations(ops):
            packed = 0
            for i, op in enumerate(ops[:8]):
                packed |= (op & 0xFF) << (i * 8)
            return packed

        # Old format: string parsing required
        old_codec = "tar.gz.encrypted"
        old_parts = old_codec.split(".")
        assert len(old_parts) == 3  # Requires string manipulation

        # New format: direct bitwise operations
        new_ops = pack_operations(
            [
                operations_pb2.OP_TAR,
                operations_pb2.OP_GZIP,
                operations_pb2.OP_AES256_GCM,
            ]
        )

        # Extract operations efficiently
        op1 = new_ops & 0xFF
        op2 = (new_ops >> 8) & 0xFF
        op3 = (new_ops >> 16) & 0xFF

        assert op1 == operations_pb2.OP_TAR
        assert op2 == operations_pb2.OP_GZIP
        assert op3 == operations_pb2.OP_AES256_GCM

        # New format is more efficient:
        # - No string parsing
        # - Fixed-size representation (64 bits)
        # - Direct bitwise operations
        # - Type-safe enums

    def test_operation_chain_limits(self) -> None:
        """Test operation chain packing limits"""

        def pack_operations(ops):
            packed = 0
            for i, op in enumerate(ops[:8]):  # Max 8 operations
                packed |= (op & 0xFF) << (i * 8)
            return packed

        # Test maximum chain length (8 operations)
        max_ops = [
            operations_pb2.OP_TAR,
            operations_pb2.OP_GZIP,
            operations_pb2.OP_BASE64,
            operations_pb2.OP_AES256_GCM,
            operations_pb2.OP_SHA256,
            operations_pb2.OP_ED25519_SIGN,
            operations_pb2.OP_SPLIT,
            operations_pb2.OP_MERGE,
        ]

        packed = pack_operations(max_ops)
        assert packed != 0
        assert packed < 2**64  # Fits in 64 bits

        # Test with more than 8 operations (should truncate)
        too_many_ops = [*max_ops, operations_pb2.OP_DEDUPE, operations_pb2.OP_DELTA]
        packed_truncated = pack_operations(too_many_ops)
        packed_max = pack_operations(max_ops)
        assert packed_truncated == packed_max  # Same result, extra ops ignored
