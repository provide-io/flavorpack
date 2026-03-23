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
    # Extend key to cover all data in one pass
    full_key = key * (n // key_len) + key[: n % key_len]
    # Single large-int XOR — zero per-chunk allocations
    data_int = int.from_bytes(data, "little")
    key_int = int.from_bytes(full_key, "little")
    result_int = data_int ^ key_int
    return result_int.to_bytes(n, "little")


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
