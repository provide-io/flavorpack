#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PSPF/2025 v0 operation chain helpers.

Implements packed operation chains for slot transformations using v0 required operations only.
"""

from __future__ import annotations

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

# Export key operations for external use
__all__ = [
    "OP_BZIP2",
    "OP_GZIP",
    "OP_NONE",
    "OP_TAR",
    "OP_XZ",
    "OP_ZSTD",
    "operations_to_string",
    "pack_operations",
    "unpack_operations",
]

# Import generated protobuf operations for name lookup
try:
    from flavor.psp.format_2025.generated.modules import operations_pb2

    _HAS_PROTOBUF = True
except ImportError:
    _HAS_PROTOBUF = False


def pack_operations(operations: list[int]) -> int:
    """
    Pack a list of operations into a 64-bit integer.

    Each operation takes 8 bits, allowing up to 8 operations in the chain.
    Operations are packed in execution order (first operation in LSB).

    Args:
        operations: List of operation constants (max 8)

    Returns:
        Packed 64-bit integer

    Raises:
        ValueError: If operation is invalid or unsupported in v0

    Example:
        >>> pack_operations([OP_TAR, OP_GZIP])
        0x1001  # 0x01 | (0x10 << 8)
    """
    if len(operations) > 8:
        raise ValueError(f"Maximum 8 operations allowed, got {len(operations)}")

    # Validate all operations are supported in v0
    for op in operations:
        if op < 0 or op > 255:
            raise ValueError(f"Operation {op} out of range (0-255)")
        if op != OP_NONE and op not in V0_REQUIRED_OPERATIONS:
            raise ValueError(f"Operation 0x{op:02x} not supported in v0")

    packed = 0
    for i, op in enumerate(operations):
        packed |= (op & 0xFF) << (i * 8)

    return packed


def unpack_operations(packed: int) -> list[int]:
    """
    Unpack a 64-bit integer into a list of operations.

    Args:
        packed: Packed 64-bit integer

    Returns:
        List of operation constants

    Example:
        >>> unpack_operations(0x1001)
        [OP_TAR, OP_GZIP]
    """
    operations = []
    for i in range(8):
        op = (packed >> (i * 8)) & 0xFF
        if op == 0:  # OP_NONE terminates the chain
            break
        operations.append(op)

    return operations


def operations_to_string(packed: int) -> str:
    """
    Convert packed operations to human-readable string.

    Args:
        packed: Packed operations as 64-bit integer

    Returns:
        String representation like "TAR|GZIP" or standard format like "tar.gz"

    Example:
        >>> operations_to_string(0x1001)
        "tar.gz"
    """
    if packed == 0:
        return "raw"

    operations = unpack_operations(packed)

    # Check for common operation chains first
    for name, ops in OPERATION_CHAINS.items():
        if operations == ops:
            return name

    # Fall back to pipe format
    names = []
    for op in operations:
        name = _get_operation_name(op)
        names.append(name.lower())

    return "|".join(names)


def _get_operation_name(op: int) -> str:
    """Get human-readable name for operation."""
    op_names = {
        OP_NONE: "NONE",
        OP_TAR: "TAR",
        OP_GZIP: "GZIP",
        OP_BZIP2: "BZIP2",
        OP_XZ: "XZ",
        OP_ZSTD: "ZSTD",
    }

    name = op_names.get(op)
    if name:
        return name

    # Try protobuf lookup if available
    if _HAS_PROTOBUF:
        try:
            name = operations_pb2.Operation.Name(op)
            if name.startswith("OP_"):
                name = name[3:]
            return name
        except (ValueError, AttributeError):
            pass

    return f"UNKNOWN_{op:02x}"


def string_to_operations(op_string: str) -> int:
    """
    Parse operation string to packed operations.

    Args:
        op_string: String like "tar|gzip", "tar.gz", or "raw"

    Returns:
        Packed operations as 64-bit integer

    Raises:
        ValueError: If operation string is invalid or uses unsupported operations

    Example:
        >>> string_to_operations("tar.gz")
        0x1001
        >>> string_to_operations("tar|gzip")
        0x1001
    """
    if not op_string or op_string.lower() in ("raw", "none"):
        return 0

    op_string = op_string.lower()

    # Check for exact match in operation chains first
    if op_string in OPERATION_CHAINS:
        return pack_operations(OPERATION_CHAINS[op_string])

    # Handle pipe-separated operations
    if "|" in op_string:
        operations = []
        for part in op_string.split("|"):
            part = part.strip().upper()
            if not part:
                continue

            # Map to v0 operation constants
            op_map = {
                "TAR": OP_TAR,
                "GZIP": OP_GZIP,
                "BZIP2": OP_BZIP2,
                "XZ": OP_XZ,
                "ZSTD": OP_ZSTD,
            }

            if part in op_map:
                operations.append(op_map[part])
            else:
                raise ValueError(f"Unsupported v0 operation: {part}")

        return pack_operations(operations)

    # Single operation
    single_ops = {
        "tar": [OP_TAR],
        "gzip": [OP_GZIP],
        "bzip2": [OP_BZIP2],
        "xz": [OP_XZ],
        "zstd": [OP_ZSTD],
    }

    if op_string in single_ops:
        return pack_operations(single_ops[op_string])

    raise ValueError(f"Unknown v0 operation string: {op_string}")


# 🌶️📦🔚
