"""
Archive operation definitions and constants.

This module defines all operation types without requiring protobuf.
Compatible with protobuf enum values for serialization.
"""

from enum import IntEnum
from typing import Any


class Operation(IntEnum):
    """
    Archive operation types.
    
    Values are fixed for compatibility - NEVER change existing values!
    """
    
    # No operation
    NONE = 0x00
    
    # BUNDLE operations (0x01-0x0F) - Combine multiple files
    BUNDLE_TAR = 0x01       # POSIX TAR archive
    BUNDLE_ZIP = 0x02       # ZIP archive container  
    BUNDLE_CPIO = 0x03      # CPIO archive
    BUNDLE_AR = 0x04        # AR archive (deb packages)
    
    # COMPRESS operations (0x10-0x2F) - Reduce size
    COMPRESS_GZIP = 0x10      # GZIP (DEFLATE + headers)
    COMPRESS_DEFLATE = 0x11   # Raw DEFLATE algorithm
    COMPRESS_BZIP2 = 0x12     # BZIP2 compression
    COMPRESS_XZ = 0x13        # XZ/LZMA2 compression
    COMPRESS_ZSTD = 0x14      # Zstandard
    COMPRESS_LZ4 = 0x15       # LZ4 (very fast)
    COMPRESS_BROTLI = 0x16    # Brotli (web-optimized)
    COMPRESS_SNAPPY = 0x17    # Snappy (Google)
    
    # ENCRYPT operations (0x30-0x3F) - Secure data
    ENCRYPT_AES256 = 0x30     # AES-256-GCM
    ENCRYPT_CHACHA20 = 0x31   # ChaCha20-Poly1305
    ENCRYPT_ZIPCRYPTO = 0x32  # Legacy ZIP encryption
    ENCRYPT_GPG = 0x33        # GPG/PGP encryption
    
    # ENCODE operations (0x40-0x4F) - Transform encoding
    ENCODE_BASE64 = 0x40      # Base64 encoding
    ENCODE_HEX = 0x41         # Hexadecimal encoding
    ENCODE_ASCII85 = 0x42     # ASCII85 encoding
    
    # ZIP compound operations (0x50-0x5F)
    ZIP_STORE = 0x50          # ZIP with no compression
    ZIP_DEFLATE = 0x51        # ZIP with DEFLATE
    ZIP_BZIP2 = 0x52          # ZIP with BZIP2
    ZIP_LZMA = 0x53           # ZIP with LZMA
    ZIP_ENCRYPTED = 0x54      # ZIP with encryption
    
    # Other compound formats (0x60-0x6F)
    SEVENZ_LZMA = 0x60        # 7-Zip with LZMA
    RAR_V5 = 0x61             # RAR version 5


# Operation capabilities (bitflags)
class Capability(IntEnum):
    """What an operation can do."""
    NONE = 0
    BUNDLE = 1 << 0        # Can combine multiple files
    COMPRESS = 1 << 1      # Can compress data
    ENCRYPT = 1 << 2       # Can encrypt data
    STREAM = 1 << 3        # Supports streaming
    RANDOM_ACCESS = 1 << 4 # Supports random access
    PRESERVE_PERMS = 1 << 5 # Preserves permissions


# Operation metadata
OPERATION_INFO = {
    Operation.NONE: {
        "name": "NONE",
        "category": "none",
        "capabilities": Capability.NONE,
    },
    
    # Bundlers
    Operation.BUNDLE_TAR: {
        "name": "TAR",
        "category": "bundle",
        "capabilities": Capability.BUNDLE | Capability.STREAM | Capability.PRESERVE_PERMS,
    },
    Operation.BUNDLE_ZIP: {
        "name": "ZIP",
        "category": "bundle",
        "capabilities": Capability.BUNDLE | Capability.RANDOM_ACCESS,
    },
    Operation.BUNDLE_CPIO: {
        "name": "CPIO",
        "category": "bundle",
        "capabilities": Capability.BUNDLE | Capability.STREAM,
    },
    Operation.BUNDLE_AR: {
        "name": "AR",
        "category": "bundle",
        "capabilities": Capability.BUNDLE,
    },
    
    # Compressors
    Operation.COMPRESS_DEFLATE: {
        "name": "DEFLATE",
        "category": "compress",
        "capabilities": Capability.COMPRESS | Capability.STREAM,
    },
    Operation.COMPRESS_GZIP: {
        "name": "GZIP",
        "category": "compress",
        "capabilities": Capability.COMPRESS | Capability.STREAM,
    },
    Operation.COMPRESS_BZIP2: {
        "name": "BZIP2",
        "category": "compress",
        "capabilities": Capability.COMPRESS,
    },
    Operation.COMPRESS_XZ: {
        "name": "XZ",
        "category": "compress",
        "capabilities": Capability.COMPRESS,
    },
    Operation.COMPRESS_ZSTD: {
        "name": "ZSTD",
        "category": "compress",
        "capabilities": Capability.COMPRESS | Capability.STREAM,
    },
    Operation.COMPRESS_LZ4: {
        "name": "LZ4",
        "category": "compress",
        "capabilities": Capability.COMPRESS | Capability.STREAM,
    },
    
    # Encryptors
    Operation.ENCRYPT_AES256: {
        "name": "AES256",
        "category": "encrypt",
        "capabilities": Capability.ENCRYPT,
    },
    Operation.ENCRYPT_CHACHA20: {
        "name": "CHACHA20",
        "category": "encrypt",
        "capabilities": Capability.ENCRYPT | Capability.STREAM,
    },
    
    # Encoders
    Operation.ENCODE_BASE64: {
        "name": "BASE64",
        "category": "encode",
        "capabilities": Capability.NONE,
    },
    Operation.ENCODE_HEX: {
        "name": "HEX",
        "category": "encode",
        "capabilities": Capability.NONE,
    },
    
    # ZIP variants
    Operation.ZIP_STORE: {
        "name": "ZIP_STORE",
        "category": "compound",
        "capabilities": Capability.BUNDLE,
    },
    Operation.ZIP_DEFLATE: {
        "name": "ZIP_DEFLATE",
        "category": "compound",
        "capabilities": Capability.BUNDLE | Capability.COMPRESS,
    },
    Operation.ZIP_ENCRYPTED: {
        "name": "ZIP_ENCRYPTED",
        "category": "compound",
        "capabilities": Capability.BUNDLE | Capability.ENCRYPT,
    },
}


def pack_operations(operations: list[int]) -> int:
    """
    Pack a list of operations into a single 64-bit integer.
    
    Operations are processed from index 0 to N.
    Maximum 8 operations can be packed.
    
    Args:
        operations: List of operation values
        
    Returns:
        Packed integer representation
        
    Example:
        [TAR, GZIP, AES] -> 0x0000000000302011
    """
    if len(operations) > 8:
        raise ValueError(f"Maximum 8 operations supported, got {len(operations)}")
    
    packed = 0
    for i, op in enumerate(operations):
        if op < 0 or op > 0xFF:
            raise ValueError(f"Operation {op} out of range (0-255)")
        packed |= (op & 0xFF) << (i * 8)
    
    return packed


def unpack_operations(packed: int) -> list[int]:
    """
    Unpack operations from a 64-bit integer.
    
    Args:
        packed: Packed integer representation
        
    Returns:
        List of operation values in processing order
        
    Example:
        0x0000000000302011 -> [0x11, 0x20, 0x30] = [GZIP, AES256, ...]
    """
    operations = []
    temp = packed
    
    for _ in range(8):
        op = temp & 0xFF
        if op != 0:  # Skip NONE operations
            operations.append(op)
        temp >>= 8
        if temp == 0:
            break
    
    return operations


def get_operation_name(op: int) -> str:
    """Get human-readable name for an operation."""
    try:
        op_enum = Operation(op)
        info = OPERATION_INFO.get(op_enum, {})
        return info.get("name", f"UNKNOWN_{op:02X}")
    except ValueError:
        return f"CUSTOM_{op:02X}"


def get_operation_capabilities(op: int) -> int:
    """Get capability flags for an operation."""
    try:
        op_enum = Operation(op)
        info = OPERATION_INFO.get(op_enum, {})
        return info.get("capabilities", Capability.NONE)
    except ValueError:
        return Capability.NONE


def get_operation_category(op: int) -> str:
    """Get category for an operation."""
    try:
        op_enum = Operation(op)
        info = OPERATION_INFO.get(op_enum, {})
        return info.get("category", "unknown")
    except ValueError:
        return "custom" if op >= 0x80 else "unknown"


def validate_operation_chain(operations: list[int]) -> tuple[bool, str]:
    """
    Validate an operation chain for common issues.
    
    Returns:
        (is_valid, error_message)
    """
    if not operations:
        return True, ""
    
    if len(operations) > 8:
        return False, "Chain exceeds 8 operations"
    
    # Check for duplicate operations
    seen = set()
    for op in operations:
        if op in seen:
            name = get_operation_name(op)
            return False, f"Duplicate operation: {name}"
        seen.add(op)
    
    # Check for invalid sequences
    categories = [get_operation_category(op) for op in operations]
    
    # Multiple bundlers usually doesn't make sense
    bundle_count = categories.count("bundle")
    if bundle_count > 2:
        return False, f"Too many bundle operations ({bundle_count})"
    
    # Multiple encryptions might be intentional but warn
    encrypt_count = categories.count("encrypt")
    if encrypt_count > 2:
        return False, f"Too many encryption operations ({encrypt_count})"
    
    return True, ""


def format_operation_chain(operations: list[int]) -> str:
    """
    Format operation chain for display.
    
    Example:
        [0x01, 0x11, 0x30] -> "TAR -> GZIP -> AES256"
    """
    if not operations:
        return "NONE"
    
    names = [get_operation_name(op) for op in operations]
    return " -> ".join(names)


def parse_operation_string(chain_str: str) -> list[int]:
    """
    Parse operation chain from string representation.
    
    Example:
        "TAR -> GZIP -> AES256" -> [0x01, 0x11, 0x30]
    """
    if not chain_str or chain_str == "NONE":
        return []
    
    parts = [p.strip() for p in chain_str.split("->")]
    operations = []
    
    for part in parts:
        # Try to find matching operation
        found = False
        for op_enum in Operation:
            info = OPERATION_INFO.get(op_enum, {})
            if info.get("name") == part.upper():
                operations.append(op_enum.value)
                found = True
                break
        
        if not found:
            # Try parsing as hex
            if part.startswith("0x") or part.startswith("0X"):
                try:
                    op_val = int(part, 16)
                    operations.append(op_val)
                except ValueError:
                    raise ValueError(f"Unknown operation: {part}")
            else:
                raise ValueError(f"Unknown operation: {part}")
    
    return operations