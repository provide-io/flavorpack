#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""JSON Structure Comparison: Old vs New PSPF/2025 Format
Shows the evolution from text-based operation chains to packed integers"""

import json
from pathlib import Path
import sys

# Add generated proto modules to path
sys.path.insert(0, str(Path(__file__).parent / "generated"))

from generated import pspf_2025_pb2
from generated.modules import (
    crypto_pb2,
    index_pb2,
    metadata_pb2,
    operations_pb2,
    slots_pb2,
)
from google.protobuf import json_format

# Import v0 constants for operation packing
from flavor.psp.format_2025.constants import (
    OP_BZIP2,
    OP_GZIP,
    OP_TAR,
)
from flavor.psp.format_2025.operations import pack_operations


def create_old_format_json() -> dict:
    """Create JSON in the old format with string-based operations"""
    return {
        "format_version": "2024.1",
        "package": {
            "name": "hello-world",
            "version": "1.0.0",
            "description": "Example Python application",
        },
        "slots": [
            {
                "slot": 0,
                "id": "python-runtime",
                "source": "runtime/python311",
                "target": "python",
                "size": 52428800,
                "checksum": "sha256:abcd1234...",
                "codec": "tar.gz",  # String-based codec chain
                "purpose": "runtime",
                "lifecycle": "eager",
            },
            {
                "slot": 1,
                "id": "application",
                "source": "src/",
                "target": "app",
                "size": 1048576,
                "checksum": "sha256:ef567890...",
                "codec": "tar.gz.encrypted",  # String concatenation
                "purpose": "code",
                "lifecycle": "startup",
            },
            {
                "slot": 2,
                "id": "dependencies",
                "source": "site-packages/",
                "target": "lib",
                "size": 10485760,
                "checksum": "sha256:9876fedc...",
                "codec": "tar.bz2",  # Different compression
                "purpose": "library",
                "lifecycle": "runtime",
            },
        ],
        "execution": {
            "command": "python",
            "args": ["-m", "app.main"],
            "env": {"PYTHONPATH": "/app:/lib"},
        },
        "security": {
            "signed": True,
            "signature": "base64:MEUCIQDx...",
            "public_key": "ed25519:MCowBQYDK...",
        },
    }


# Remove local pack_operations - using the official one from operations.py


def create_new_format_protobuf() -> pspf_2025_pb2.PSPFPackage:
    """Create new format using protobuf messages with packed operations"""

    # Create package metadata
    metadata = metadata_pb2.PackageMetadata(
        name="hello-world",
        version="1.0.0",
        format_version="2025.1",
        description="Example Python application",
        author="Developer",
        license="MIT",
    )

    # Add execution config
    metadata.execution.command = "python"
    metadata.execution.args.extend(["-m", "app.main"])
    metadata.execution.env["PYTHONPATH"] = "/app:/lib"
    metadata.execution.interpreter = "python3.11"
    metadata.execution.timeout_seconds = 300

    # Add build info
    metadata.build.timestamp = 1735344000
    metadata.build.machine = "builder-x64"
    metadata.build.user = "ci"
    metadata.build.commit = "abc123def456"
    metadata.build.branch = "main"
    metadata.build.builder_version = "flavor-2025.1"

    # Add requirements
    metadata.requirements.python_version = ">=3.11"
    metadata.requirements.platform = "linux"
    metadata.requirements.architecture = "x86_64"
    metadata.requirements.memory_mb = 512
    metadata.requirements.disk_mb = 100

    # Add slot metadata with operation chains
    slot0 = metadata_pb2.SlotMetadata(
        slot=0,
        id="python-runtime",
        source="runtime/python311",
        target="python",
        size=52428800,
        checksum="adler32:12345678",
        operations="TAR|GZIP",  # Human-readable for JSON
        purpose="runtime",
        lifecycle="eager",
        permissions="755",
    )

    slot1 = metadata_pb2.SlotMetadata(
        slot=1,
        id="application",
        source="src/",
        target="app",
        size=1048576,
        checksum="sha256:ef567890abcdef",
        operations="TAR|GZIP|AES256_GCM",
        purpose="code",
        lifecycle="startup",
        permissions="644",
    )

    slot2 = metadata_pb2.SlotMetadata(
        slot=2,
        id="dependencies",
        source="site-packages/",
        target="lib",
        size=10485760,
        checksum="xxhash:fedcba98",
        operations="TAR|BZIP2",
        purpose="library",
        lifecycle="runtime",
        permissions="644",
    )

    metadata.slots.extend([slot0, slot1, slot2])

    # Enable advanced features
    metadata.spa.enabled = True
    metadata.spa.pvp_slot = 0
    metadata.spa.pvp_timeout_ms = 5000
    metadata.spa.pvp_max_memory = 104857600
    metadata.spa.pvp_capabilities.extend(["ui_render", "temp_files"])

    metadata.jit.enabled = True
    metadata.jit.strategy = "aggressive"
    metadata.jit.cache_dir = "{workenv}/.jit_cache"
    metadata.jit.max_cache_size = 1073741824
    metadata.jit.network_timeout_ms = 30000
    metadata.jit.background_slots.extend([2])

    metadata.security.require_signature = True
    metadata.security.signature_algorithm = "ed25519"
    metadata.security.verify_checksums = True

    # Create index block
    index = index_pb2.IndexBlock(
        format_version=0x20250001,  # PSPF/2025 v1
        index_checksum=0x12345678,
        package_size=64000000,
        launcher_size=10485760,
        metadata_offset=10485760,
        metadata_size=8192,
        slot_table_offset=10493952,
        slot_table_size=4096,
        slot_count=3,
        flags=index_pb2.FLAG_SIGNED
        | index_pb2.FLAG_COMPRESSED
        | index_pb2.FLAG_SPA_ENABLED
        | index_pb2.FLAG_JIT_ENABLED,
    )

    # Create slot entries with packed operations
    slot_entries = []

    # Slot 0: TAR + GZIP (using v0 constants)
    ops0 = pack_operations([OP_TAR, OP_GZIP])
    slot0_entry = slots_pb2.SlotEntry(
        id=0,
        name_hash=0x123456789ABCDEF0,  # xxHash64("python-runtime")
        offset=10498048,
        size=52428800,
        operations=ops0,  # Packed: 0x0000000000001001
        checksum=0x12345678,
        purpose=slots_pb2.PURPOSE_RUNTIME,
        lifecycle=slots_pb2.LIFECYCLE_EAGER,
        platform=slots_pb2.PLATFORM_LINUX,
        permissions=0o755,
        flags=0,
        name="python-runtime",
        source_path="runtime/python311",
        target_path="python",
    )

    # Slot 1: TAR + GZIP (v0 doesn't support AES256_GCM - using only supported operations)
    ops1 = pack_operations([OP_TAR, OP_GZIP])
    slot1_entry = slots_pb2.SlotEntry(
        id=1,
        name_hash=0xFEDCBA9876543210,  # xxHash64("application")
        offset=62926848,
        size=1048576,
        operations=ops1,  # Packed: 0x0000000000001001 (TAR + GZIP)
        checksum=0x87654321,
        purpose=slots_pb2.PURPOSE_CODE,
        lifecycle=slots_pb2.LIFECYCLE_STARTUP,
        platform=slots_pb2.PLATFORM_ANY,
        permissions=0o644,
        flags=0,
        name="application",
        source_path="src/",
        target_path="app",
    )

    # Slot 2: TAR + BZIP2 (using v0 constants)
    ops2 = pack_operations([OP_TAR, OP_BZIP2])
    slot2_entry = slots_pb2.SlotEntry(
        id=2,
        name_hash=0xABCDEF0123456789,  # xxHash64("dependencies")
        offset=63975424,
        size=10485760,
        operations=ops2,  # Packed: 0x0000000000001301 (TAR + BZIP2)
        checksum=0xFEDCBA98,
        purpose=slots_pb2.PURPOSE_LIBRARY,
        lifecycle=slots_pb2.LIFECYCLE_RUNTIME,
        platform=slots_pb2.PLATFORM_LINUX,
        permissions=0o644,
        flags=0,
        name="dependencies",
        source_path="site-packages/",
        target_path="lib",
    )

    # Configure JIT for slot 2
    slot2_entry.jit.source.type = "grpc"
    slot2_entry.jit.source.endpoint = "cdn.example.com:443"
    slot2_entry.jit.source.path = "/packages/deps/v1.0.0"
    slot2_entry.jit.cache.strategy = "persistent"
    slot2_entry.jit.cache.ttl = 86400
    slot2_entry.jit.priority = 5

    slot_entries.extend([slot0_entry, slot1_entry, slot2_entry])

    # Create crypto info
    crypto = crypto_pb2.CryptoInfo()
    crypto.signature.algorithm = crypto_pb2.SIGNATURE_ED25519
    crypto.signature.public_key = b"\x00" * 32  # Ed25519 public key
    crypto.signature.signature = b"\x00" * 64  # Ed25519 signature
    crypto.signature.timestamp = 1735344000
    crypto.signature.key_id = "main-signing-key"

    # Create full package
    package = pspf_2025_pb2.PSPFPackage()
    package.index.CopyFrom(index)
    package.metadata.CopyFrom(metadata)
    package.slots.extend(slot_entries)
    package.crypto.CopyFrom(crypto)

    # Add operation chains for clarity
    for slot in slot_entries:
        chain = operations_pb2.OperationChain(
            packed=slot.operations, description=f"Operations for slot {slot.id}"
        )
        # Unpack for clarity
        ops = []
        packed = slot.operations
        for i in range(8):
            op = (packed >> (i * 8)) & 0xFF
            if op == 0 or op == 0xFF:
                break
            ops.append(op)
        chain.operations.extend(ops)
        package.operation_chains.append(chain)

    return package


def main() -> None:
    """Compare old and new JSON structures"""

    # Create old format
    old_json = create_old_format_json()

    # Create new format
    new_proto = create_new_format_protobuf()

    # Convert protobuf to JSON
    new_json = json.loads(
        json_format.MessageToJson(
            new_proto,
            always_print_fields_with_no_presence=False,
            preserving_proto_field_name=True,
            use_integers_for_enums=False,  # Use enum names for readability
        )
    )

    # Print comparison
    print("=" * 80)
    print("OLD FORMAT (2024.1) - String-based codecs")
    print("=" * 80)
    print(json.dumps(old_json, indent=2))

    print("\n" + "=" * 80)
    print("NEW FORMAT (2025.1) - Packed operation chains with protobuf")
    print("=" * 80)
    print(json.dumps(new_json, indent=2))

    print("\n" + "=" * 80)
    print("KEY IMPROVEMENTS:")
    print("=" * 80)
    print("""
1. OPERATION CHAINS:
   Old: "codec": "tar.gz.encrypted" (string concatenation)
   New: "operations": 0x31100001 (packed 64-bit: TAR|GZIP|AES256_GCM)

2. SLOT METADATA:
   Old: Simple flat structure with mixed concerns
   New: Structured with purpose, lifecycle, platform, permissions

3. CRYPTOGRAPHY:
   Old: Basic signature and public key
   New: Full crypto info with algorithms, key management, trust chains

4. ADVANCED FEATURES:
   Old: Not supported
   New: SPA (Staged Payload Architecture) and JIT loading configurations

5. TYPE SAFETY:
   Old: Strings and loose typing
   New: Strongly typed enums and structured messages

6. EXTENSIBILITY:
   Old: Limited, requires format changes
   New: Protocol buffer extensibility, backward/forward compatible

7. PERFORMANCE:
   Old: String parsing for operations
   New: Direct bitwise operations on packed integers

8. CROSS-LANGUAGE:
   Old: JSON-only, language-specific parsers
   New: Protobuf with native code generation for Python, Go, Rust
""")

    # Show operation packing example
    print("=" * 80)
    print("OPERATION PACKING EXAMPLE:")
    print("=" * 80)

    ops = [operations_pb2.OP_TAR, operations_pb2.OP_GZIP, operations_pb2.OP_AES256_GCM]
    packed = pack_operations(ops)

    print(f"Operations: {[operations_pb2.Operation.Name(op) for op in ops]}")
    print(f"Hex values: {[hex(op) for op in ops]}")
    print(f"Packed (64-bit): 0x{packed:016x}")
    print(f"Binary: {bin(packed)}")
    print()
    print("Unpacking:")
    for i in range(3):
        op = (packed >> (i * 8)) & 0xFF
        print(f"  Position {i}: 0x{op:02x} = {operations_pb2.Operation.Name(op)}")


if __name__ == "__main__":
    main()

# 🌶️📦🔚
