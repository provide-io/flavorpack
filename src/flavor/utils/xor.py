"""XOR encoding utilities for PSPF magic bytes obfuscation."""

# XOR key - digits of π (memorable, non-obvious)
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
    return bytes(data[i] ^ key[i % len(key)] for i in range(len(data)))


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
