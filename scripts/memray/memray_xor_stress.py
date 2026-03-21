#!/usr/bin/env python3
"""
Memray stress test: XOR encode/decode hot path.

Profiles allocation patterns in:
- xor_encode() across 4 payload sizes (1KB, 10KB, 100KB, 1MB)
- xor_decode() across 4 payload sizes
- Round-trip encode -> decode cycles (assert decoded == original)
"""

import os

os.environ.setdefault("LOG_LEVEL", "ERROR")

from flavor.utils.xor import XOR_KEY, xor_decode, xor_encode

# Payload sizes with cycle counts scaled inversely to size
# (keeps total data processed ~1GB across all sizes)
PAYLOAD_CONFIGS = [
    ("1KB", 1_024, 10_000),
    ("10KB", 10_240, 5_000),
    ("100KB", 102_400, 1_000),
    ("1MB", 1_048_576, 200),
]


def _make_payload(size: int) -> bytes:
    """Create a deterministic test payload of given size."""
    # Repeating pattern that exercises all byte values
    pattern = bytes(range(256))
    repeats = (size // len(pattern)) + 1
    return (pattern * repeats)[:size]


def stress_xor() -> None:
    """Stress test XOR encode/decode hot paths."""
    payloads = [(name, _make_payload(size), cycles) for name, size, cycles in PAYLOAD_CONFIGS]

    # Warmup - separate import-time allocations
    _ = xor_encode(b"warmup", key=XOR_KEY)
    _ = xor_decode(xor_encode(b"warmup", key=XOR_KEY), key=XOR_KEY)

    total_cycles = 0

    # Encode cycles (scaled per size)
    for _name, payload, cycles in payloads:
        for _ in range(cycles):
            _ = xor_encode(payload, key=XOR_KEY)
        total_cycles += cycles

    # Decode cycles (scaled per size)
    for _name, payload, cycles in payloads:
        encoded = xor_encode(payload, key=XOR_KEY)
        for _ in range(cycles):
            _ = xor_decode(encoded, key=XOR_KEY)
        total_cycles += cycles

    # Round-trip cycles (half the encode count per size)
    for _name, payload, cycles in payloads:
        rt_cycles = cycles // 2
        for _ in range(rt_cycles):
            encoded = xor_encode(payload, key=XOR_KEY)
            decoded = xor_decode(encoded, key=XOR_KEY)
            assert decoded == payload, f"Round-trip failed for {_name}"
        total_cycles += rt_cycles

    print(f"XOR stress test complete: {total_cycles} cycles across 4 payload sizes")


def main() -> None:
    """Entry point."""
    stress_xor()


if __name__ == "__main__":
    main()
