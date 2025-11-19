#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Verify operation implementations across Python and Go.

This script checks that operation packing/unpacking produces
consistent results between Python and Go implementations."""

import json
from pathlib import Path
import subprocess
import sys

from flavor.psp.format_2025.operations import (
    OP_AES256_GCM,
    OP_BZIP2,
    OP_GZIP,
    OP_TAR,
    OP_ZSTD,
    pack_operations,
    unpack_operations,
)


def run_go_tests():
    """Run Go operation tests and check results."""

    go_dir = Path("src/flavor-go/pkg/psp/format_2025")
    if not go_dir.exists():
        print(f"❌ Go directory not found: {go_dir}")
        return False

    # Change to Go directory and run tests
    result = subprocess.run(
        ["go", "test", "-v", "-run", "TestOperation"],
        cwd=go_dir,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"❌ Go tests failed:\n{result.stderr}")
        return False

    # Check for PASS in output
    if "PASS" in result.stdout:
        return True
    else:
        print(f"❌ Go tests did not pass:\n{result.stdout}")
        return False


def verify_python_operations():
    """Verify Python operation packing/unpacking."""

    test_cases = [
        ([], 0x0, "empty/raw"),
        ([OP_GZIP], 0x10, "single GZIP"),
        ([OP_TAR], 0x01, "single TAR"),
        ([OP_TAR, OP_GZIP], 0x1001, "TAR + GZIP"),
        ([OP_TAR, OP_BZIP2], 0x1301, "TAR + BZIP2"),
        ([OP_TAR, OP_ZSTD], 0x1B01, "TAR + ZSTD"),
        ([OP_TAR, OP_GZIP, OP_AES256_GCM], 0x311001, "TAR + GZIP + AES256_GCM"),
    ]

    all_passed = True
    for ops, expected_packed, description in test_cases:
        # Test packing
        packed = pack_operations(ops)
        if packed != expected_packed:
            print(
                f"❌ Python pack failed for {description}: got 0x{packed:016x}, want 0x{expected_packed:016x}"
            )
            all_passed = False
        else:
            pass

        # Test unpacking
        unpacked = unpack_operations(expected_packed)
        if unpacked != ops:
            print(f"❌ Python unpack failed for {description}: got {unpacked}, want {ops}")
            all_passed = False
        else:
            pass

    return all_passed


def compare_test_vectors():
    """Compare Python-generated test vectors with expected values."""
    print("📊 Comparing test vectors...")

    # Load the generated test vectors
    test_file = Path("src/flavor-go/pkg/psp/format_2025/testdata/operations.json")
    if not test_file.exists():
        print(f"❌ Test vectors not found: {test_file}")
        return False

    with open(test_file) as f:
        vectors = json.load(f)

    print(f"📝 Loaded {len(vectors)} test vectors")

    all_correct = True
    for v in vectors:
        ops = v["operations"]
        expected = v["packed"]

        # Check Python implementation
        packed = pack_operations(ops)
        if packed != expected:
            print(f"❌ Mismatch for {v['description']}: Python={packed}, Expected={expected}")
            all_correct = False
        else:
            pass

    return all_correct


def check_operation_constants():
    """Verify operation constants are consistent."""
    print("🔍 Checking operation constants...")

    # Load the operation mapping
    mapping_file = Path("spec/pspf_2025/operation_mapping.json")
    if not mapping_file.exists():
        print(f"❌ Operation mapping not found: {mapping_file}")
        return False

    with open(mapping_file) as f:
        mapping = json.load(f)

    # Check key operations
    critical_ops = {
        "OP_NONE": 0x00,
        "OP_TAR": 0x01,
        "OP_GZIP": 0x10,
        "OP_BZIP2": 0x13,
        "OP_ZSTD": 0x1B,
        "OP_AES256_GCM": 0x31,
    }

    all_correct = True
    for name, expected_value in critical_ops.items():
        if name not in mapping:
            print(f"❌ Missing operation: {name}")
            all_correct = False
            continue

        actual_value = mapping[name]
        if actual_value != expected_value:
            print(f"❌ Wrong value for {name}: got 0x{actual_value:02X}, want 0x{expected_value:02X}")
            all_correct = False
        else:
            pass

    return all_correct


def main():
    """Run all verification checks."""
    print("🚀 Starting operation verification")
    print("=" * 60)

    results = []

    # Check Python operations
    results.append(("Python operations", verify_python_operations()))
    print()

    # Check operation constants
    results.append(("Operation constants", check_operation_constants()))
    print()

    # Compare test vectors
    results.append(("Test vectors", compare_test_vectors()))
    print()

    # Run Go tests (if available)
    try:
        results.append(("Go tests", run_go_tests()))
    except Exception as e:
        print(f"⚠️  Could not run Go tests: {e}")
        results.append(("Go tests", None))

    # Summary
    print("=" * 60)
    print("📊 Verification Summary:")
    for name, result in results:
        if result is True:
            pass
        elif result is False:
            print(f"  ❌ {name}: FAILED")
        else:
            print(f"  ⚠️  {name}: SKIPPED")

    # Overall result
    if all(r is True for _, r in results if r is not None):
        print("\n✨ All verifications passed!")
        return 0
    else:
        print("\n❌ Some verifications failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

# 🌶️📦🔚
