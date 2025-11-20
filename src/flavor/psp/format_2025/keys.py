#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PSPF key management utilities for handling cryptographic keys."""

import hashlib
from pathlib import Path

from provide.foundation import logger
from provide.foundation.crypto import generate_ed25519_keypair
from provide.foundation.file import atomic_write
from provide.foundation.file.directory import ensure_dir

from flavor.config.defaults import DEFAULT_FILE_PERMS
from flavor.psp.format_2025.spec import KeyConfig


def resolve_keys(config: KeyConfig) -> tuple[bytes, bytes]:
    """
    Resolve keys based on configuration priority.

    Priority order:
    1. Explicit keys (if both provided)
    2. Deterministic from seed
    3. Load from filesystem path
    4. Generate ephemeral (default)

    Args:
        config: Key configuration specifying key source

    Returns:
        Tuple of (private_key, public_key) as bytes
    """
    # Priority 1: Explicit keys
    if config.has_explicit_keys():
        logger.info("🔑 Using explicitly provided keys")
        # Type assertion: we know both are not None due to has_explicit_keys() check
        assert config.private_key is not None and config.public_key is not None
        return config.private_key, config.public_key

    # Priority 2: Deterministic from seed
    if config.has_seed():
        logger.info("🌱 Generating deterministic keys from seed")
        # Type assertion: we know key_seed is not None due to has_seed() check
        assert config.key_seed is not None
        return generate_deterministic_keys(config.key_seed)

    # Priority 3: Load from path
    if config.has_path():
        # Type assertion: we know key_path is not None due to has_path() check
        assert config.key_path is not None
        return load_keys_from_path(config.key_path)

    # Priority 4: Generate ephemeral
    logger.info("✨ Generating ephemeral keys")
    return generate_ephemeral_keys()


def generate_deterministic_keys(seed: str) -> tuple[bytes, bytes]:
    """
    Generate deterministic Ed25519 keys from a seed string.

    Uses SHA256 to derive a 32-byte seed from the input string,
    ensuring reproducible key generation.

    Args:
        seed: Seed string for deterministic generation

    Returns:
        Tuple of (private_key, public_key) as bytes
    """
    # Derive 32-byte seed from string using SHA256
    seed_bytes = hashlib.sha256(seed.encode("utf-8")).digest()

    # Use the seed to generate keys deterministically
    # We'll use the seed as the private key directly for Ed25519
    # This is safe because Ed25519 private keys are just 32 random bytes
    private_key = seed_bytes

    # Generate public key from private key
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    # Create Ed25519 key object from private bytes
    # Ed25519PrivateKey.from_private_bytes expects the raw 32-byte seed
    key = Ed25519PrivateKey.from_private_bytes(private_key)

    # Get public key bytes
    public_key = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )

    logger.debug(
        f"🌱 Generated deterministic keys (public key hash: {hashlib.sha256(public_key).hexdigest()[:8]})"
    )

    return private_key, public_key


def generate_ephemeral_keys() -> tuple[bytes, bytes]:
    """
    Generate new ephemeral Ed25519 keys.

    Creates a new random key pair that will be discarded after use.

    Returns:
        Tuple of (private_key, public_key) as bytes
    """
    private_key, public_key = generate_ed25519_keypair()

    logger.debug(
        f"✨ Generated ephemeral keys (public key hash: {hashlib.sha256(public_key).hexdigest()[:8]})"
    )

    return private_key, public_key


def load_keys_from_path(key_path: Path) -> tuple[bytes, bytes]:
    """
    Load Ed25519 keys from filesystem.

    Expects to find:
    - flavor-private.key: Raw 32-byte private key
    - flavor-public.key: Raw 32-byte public key

    Args:
        key_path: Directory containing key files

    Returns:
        Tuple of (private_key, public_key) as bytes

    Raises:
        FileNotFoundError: If key files don't exist
        ValueError: If key files are invalid
    """
    private_key_path = key_path / "flavor-private.key"
    public_key_path = key_path / "flavor-public.key"

    if not private_key_path.exists():
        raise FileNotFoundError(f"🔑 Private key not found: {private_key_path}")
    if not public_key_path.exists():
        raise FileNotFoundError(f"🔑 Public key not found: {public_key_path}")

    private_key = private_key_path.read_bytes()
    public_key = public_key_path.read_bytes()

    # Validate key sizes
    if len(private_key) != 32:
        raise ValueError(f"🔑 Invalid private key size: expected 32 bytes, got {len(private_key)}")
    if len(public_key) != 32:
        raise ValueError(f"🔑 Invalid public key size: expected 32 bytes, got {len(public_key)}")

    logger.debug(
        "🔑 Keys loaded successfully",
        private_key_size=len(private_key),
        public_key_size=len(public_key),
        path=str(key_path),
    )

    return private_key, public_key


def save_keys_to_path(private_key: bytes, public_key: bytes, key_path: Path) -> None:
    """
    Save Ed25519 keys to filesystem.

    Saves raw key bytes to:
    - flavor-private.key: Raw 32-byte private key
    - flavor-public.key: Raw 32-byte public key

    Args:
        private_key: 32-byte private key
        public_key: 32-byte public key
        key_path: Directory to save keys in
    """
    # Ensure directory exists
    ensure_dir(key_path)

    private_key_path = key_path / "flavor-private.key"
    public_key_path = key_path / "flavor-public.key"

    # Save keys atomically for safety
    atomic_write(private_key_path, private_key)
    atomic_write(public_key_path, public_key)

    # Set restrictive permissions on private key
    private_key_path.chmod(DEFAULT_FILE_PERMS)

    logger.info(f"💾 Saved keys to {key_path}")
    logger.debug(f"   Public key hash: {hashlib.sha256(public_key).hexdigest()[:8]}")


def create_key_config(
    seed: str | None = None,
    private_key: bytes | None = None,
    public_key: bytes | None = None,
    key_path: Path | None = None,
) -> KeyConfig:
    """
    Helper function to create a KeyConfig with validation.

    Ensures that key configuration is consistent and valid.

    Args:
        seed: Seed for deterministic generation
        private_key: Explicit private key bytes
        public_key: Explicit public key bytes
        key_path: Path to load keys from

    Returns:
        Validated KeyConfig instance

    Raises:
        ValueError: If configuration is invalid
    """
    # Check that explicit keys are both provided or both absent
    if (private_key is None) != (public_key is None):
        raise ValueError("🔑 Both private and public keys must be provided together")

    # Check that only one key source is specified
    sources = sum([private_key is not None, seed is not None, key_path is not None])

    if sources > 1:
        raise ValueError("🔑 Only one key source can be specified (explicit, seed, or path)")

    return KeyConfig(private_key=private_key, public_key=public_key, key_seed=seed, key_path=key_path)


# 🌶️📦🔚
