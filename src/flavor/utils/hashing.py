"""Hashing and checksum utilities."""

import hashlib
from pathlib import Path


def hash_name(name: str) -> int:
    """Generate a 64-bit hash of a string for fast lookup.
    
    Args:
        name: String to hash
        
    Returns:
        64-bit integer hash
    """
    # Use first 8 bytes of SHA256 for good distribution
    hash_bytes = hashlib.sha256(name.encode("utf-8")).digest()[:8]
    return int.from_bytes(hash_bytes, byteorder="little")


def hash_file(path: Path, algorithm: str = "sha256") -> str:
    """Hash a file's contents.
    
    Args:
        path: File path
        algorithm: Hash algorithm (sha256, sha512, md5, etc.)
        
    Returns:
        Hex digest of file hash
    """
    hasher = hashlib.new(algorithm)
    
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    
    return hasher.hexdigest()


def hash_data(data: bytes, algorithm: str = "sha256") -> str:
    """Hash binary data.
    
    Args:
        data: Data to hash
        algorithm: Hash algorithm
        
    Returns:
        Hex digest
    """
    hasher = hashlib.new(algorithm)
    hasher.update(data)
    return hasher.hexdigest()


def verify_hash(data: bytes, expected_hash: str, algorithm: str = "sha256") -> bool:
    """Verify data matches expected hash.
    
    Args:
        data: Data to verify
        expected_hash: Expected hash value
        algorithm: Hash algorithm
        
    Returns:
        True if hash matches
    """
    actual_hash = hash_data(data, algorithm)
    return actual_hash.lower() == expected_hash.lower()


def quick_hash(data: bytes) -> int:
    """Generate a quick non-cryptographic hash for lookups.
    
    Args:
        data: Data to hash
        
    Returns:
        32-bit hash value
    """
    # Use Python's built-in hash for speed
    return hash(data) & 0xFFFFFFFF