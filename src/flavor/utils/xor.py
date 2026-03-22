#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

from __future__ import annotations

XOR_KEY = bytes([3, 1, 4, 1, 5, 9, 2, 6])  # First 8 digits of π


def xor_encode(data: bytes, key: bytes = XOR_KEY) -> bytes:
    """
    XOR encode data with repeating key.

    Args:
        data: Bytes to encode
        key: XOR key bytes (defaults to π digits)

    Returns:
        XOR encoded bytes
    """
    n = len(data)
    if n == 0:
        return b""
    key_len = len(key)
    key_int = int.from_bytes(key, "little")
    result = bytearray(n)
    # XOR key_len bytes at a time as integers
    aligned = n - (n % key_len)
    for i in range(0, aligned, key_len):
        chunk = int.from_bytes(data[i : i + key_len], "little")
        result[i : i + key_len] = (chunk ^ key_int).to_bytes(key_len, "little")
    # Handle remaining bytes
    for i in range(aligned, n):
        result[i] = data[i] ^ key[i % key_len]
    return bytes(result)


def xor_decode(data: bytes, key: bytes = XOR_KEY) -> bytes:
    """
    XOR decode data with repeating key.

    Since XOR is symmetric, this is the same as encoding.

    Args:
        data: Bytes to decode
        key: XOR key bytes (defaults to π digits)

    Returns:
        XOR decoded bytes
    """
    return xor_encode(data, key)  # XOR is its own inverse


# 🌶️📦🔚
