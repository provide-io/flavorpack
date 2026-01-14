#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Comprehensive tests for operation chain packing/unpacking.

Tests all v0 required operations and their combinations to ensure
binary compatibility across Python, Go, and Rust implementations."""

from __future__ import annotations

import pytest

from flavor.psp.format_2025.constants import (
    OP_BZIP2,
    OP_GZIP,
    OP_NONE,
    OP_TAR,
    OP_XZ,
    OP_ZSTD,
    OPERATION_CHAINS,
    V0_REQUIRED_OPERATIONS,
)
from flavor.psp.format_2025.operations import (
    operations_to_string,
    pack_operations,
    string_to_operations,
    unpack_operations,
)


class TestOperationPacking:
    """Test operation chain packing functionality."""

    def test_single_operations(self) -> None:
        """Test packing/unpacking of single operations."""
        test_cases = [
            (OP_NONE, []),
            (OP_TAR, [OP_TAR]),
            (OP_GZIP, [OP_GZIP]),
            (OP_BZIP2, [OP_BZIP2]),
            (OP_XZ, [OP_XZ]),
            (OP_ZSTD, [OP_ZSTD]),
        ]

        for expected_packed, operations_list in test_cases:
            if operations_list:
                packed = pack_operations(operations_list)
                assert packed == expected_packed, f"Pack failed for {operations_list}"

                unpacked = unpack_operations(packed)
                assert unpacked == operations_list, f"Unpack failed for {operations_list}"

    def test_common_combinations(self) -> None:
        """Test common operation combinations."""
        # Test round-trip packing/unpacking for common combinations
        common_operations = [
            [OP_TAR, OP_GZIP],
            [OP_TAR, OP_BZIP2],
            [OP_TAR, OP_XZ],
            [OP_TAR, OP_ZSTD],
        ]

        for operations_list in common_operations:
            # Test packing
            packed = pack_operations(operations_list)

            # Test unpacking
            unpacked = unpack_operations(packed)
            assert unpacked == operations_list, f"Round-trip failed for {operations_list}"

            # Test string conversion produces valid output
            string_result = operations_to_string(packed)
            assert string_result, f"Empty string result for {operations_list}"

        # Test specific string mappings (canonical forms)
        string_test_cases = [
            ([OP_TAR, OP_GZIP], "tar.gz"),
            ([OP_TAR, OP_BZIP2], "tar.bz2"),
            ([OP_TAR, OP_XZ], "tar.xz"),
            ([OP_TAR, OP_ZSTD], "tar.zst"),
        ]

        for operations_list, expected_string in string_test_cases:
            packed = pack_operations(operations_list)
            string_result = operations_to_string(packed)
            assert string_result == expected_string, f"String conversion failed for {operations_list}"

    def test_operation_chain_constants(self) -> None:
        """Test all predefined operation chains."""
        for chain_name, operations_list in OPERATION_CHAINS.items():
            if not operations_list:  # Skip empty "raw" chain
                continue

            # Test string to operations
            packed_from_string = string_to_operations(chain_name)

            # Test manual packing
            packed_manual = pack_operations(operations_list)

            assert packed_from_string == packed_manual, f"Mismatch for chain '{chain_name}'"

            # Test round-trip
            unpacked = unpack_operations(packed_from_string)
            assert unpacked == operations_list, f"Round-trip failed for chain '{chain_name}'"

    def test_max_operations_chain(self) -> None:
        """Test maximum length operation chain (8 operations)."""
        # Create a chain with 8 operations (max allowed)
        max_operations = [
            OP_TAR,
            OP_GZIP,
            OP_TAR,
            OP_BZIP2,
            OP_TAR,
            OP_XZ,
            OP_TAR,
            OP_ZSTD,
        ]

        packed = pack_operations(max_operations)
        unpacked = unpack_operations(packed)

        assert unpacked == max_operations, "Max length chain round-trip failed"

    def test_operation_validation(self) -> None:
        """Test operation validation."""
        # Test too many operations
        with pytest.raises(ValueError, match="Maximum 8 operations"):
            pack_operations([OP_TAR] * 9)

        # Test invalid operation (not in v0 spec)
        with pytest.raises(ValueError, match="not supported in v0"):
            pack_operations([255])  # Invalid operation

        # Test out of range operation
        with pytest.raises(ValueError, match="out of range"):
            pack_operations([256])  # Too large

        with pytest.raises(ValueError, match="out of range"):
            pack_operations([-1])  # Negative

    def test_empty_operations(self) -> None:
        """Test empty operation chains."""
        # Test empty list
        packed = pack_operations([])
        assert packed == 0, "Empty operations should pack to 0"

        unpacked = unpack_operations(0)
        assert unpacked == [], "Zero should unpack to empty list"

        # Test string conversion
        string_result = operations_to_string(0)
        assert string_result == "raw", "Zero operations should be 'raw'"

    def test_string_parsing(self) -> None:
        """Test string to operations parsing."""
        test_cases = [
            ("raw", []),
            ("none", []),
            ("", []),
            ("tar", [OP_TAR]),
            ("gzip", [OP_GZIP]),
            ("tar|gzip", [OP_TAR, OP_GZIP]),
            ("tar.gz", [OP_TAR, OP_GZIP]),
            ("tgz", [OP_TAR, OP_GZIP]),
        ]

        for string_input, expected_operations in test_cases:
            packed = string_to_operations(string_input)
            unpacked = unpack_operations(packed)
            assert unpacked == expected_operations, f"String parsing failed for '{string_input}'"

    def test_invalid_string_operations(self) -> None:
        """Test invalid operation strings."""
        invalid_strings = [
            "invalid_operation",
            "tar|invalid",
            "unknown.format",
        ]

        for invalid_string in invalid_strings:
            with pytest.raises(ValueError):
                string_to_operations(invalid_string)

    def test_binary_format_compatibility(self) -> None:
        """Test specific binary format values for cross-language compatibility."""
        # These values must match across Python, Go, and Rust implementations
        test_cases = [
            # Single operations
            ([OP_TAR], 0x0000000000000001),
            ([OP_GZIP], 0x0000000000000010),
            # TAR + GZIP (most common)
            ([OP_TAR, OP_GZIP], 0x0000000000001001),
            # TAR + BZIP2
            ([OP_TAR, OP_BZIP2], 0x0000000000001301),
            # TAR + XZ
            ([OP_TAR, OP_XZ], 0x0000000000001601),
            # TAR + ZSTD
            ([OP_TAR, OP_ZSTD], 0x0000000000001B01),
        ]

        for operations_list, expected_packed in test_cases:
            packed = pack_operations(operations_list)
            assert packed == expected_packed, (
                f"Binary format mismatch for {operations_list}: got {packed:#018x}, expected {expected_packed:#018x}"
            )

            # Verify round-trip
            unpacked = unpack_operations(packed)
            assert unpacked == operations_list, f"Round-trip failed for {operations_list}"

    def test_v0_operations_coverage(self) -> None:
        """Test that all v0 required operations can be packed/unpacked."""
        for operation in V0_REQUIRED_OPERATIONS:
            if operation == OP_NONE:
                continue  # Skip OP_NONE as it's handled specially

            # Test single operation
            packed = pack_operations([operation])
            unpacked = unpack_operations(packed)
            assert unpacked == [operation], f"V0 operation {operation:#02x} failed round-trip"

    def test_operation_byte_positions(self) -> None:
        """Test that operations are packed in correct byte positions."""
        # Test specific byte positions in the 64-bit packed value
        operations = [OP_TAR, OP_GZIP, OP_BZIP2, OP_XZ]  # 0x01, 0x10, 0x13, 0x16
        packed = pack_operations(operations)

        # Verify each operation is in the correct byte position
        assert (packed & 0xFF) == OP_TAR, "OP_TAR should be in byte 0"
        assert ((packed >> 8) & 0xFF) == OP_GZIP, "OP_GZIP should be in byte 1"
        assert ((packed >> 16) & 0xFF) == OP_BZIP2, "OP_BZIP2 should be in byte 2"
        assert ((packed >> 24) & 0xFF) == OP_XZ, "OP_XZ should be in byte 3"

        # Verify unpacking preserves order
        unpacked = unpack_operations(packed)
        assert unpacked == operations, "Operation order not preserved in unpacking"


# 🌶️📦🔚
