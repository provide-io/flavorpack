#!/usr/bin/env python3
"""
PSPF/2025 Operation Chain System
Implements packed operation chains for slot transformations
"""

# Import generated protobuf operations
from flavor.psp.format_2025.generated.modules import operations_pb2

# Re-export operation constants for convenience
OP_NONE = operations_pb2.OP_NONE
OP_TAR = operations_pb2.OP_TAR
OP_GZIP = operations_pb2.OP_GZIP
OP_BZIP2 = operations_pb2.OP_BZIP2
OP_XZ = operations_pb2.OP_XZ
OP_ZSTD = operations_pb2.OP_ZSTD
OP_LZ4 = operations_pb2.OP_LZ4
OP_BROTLI = operations_pb2.OP_BROTLI
OP_AES256_GCM = operations_pb2.OP_AES256_GCM
OP_CHACHA20_POLY1305 = operations_pb2.OP_CHACHA20_POLY1305
OP_BASE64 = operations_pb2.OP_BASE64
OP_SHA256 = operations_pb2.OP_SHA256
OP_ED25519_SIGN = operations_pb2.OP_ED25519_SIGN
OP_TERMINAL = operations_pb2.OP_TERMINAL



def pack_operations(operations: list[int]) -> int:
    """
    Pack a list of operations into a 64-bit integer.
    
    Each operation takes 8 bits, allowing up to 8 operations in the chain.
    Operations are packed in execution order (first operation in LSB).
    
    Args:
        operations: List of operation constants (max 8)
    
    Returns:
        Packed 64-bit integer
    
    Example:
        >>> pack_operations([OP_TAR, OP_GZIP])
        0x1001  # 0x01 | (0x10 << 8)
    """
    if len(operations) > 8:
        raise ValueError(f"Maximum 8 operations allowed, got {len(operations)}")
    
    packed = 0
    for i, op in enumerate(operations):
        if op < 0 or op > 255:
            raise ValueError(f"Operation {op} out of range (0-255)")
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
        if op == 0 or op == OP_TERMINAL:
            break
        operations.append(op)
    
    return operations




def operations_to_string(packed: int) -> str:
    """
    Convert packed operations to human-readable string.
    
    Args:
        packed: Packed operations as 64-bit integer
    
    Returns:
        String representation like "TAR|GZIP"
    
    Example:
        >>> operations_to_string(0x1001)
        "TAR|GZIP"
    """
    if packed == 0:
        return "RAW"
    
    operations = unpack_operations(packed)
    names = []
    for op in operations:
        try:
            name = operations_pb2.Operation.Name(op)
            # Remove OP_ prefix for readability
            if name.startswith("OP_"):
                name = name[3:]
            names.append(name)
        except ValueError:
            names.append(f"UNKNOWN_{op:02x}")
    
    return "|".join(names)


def string_to_operations(op_string: str) -> int:
    """
    Parse operation string to packed operations.
    
    Args:
        op_string: String like "TAR|GZIP" or "tar.gz"
    
    Returns:
        Packed operations as 64-bit integer
    
    Example:
        >>> string_to_operations("TAR|GZIP")
        0x1001
        >>> string_to_operations("tar.gz")
        0x1001
    """
    if not op_string or op_string.upper() == "RAW":
        return 0
    
    # Handle legacy codec strings
    if op_string == "tar":
        return pack_operations([OP_TAR])
    elif op_string == "gz" or op_string == "gzip":
        return pack_operations([OP_GZIP])
    elif op_string == "tar.gz" or op_string == "tgz":
        return pack_operations([OP_TAR, OP_GZIP])
    elif op_string == "tar.bz2" or op_string == "tbz2":
        return pack_operations([OP_TAR, OP_BZIP2])
    elif op_string == "tar.xz" or op_string == "txz":
        return pack_operations([OP_TAR, OP_XZ])
    elif op_string == "tar.zst" or op_string == "tzst":
        return pack_operations([OP_TAR, OP_ZSTD])
    
    # Parse pipe-separated operations
    operations = []
    for part in op_string.split("|"):
        part = part.strip().upper()
        if not part:
            continue
        
        # Add OP_ prefix if not present
        if not part.startswith("OP_"):
            part = "OP_" + part
        
        # Look up operation
        try:
            op = getattr(operations_pb2, part)
            operations.append(op)
        except AttributeError:
            raise ValueError(f"Unknown operation: {part}")
    
    return pack_operations(operations)