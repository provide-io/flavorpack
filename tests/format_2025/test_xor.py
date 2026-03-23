#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for flavor.utils.xor — XOR encode/decode."""

import pytest

from flavor.utils.xor import XOR_KEY, xor_decode, xor_encode


@pytest.mark.unit
class TestXorEncode:
    """Tests for xor_encode."""

    def test_empty_bytes(self) -> None:
        """Encoding empty bytes returns empty bytes."""
        assert xor_encode(b"") == b""

    def test_single_byte(self) -> None:
        """Encoding a single byte XORs with first key byte."""
        data = bytes([0xFF])
        expected = bytes([0xFF ^ XOR_KEY[0]])
        assert xor_encode(data) == expected

    @pytest.mark.parametrize(
        "data",
        [
            b"\x00",
            b"\xff",
            b"hello",
            b"\x00" * 16,
            b"\xff" * 16,
            bytes(range(256)),
        ],
    )
    def test_encode_decode_roundtrip(self, data: bytes) -> None:
        """XOR encode followed by decode returns original data."""
        assert xor_decode(xor_encode(data)) == data

    @pytest.mark.parametrize(
        "data",
        [
            b"\x00",
            b"\xff",
            b"hello",
            b"\x00" * 16,
            b"\xff" * 16,
            bytes(range(256)),
        ],
    )
    def test_decode_encode_roundtrip(self, data: bytes) -> None:
        """XOR decode followed by encode returns original data (symmetric)."""
        assert xor_encode(xor_decode(data)) == data

    def test_key_repeats(self) -> None:
        """Key wraps around for data longer than the key."""
        key = bytes([1, 2])
        data = bytes([0xAA, 0xBB, 0xCC, 0xDD])
        expected = bytes([0xAA ^ 1, 0xBB ^ 2, 0xCC ^ 1, 0xDD ^ 2])
        assert xor_encode(data, key) == expected

    def test_custom_key(self) -> None:
        """Custom key is applied instead of default."""
        custom_key = bytes([0xFF])
        data = bytes([0xAA, 0xBB])
        result = xor_encode(data, custom_key)
        assert result == bytes([0xAA ^ 0xFF, 0xBB ^ 0xFF])

    def test_decode_equals_encode(self) -> None:
        """xor_decode and xor_encode produce identical output (XOR is symmetric)."""
        data = b"test_data_12345"
        assert xor_decode(data) == xor_encode(data)

    def test_encode_different_from_input(self) -> None:
        """Encoded output differs from input when key is nonzero."""
        data = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        encoded = xor_encode(data)
        # At least one byte should differ (since XOR_KEY is non-zero)
        assert any(e != d for e, d in zip(encoded, data, strict=True))

    def test_double_encode_equals_original(self) -> None:
        """Encoding twice with the same key returns original."""
        data = b"double_encode_test"
        assert xor_encode(xor_encode(data)) == data

    def test_pi_key_values(self) -> None:
        """Default key is the first 8 digits of pi."""
        assert bytes([3, 1, 4, 1, 5, 9, 2, 6]) == XOR_KEY


# 🌶️📦🔚
