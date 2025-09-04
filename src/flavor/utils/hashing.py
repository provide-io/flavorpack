"""Hashing utilities for Flavor - thin wrapper around foundation.

For new code, prefer importing directly from provide.foundation.crypto.
"""

from pathlib import Path

from provide.foundation.crypto import (
    hash_file as _hash_file,
    hash_data as _hash_data,
    quick_hash as _quick_hash,
)


def hash_name(name: str) -> int:
    """Generate a 64-bit hash of a string for fast lookup.
    
    Args:
        name: String to hash
        
    Returns:
        64-bit integer hash
    """
    from provide.foundation.crypto.utils import hash_name as _hash_name
    return _hash_name(name)


def hash_file(path: Path, algorithm: str = "sha256") -> str:
    """Hash a file's contents.
    
    Args:
        path: File path
        algorithm: Hash algorithm (sha256, sha512, md5, etc.)
        
    Returns:
        Hex digest of file hash
    """
    return _hash_file(path, algorithm)


def hash_data(data: bytes, algorithm: str = "sha256") -> str:
    """Hash binary data.
    
    Args:
        data: Data to hash
        algorithm: Hash algorithm
        
    Returns:
        Hex digest
    """
    return _hash_data(data, algorithm)


def verify_hash(data: bytes, expected_hash: str, algorithm: str = "sha256") -> bool:
    """Verify data matches expected hash.
    
    Args:
        data: Data to verify
        expected_hash: Expected hash value
        algorithm: Hash algorithm
        
    Returns:
        True if hash matches
    """
    from provide.foundation.crypto import verify_data
    return verify_data(data, expected_hash, algorithm)


def quick_hash(data: bytes) -> int:
    """Generate a quick non-cryptographic hash for lookups.
    
    Args:
        data: Data to hash
        
    Returns:
        32-bit hash value
    """
    return _quick_hash(data)