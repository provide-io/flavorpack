#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""Generate test vectors for Go/Rust implementations of PSPF/2025 operation chains.

This script creates known-good binary data from the Python implementation
to ensure cross-language compatibility.
"""

import json
import logging
from pathlib import Path
import sys

from flavor.psp.format_2025.operations import (
    OP_AES256_GCM,
    OP_BZIP2,
    OP_GZIP,
    OP_TAR,
    OP_ZSTD,
    pack_operations,
)
from flavor.psp.format_2025.slots import SlotDescriptor

# Configure logging with emojis
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s", stream=sys.stdout)
logger = logging.getLogger(__name__)


# Custom log levels with emojis
def log_trace(msg: str):
    logger.debug(f"🔍 [TRACE] {msg}")


def log_debug(msg: str):
    logger.debug(f"🐛 [DEBUG] {msg}")


def log_info(msg: str):
    logger.info(f"📊 [INFO] {msg}")


def log_success(msg: str):
    logger.info(f"✅ [SUCCESS] {msg}")


def log_warning(msg: str):
    logger.warning(f"⚠️  [WARN] {msg}")


def log_error(msg: str):
    logger.error(f"❌ [ERROR] {msg}")


def generate_slot_descriptors():
    """Generate various SlotDescriptor test cases."""

    log_info("🎯 Starting slot descriptor generation")
    test_cases = []

    # Test case 1: No operations (raw)
    log_debug("Creating test case 1: raw data with no operations")
    desc1 = SlotDescriptor(
        id=1,
        name="test_raw.txt",
        offset=0,
        size=100,
        original_size=100,
        operations=0,  # No operations
        checksum=0x12345678,
        purpose=0,  # data
        lifecycle=0,  # runtime
    )
    log_trace(f"Descriptor 1: ID={desc1.id}, operations=0x{desc1.operations:016x}")
    test_cases.append(
        {
            "name": "raw_data",
            "description": "Raw data with no operations",
            "descriptor": desc1,
            "expected_operations": [],
        }
    )
    log_success("Test case 1 created: raw_data")

    # Test case 2: Single GZIP operation
    log_debug("Creating test case 2: single GZIP operation")
    packed_gzip = pack_operations([OP_GZIP])
    log_trace(f"Packing [OP_GZIP] -> 0x{packed_gzip:016x}")
    desc2 = SlotDescriptor(
        id=2,
        name="test_gzip.txt",
        offset=1024,
        size=512,
        original_size=1000,
        operations=packed_gzip,
        checksum=0xABCDEF01,
        purpose=1,  # code
        lifecycle=2,  # startup
    )
    log_trace(f"Descriptor 2: ID={desc2.id}, operations=0x{desc2.operations:016x}")
    test_cases.append(
        {
            "name": "gzip_only",
            "description": "Single GZIP operation",
            "descriptor": desc2,
            "expected_operations": [OP_GZIP],
        }
    )
    log_success("Test case 2 created: gzip_only")

    # Test case 3: TAR + GZIP (tar.gz)
    log_debug("Creating test case 3: TAR + GZIP chain (tar.gz)")
    packed_tar_gzip = pack_operations([OP_TAR, OP_GZIP])
    log_trace(f"Packing [OP_TAR, OP_GZIP] -> 0x{packed_tar_gzip:016x}")
    desc3 = SlotDescriptor(
        id=42,
        name="archive.tar.gz",
        offset=8192,
        size=4096,
        original_size=16384,
        operations=packed_tar_gzip,
        checksum=0xDEADBEEF,
        purpose=0,  # data
        lifecycle=1,  # cached
    )
    log_trace(f"Descriptor 3: ID={desc3.id}, operations=0x{desc3.operations:016x}")
    test_cases.append(
        {
            "name": "tar_gzip",
            "description": "TAR followed by GZIP (tar.gz)",
            "descriptor": desc3,
            "expected_operations": [OP_TAR, OP_GZIP],
        }
    )
    log_success("Test case 3 created: tar_gzip")

    # Test case 4: Complex chain
    log_debug("Creating test case 4: complex operation chain")
    packed_complex = pack_operations([OP_TAR, OP_ZSTD, OP_AES256_GCM])
    log_trace(f"Packing [OP_TAR, OP_ZSTD, OP_AES256_GCM] -> 0x{packed_complex:016x}")
    desc4 = SlotDescriptor(
        id=999,
        name="complex.data",
        offset=65536,
        size=32768,
        original_size=131072,
        operations=packed_complex,
        checksum=0xCAFEBABE,
        purpose=2,  # config
        lifecycle=0,  # runtime
        permissions=0o755,
    )
    log_trace(f"Descriptor 4: ID={desc4.id}, operations=0x{desc4.operations:016x}")
    test_cases.append(
        {
            "name": "complex_chain",
            "description": "TAR -> ZSTD -> AES256_GCM",
            "descriptor": desc4,
            "expected_operations": [OP_TAR, OP_ZSTD, OP_AES256_GCM],
        }
    )
    log_success("Test case 4 created: complex_chain")

    log_info(f"📦 Generated {len(test_cases)} slot descriptor test cases")
    return test_cases


def save_test_vectors(test_cases):
    """Save test vectors for Go and Rust implementations."""

    log_info("💾 Starting to save test vectors")

    # Create output directories
    go_testdata = Path("src/flavor-go/pkg/psp/format_2025/testdata")
    log_debug(f"Creating Go testdata directory: {go_testdata}")
    go_testdata.mkdir(parents=True, exist_ok=True)

    rust_testdata = Path("src/flavor-rs/src/psp/format_2025/testdata")
    log_debug(f"Creating Rust testdata directory: {rust_testdata}")
    rust_testdata.mkdir(parents=True, exist_ok=True)

    # Prepare JSON metadata and binary data
    log_info("🔨 Preparing JSON metadata and binary data")
    json_data = []
    binary_data = b""

    for i, case in enumerate(test_cases):
        log_trace(f"Processing test case {i}: {case['name']}")
        desc = case["descriptor"]
        packed = desc.pack()

        # Verify it's exactly 64 bytes
        if len(packed) != 64:
            log_error(f"Descriptor {case['name']} must be 64 bytes, got {len(packed)}")
            raise AssertionError(f"Descriptor must be 64 bytes, got {len(packed)}")
        log_trace("✓ Packed descriptor is exactly 64 bytes")

        # Add to binary data
        binary_data += packed
        log_trace(f"Binary data size: {len(binary_data)} bytes")

        # Create JSON entry
        json_entry = {
            "name": case["name"],
            "description": case["description"],
            "offset": i * 64,  # Offset in binary file
            "hex": packed.hex(),
            "fields": {
                "id": desc.id,
                "name_hash": desc.name_hash,
                "offset": desc.offset,
                "size": desc.size,
                "original_size": desc.original_size,
                "operations": desc.operations,
                "operations_hex": f"0x{desc.operations:016x}",
                "checksum": desc.checksum,
                "purpose": desc.purpose,
                "lifecycle": desc.lifecycle,
                "permissions": desc.permissions,
            },
            "expected_operations": case["expected_operations"],
            "expected_operations_packed": pack_operations(case["expected_operations"]),
        }
        json_data.append(json_entry)
        log_debug(f"📝 Created JSON entry for {case['name']}")

    # Save binary files
    log_info("💾 Writing binary descriptor files")
    with open(go_testdata / "descriptors.bin", "wb") as f:
        f.write(binary_data)
    log_success(f"Wrote {len(binary_data)} bytes to Go descriptors.bin")

    with open(rust_testdata / "descriptors.bin", "wb") as f:
        f.write(binary_data)
    log_success(f"Wrote {len(binary_data)} bytes to Rust descriptors.bin")

    # Save JSON metadata
    log_info("📄 Writing JSON metadata files")
    with open(go_testdata / "test_vectors.json", "w") as f:
        json.dump(json_data, f, indent=2)
    log_success(f"Wrote test vectors JSON for Go ({len(json_data)} entries)")

    with open(rust_testdata / "test_vectors.json", "w") as f:
        json.dump(json_data, f, indent=2)
    log_success(f"Wrote test vectors JSON for Rust ({len(json_data)} entries)")

    # Generate Go test constants
    log_info("🔧 Generating Go test constants")
    go_constants = generate_go_constants(json_data)
    with open(go_testdata / "vectors_test.go", "w") as f:
        f.write(go_constants)
    log_success("Generated Go test constants file")

    log_success(f"✨ Successfully saved {len(test_cases)} test vectors")
    log_info("📁 Files saved to:")
    log_info(f"   • Go: {go_testdata}")
    log_info(f"   • Rust: {rust_testdata}")


def generate_go_constants(json_data):
    """Generate Go test constants from test vectors."""

    log_debug("📝 Generating Go test constants")

    go_code = """// Code generated by generate_test_vectors.py; DO NOT EDIT.

package format_2025

// TestVectors contains binary test data from Python implementation
var TestVectors = []struct {
    Name        string
    Description string
    Binary      []byte
    ID          uint64
    Operations  uint64
}{
"""

    for case in json_data:
        log_trace(f"Generating Go constant for {case['name']}")
        # Format hex as Go byte array
        hex_str = case["hex"]
        bytes_str = ", ".join([f"0x{hex_str[i : i + 2]}" for i in range(0, len(hex_str), 2)])

        go_code += f"""    {{
        Name:        "{case["name"]}",
        Description: "{case["description"]}",
        Binary:      []byte{{{bytes_str[:100]},
            {bytes_str[100:200] if len(bytes_str) > 100 else ""}
            {bytes_str[200:] if len(bytes_str) > 200 else ""}}},
        ID:          {case["fields"]["id"]},
        Operations:  {case["fields"]["operations_hex"]},
    }},
"""

    go_code += "}\n"
    log_trace(f"Generated {len(go_code)} bytes of Go code")
    return go_code


def generate_operation_tests():
    """Generate operation packing/unpacking test cases."""

    log_info("🔬 Generating operation packing/unpacking test cases")

    test_cases = [
        ([], 0x0, "empty/raw"),
        ([OP_GZIP], 0x10, "single GZIP"),
        ([OP_TAR], 0x01, "single TAR"),
        ([OP_TAR, OP_GZIP], 0x1001, "TAR + GZIP"),
        ([OP_TAR, OP_BZIP2], 0x1301, "TAR + BZIP2"),  # Fixed: BZIP2 is 0x13
        ([OP_TAR, OP_ZSTD], 0x1B01, "TAR + ZSTD"),  # Fixed: ZSTD is 0x1b
        ([OP_TAR, OP_GZIP, OP_AES256_GCM], 0x311001, "TAR + GZIP + AES256_GCM"),
    ]

    for ops, packed, desc in test_cases:
        log_trace(f"Test case: {desc} -> ops={ops}, packed=0x{packed:016x}")

    log_success(f"Generated {len(test_cases)} operation test cases")
    return test_cases


def main():
    """Generate all test vectors."""

    log_info("🚀 Starting PSPF/2025 test vector generation")
    log_info("=" * 60)

    # Generate slot descriptors
    slot_cases = generate_slot_descriptors()
    save_test_vectors(slot_cases)

    # Generate operation test cases
    op_cases = generate_operation_tests()

    # Save operation test cases
    log_info("📝 Saving operation test cases")
    go_testdata = Path("src/flavor-go/pkg/psp/format_2025/testdata")
    op_file = go_testdata / "operations.json"
    log_debug(f"Writing operation tests to {op_file}")

    with open(op_file, "w") as f:
        json.dump(
            [
                {
                    "operations": ops,
                    "packed": packed,
                    "packed_hex": f"0x{packed:016x}",
                    "description": desc,
                }
                for ops, packed, desc in op_cases
            ],
            f,
            indent=2,
        )

    log_success(f"Wrote {len(op_cases)} operation test cases to {op_file}")

    log_info("=" * 60)
    log_success("✨ Test vector generation complete!")
    log_info("🎯 Summary:")
    log_info(f"   • Generated {len(slot_cases)} slot descriptor test cases")
    log_info(f"   • Generated {len(op_cases)} operation test cases")
    log_info("   • Created test data for Go and Rust implementations")


if __name__ == "__main__":
    main()
# 🌶️📦🔚
