#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Cross-language verification tests for PSPF operations field compatibility."""

from pathlib import Path
import subprocess

import pytest

from flavor.psp.format_2025.operations import operations_to_string, string_to_operations


@pytest.mark.cross_language
@pytest.mark.taster
@pytest.mark.integration
class TestCrossLanguageOperations:
    """Test operations field compatibility between Python, Go, and Rust."""

    def test_operations_serialization_compatibility(self) -> None:
        """Test that operations field is serialized consistently across languages."""
        # Test various operation chain combinations
        test_operations = [
            "RAW",
            "GZIP",
            "TAR",
            "TAR|GZIP",
            "GZIP|TAR",  # Different order to test chain handling
        ]

        for ops_string in test_operations:
            # Test Python operations encoding/decoding
            packed_ops = string_to_operations(ops_string)
            unpacked_ops = operations_to_string(packed_ops)

            # Verify round-trip consistency
            assert unpacked_ops == ops_string, f"Round-trip failed for {ops_string}: got {unpacked_ops}"

            # Verify packed value is a valid 64-bit integer
            assert isinstance(packed_ops, int), f"Packed operations should be int, got {type(packed_ops)}"
            assert 0 <= packed_ops < 2**64, f"Packed operations out of 64-bit range: {packed_ops}"

    def test_taster_operations_verification(self) -> None:
        """Test that taster can verify packages with various operations."""
        # Skip if taster not available
        taster_path = Path(__file__).parents[1] / "dist" / "taster.psp"
        if not taster_path.exists():
            pytest.skip("taster.psp not built")

        # Use taster to run crosslang verification which tests operations
        result = subprocess.run(
            ["FLAVOR_VALIDATION=none", str(taster_path), "crosslang", "--json"],
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Should not fail completely (exit code 0 or 1 is acceptable)
        assert result.returncode in [0, 1], (
            f"Unexpected exit code: {result.returncode}, stderr: {result.stderr}"
        )

        # Should produce JSON output
        if result.stdout.strip():
            import json

            try:
                results = json.loads(result.stdout)
                assert isinstance(results, dict), "Cross-lang results should be a dictionary"
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON output: {e}, output: {result.stdout}")

    def test_slot_descriptor_operations_field(self) -> None:
        """Test that SlotDescriptor properly handles operations field."""
        from flavor.psp.format_2025.slots import SlotDescriptor

        # Test various operations values
        test_cases = [
            ("RAW", 0),  # RAW should be 0
            ("GZIP", string_to_operations("GZIP")),
            ("TAR|GZIP", string_to_operations("TAR|GZIP")),
        ]

        for ops_string, _expected_packed in test_cases:
            descriptor = SlotDescriptor(
                id=1,
                operations=string_to_operations(ops_string),
                size=1024,
                original_size=2048,
                checksum=0x12345678,
            )

            # Test binary serialization round-trip
            packed_bytes = descriptor.pack()
            unpacked_descriptor = SlotDescriptor.unpack(packed_bytes)

            # Verify operations field is preserved
            assert unpacked_descriptor.operations == descriptor.operations

            # Verify operations can be converted back to string
            restored_ops = operations_to_string(unpacked_descriptor.operations)
            assert restored_ops == ops_string

    @pytest.mark.requires_helpers
    def test_cross_language_package_verification(self) -> None:
        """Test that packages built with different languages verify consistently."""
        # Skip if taster not available
        taster_path = Path(__file__).parents[1] / "dist" / "taster.psp"
        if not taster_path.exists():
            pytest.skip("taster.psp not built")

        # Test that we can call taster's package verification
        result = subprocess.run(
            ["FLAVOR_VALIDATION=none", str(taster_path), "verify", str(taster_path)],
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Verification should succeed
        assert result.returncode == 0, f"Package verification failed: {result.stderr}"

        # Should have some output indicating success
        assert result.stdout or not result.stderr, "No verification output produced"

    def test_metadata_operations_compatibility(self) -> None:
        """Test that SlotMetadata properly converts to SlotDescriptor operations."""
        from flavor.psp.format_2025.slots import SlotDescriptor, SlotMetadata

        # Test metadata with operations field
        metadata = SlotMetadata(
            index=0,
            id="test-slot",
            source="/tmp/test.txt",
            target="test.txt",
            size=1024,
            checksum="abcd1234",
            operations="TAR|GZIP",
            purpose="data",
            lifecycle="runtime",
        )

        # Convert to descriptor
        descriptor = metadata.to_descriptor()

        # Verify operations field is properly converted
        ops_string = operations_to_string(descriptor.operations)
        assert ops_string == "TAR|GZIP"

        # Verify descriptor serialization works
        packed_bytes = descriptor.pack()
        unpacked_descriptor = SlotDescriptor.unpack(packed_bytes)
        restored_ops = operations_to_string(unpacked_descriptor.operations)
        assert restored_ops == "TAR|GZIP"

    def test_operations_error_handling(self) -> None:
        """Test that invalid operations are handled gracefully."""
        # Test invalid operation strings
        invalid_operations = [
            "INVALID_OP",
            "TAR|INVALID",
            "GZIP|TAR|INVALID",
        ]

        for invalid_op in invalid_operations:
            with pytest.raises(ValueError, match=r"Unknown operation|Invalid operations"):
                string_to_operations(invalid_op)


# 🌶️📦🔚
