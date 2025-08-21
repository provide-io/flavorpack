#!/usr/bin/env python3
"""
Checksum utilities for PSPF packages.

Supports multiple checksum algorithms with a prefixed format for extensibility.
Format: "algorithm:hexvalue" (e.g., "sha256:abc123...", "adler32:deadbeef")
"""

import hashlib
import zlib

from flavor.exceptions import ValidationError

# Supported checksum algorithms
SUPPORTED_ALGORITHMS = ["sha256", "sha512", "blake2b", "blake2s", "adler32", "md5"]


def calculate_checksum(data: bytes, algorithm: str = "sha256") -> str:
    """
    Calculate checksum with algorithm prefix.

    Args:
        data: The data to checksum
        algorithm: The checksum algorithm to use

    Returns:
        Prefixed checksum string (e.g., "sha256:abc123...")

    Raises:
        ValueError: If algorithm is not supported
    """
    if algorithm == "sha256":
        digest = hashlib.sha256(data).hexdigest()
        return f"sha256:{digest}"
    elif algorithm == "sha512":
        digest = hashlib.sha512(data).hexdigest()
        return f"sha512:{digest}"
    elif algorithm == "blake2b":
        digest = hashlib.blake2b(data).hexdigest()
        return f"blake2b:{digest}"
    elif algorithm == "blake2s":
        digest = hashlib.blake2s(data).hexdigest()
        return f"blake2s:{digest}"
    elif algorithm == "md5":
        # MD5 for compatibility, not recommended for security
        digest = hashlib.md5(data, usedforsecurity=False).hexdigest()
        return f"md5:{digest}"
    elif algorithm == "adler32":
        # Adler32 returns an integer, format as 8-char hex
        checksum = zlib.adler32(data)
        return f"adler32:{checksum:08x}"
    else:
        raise ValueError(f"Unsupported checksum algorithm: {algorithm}")


def verify_checksum(data: bytes, checksum_str: str) -> bool:
    """
    Verify data against a prefixed checksum string.

    Args:
        data: The data to verify
        checksum_str: The expected checksum (with or without prefix)

    Returns:
        True if checksum matches, False otherwise
    """
    try:
        algo, _ = parse_checksum(checksum_str)
        actual = calculate_checksum(data, algo)
        return actual == normalize_checksum(checksum_str)
    except (ValueError, ValidationError):
        return False


def parse_checksum(checksum_str: str) -> tuple[str, str]:
    """
    Parse algorithm and value from a checksum string.

    Handles both prefixed ("sha256:abc123") and legacy (unprefixed) formats.
    Legacy format assumes SHA-256 for backward compatibility.

    Args:
        checksum_str: The checksum string to parse

    Returns:
        Tuple of (algorithm, hex_value)

    Raises:
        ValidationError: If checksum format is invalid
    """
    if not checksum_str:
        raise ValidationError("Empty checksum string")

    if ":" in checksum_str:
        # Prefixed format
        parts = checksum_str.split(":", 1)
        if len(parts) != 2:
            raise ValidationError(f"Invalid checksum format: {checksum_str}")

        algo, value = parts
        if algo not in SUPPORTED_ALGORITHMS:
            raise ValidationError(f"Unknown checksum algorithm: {algo}")

        return algo, value
    else:
        # Legacy format - assume SHA-256
        # Check if it looks like a hex string
        try:
            int(checksum_str, 16)
        except ValueError as e:
            raise ValidationError(f"Invalid hex checksum: {checksum_str}") from e

        # Guess algorithm based on length
        if len(checksum_str) == 64:
            return "sha256", checksum_str
        elif len(checksum_str) == 128:
            return "sha512", checksum_str
        elif len(checksum_str) == 8:
            return "adler32", checksum_str
        elif len(checksum_str) == 32:
            return "md5", checksum_str
        else:
            # Default to SHA-256 for unknown lengths
            return "sha256", checksum_str


def normalize_checksum(checksum_str: str) -> str:
    """
    Normalize a checksum string to prefixed format.

    Args:
        checksum_str: The checksum string (with or without prefix)

    Returns:
        Normalized checksum with prefix
    """
    algo, value = parse_checksum(checksum_str)
    return f"{algo}:{value}"


def get_checksum_algorithm(checksum_str: str) -> str:
    """
    Get the algorithm from a checksum string.

    Args:
        checksum_str: The checksum string

    Returns:
        The algorithm name
    """
    algo, _ = parse_checksum(checksum_str)
    return algo


def is_strong_checksum(checksum_str: str) -> bool:
    """
    Check if a checksum uses a cryptographically strong algorithm.

    Args:
        checksum_str: The checksum string

    Returns:
        True if using a strong algorithm (sha256, sha512, blake2b, blake2s)
    """
    algo = get_checksum_algorithm(checksum_str)
    return algo in ["sha256", "sha512", "blake2b", "blake2s"]
