#!/usr/bin/env python3
"""
Memray stress test: Operation chain pack/unpack hot path.

Profiles allocation patterns in:
- pack_operations() with various operation chains
- unpack_operations() from packed values
- Round-trip pack -> unpack cycles (assert equal)
"""

import os

os.environ.setdefault("LOG_LEVEL", "ERROR")

from flavor.psp.format_2025.constants import (
    OP_BZIP2,
    OP_GZIP,
    OP_TAR,
    OP_XZ,
    OP_ZSTD,
)
from flavor.psp.format_2025.operations import (
    pack_operations,
    unpack_operations,
)

# 5 different operation chains to exercise various code paths
OPERATION_CHAINS = [
    [OP_TAR, OP_GZIP],  # tar.gz (most common)
    [OP_TAR, OP_ZSTD],  # tar.zst
    [OP_TAR, OP_XZ],  # tar.xz
    [OP_TAR, OP_BZIP2],  # tar.bz2
    [OP_GZIP],  # gzip only
]


def stress_operations() -> None:
    """Stress test operation chain pack/unpack hot paths."""
    # Warmup - separate import-time allocations
    _ = pack_operations([OP_TAR, OP_GZIP])
    _ = unpack_operations(pack_operations([OP_TAR, OP_GZIP]))

    # 50K pack cycles (10K per chain x 5 chains)
    for _ in range(10_000):
        for chain in OPERATION_CHAINS:
            _ = pack_operations(chain)

    # 50K unpack cycles from pre-packed values
    packed_values = [pack_operations(chain) for chain in OPERATION_CHAINS]
    for _ in range(10_000):
        for packed in packed_values:
            _ = unpack_operations(packed)

    # 25K round-trip cycles (5K per chain x 5 chains) - assert equality
    for _ in range(5_000):
        for chain in OPERATION_CHAINS:
            packed = pack_operations(chain)
            unpacked = unpack_operations(packed)
            assert unpacked == chain, f"Round-trip failed: {chain} -> {packed} -> {unpacked}"

    print("Operations stress test complete: 125K cycles")


def main() -> None:
    """Entry point."""
    stress_operations()


if __name__ == "__main__":
    main()
