#!/usr/bin/env python3
"""Generate test vectors for Go/Rust implementations of PSPF/2025 operation chains.

This script creates known-good binary data from the Python implementation
to ensure cross-language compatibility.
"""

import json
import struct
from pathlib import Path

from flavor.psp.format_2025.operations import (
    pack_operations, unpack_operations,
    OP_NONE, OP_TAR, OP_GZIP, OP_BZIP2, OP_ZSTD,
    OP_AES256_GCM
)
from flavor.psp.format_2025.slots import SlotDescriptor


def generate_slot_descriptors():
    """Generate various SlotDescriptor test cases."""
    
    test_cases = []
    
    # Test case 1: No operations (raw)
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
    test_cases.append({
        "name": "raw_data",
        "description": "Raw data with no operations",
        "descriptor": desc1,
        "expected_operations": []
    })
    
    # Test case 2: Single GZIP operation
    desc2 = SlotDescriptor(
        id=2,
        name="test_gzip.txt",
        offset=1024,
        size=512,
        original_size=1000,
        operations=pack_operations([OP_GZIP]),
        checksum=0xABCDEF01,
        purpose=1,  # code
        lifecycle=2,  # startup
    )
    test_cases.append({
        "name": "gzip_only",
        "description": "Single GZIP operation",
        "descriptor": desc2,
        "expected_operations": [OP_GZIP]
    })
    
    # Test case 3: TAR + GZIP (tar.gz)
    desc3 = SlotDescriptor(
        id=42,
        name="archive.tar.gz",
        offset=8192,
        size=4096,
        original_size=16384,
        operations=pack_operations([OP_TAR, OP_GZIP]),
        checksum=0xDEADBEEF,
        purpose=0,  # data
        lifecycle=1,  # cached
    )
    test_cases.append({
        "name": "tar_gzip",
        "description": "TAR followed by GZIP (tar.gz)",
        "descriptor": desc3,
        "expected_operations": [OP_TAR, OP_GZIP]
    })
    
    # Test case 4: Complex chain
    desc4 = SlotDescriptor(
        id=999,
        name="complex.data",
        offset=65536,
        size=32768,
        original_size=131072,
        operations=pack_operations([OP_TAR, OP_ZSTD, OP_AES256_GCM]),
        checksum=0xCAFEBABE,
        purpose=2,  # config
        lifecycle=0,  # runtime
        permissions=0o755,
    )
    test_cases.append({
        "name": "complex_chain",
        "description": "TAR -> ZSTD -> AES256_GCM",
        "descriptor": desc4,
        "expected_operations": [OP_TAR, OP_ZSTD, OP_AES256_GCM]
    })
    
    return test_cases


def save_test_vectors(test_cases):
    """Save test vectors for Go and Rust implementations."""
    
    # Create output directories
    go_testdata = Path("ingredients/flavor-go/pkg/psp/format_2025/testdata")
    go_testdata.mkdir(parents=True, exist_ok=True)
    
    rust_testdata = Path("ingredients/flavor-rs/src/psp/format_2025/testdata")
    rust_testdata.mkdir(parents=True, exist_ok=True)
    
    # Prepare JSON metadata and binary data
    json_data = []
    binary_data = b""
    
    for i, case in enumerate(test_cases):
        desc = case["descriptor"]
        packed = desc.pack()
        
        # Verify it's exactly 64 bytes
        assert len(packed) == 64, f"Descriptor must be 64 bytes, got {len(packed)}"
        
        # Add to binary data
        binary_data += packed
        
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
            "expected_operations_packed": pack_operations(case["expected_operations"])
        }
        json_data.append(json_entry)
    
    # Save binary files
    with open(go_testdata / "descriptors.bin", "wb") as f:
        f.write(binary_data)
    with open(rust_testdata / "descriptors.bin", "wb") as f:
        f.write(binary_data)
    
    # Save JSON metadata
    with open(go_testdata / "test_vectors.json", "w") as f:
        json.dump(json_data, f, indent=2)
    with open(rust_testdata / "test_vectors.json", "w") as f:
        json.dump(json_data, f, indent=2)
    
    # Generate Go test constants
    go_constants = generate_go_constants(json_data)
    with open(go_testdata / "vectors_test.go", "w") as f:
        f.write(go_constants)
    
    print(f"✅ Generated {len(test_cases)} test vectors")
    print(f"📁 Saved to {go_testdata} and {rust_testdata}")
    

def generate_go_constants(json_data):
    """Generate Go test constants from test vectors."""
    
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
        # Format hex as Go byte array
        hex_str = case["hex"]
        bytes_str = ", ".join([f"0x{hex_str[i:i+2]}" for i in range(0, len(hex_str), 2)])
        
        go_code += f"""    {{
        Name:        "{case['name']}",
        Description: "{case['description']}",
        Binary:      []byte{{{bytes_str[:100]},
            {bytes_str[100:200] if len(bytes_str) > 100 else ""}
            {bytes_str[200:] if len(bytes_str) > 200 else ""}}},
        ID:          {case['fields']['id']},
        Operations:  {case['fields']['operations_hex']},
    }},
"""
    
    go_code += "}\n"
    return go_code


def generate_operation_tests():
    """Generate operation packing/unpacking test cases."""
    
    test_cases = [
        ([], 0x0, "empty/raw"),
        ([OP_GZIP], 0x10, "single GZIP"),
        ([OP_TAR], 0x01, "single TAR"),
        ([OP_TAR, OP_GZIP], 0x1001, "TAR + GZIP"),
        ([OP_TAR, OP_BZIP2], 0x1101, "TAR + BZIP2"),
        ([OP_TAR, OP_ZSTD], 0x1201, "TAR + ZSTD"),
        ([OP_TAR, OP_GZIP, OP_AES256_GCM], 0x311001, "TAR + GZIP + AES256_GCM"),
    ]
    
    return test_cases


def main():
    """Generate all test vectors."""
    
    print("🔧 Generating PSPF/2025 test vectors...")
    
    # Generate slot descriptors
    slot_cases = generate_slot_descriptors()
    save_test_vectors(slot_cases)
    
    # Generate operation test cases
    op_cases = generate_operation_tests()
    
    # Save operation test cases
    go_testdata = Path("ingredients/flavor-go/pkg/psp/format_2025/testdata")
    with open(go_testdata / "operations.json", "w") as f:
        json.dump([{
            "operations": ops,
            "packed": packed,
            "packed_hex": f"0x{packed:016x}",
            "description": desc
        } for ops, packed, desc in op_cases], f, indent=2)
    
    print(f"✅ Generated {len(op_cases)} operation test cases")
    print("✨ Test vector generation complete!")


if __name__ == "__main__":
    main()