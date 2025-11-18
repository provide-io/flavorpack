#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Key management for FlavorPack package signing."""

from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from provide.foundation.file import atomic_write
from provide.foundation.file.directory import ensure_dir

from flavor.config.defaults import DEFAULT_FILE_PERMS


def generate_key_pair(keys_dir: Path) -> tuple[Path, Path]:
    """Generates a new Ed25519 key pair and saves them to PEM files.

    This function is used for CLI operations where keys need to be persisted
    to files for later use. For internal package building where keys are
    used immediately and discarded, use flavor.psp.format_2025.crypto.generate_key_pair()
    which returns raw bytes instead.

    Ed25519 is used for all PSPF packages as specified in the PSPF/2025 format.
    This provides:
    - Small keys (32 bytes public, 32 bytes private seed)
    - Fast signing and verification
    - Deterministic signatures
    - Strong security with no parameters to misconfigure

    Args:
        keys_dir: Directory to save the key files

    Returns:
        tuple: (private_key_path, public_key_path)

    See Also:
        flavor.psp.format_2025.crypto.generate_key_pair: For in-memory key generation
    """
    # Generate Ed25519 key pair
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    # Serialize to PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # Save to files with secure permissions
    private_key_path = keys_dir / "flavor-private.key"
    public_key_path = keys_dir / "flavor-public.key"

    ensure_dir(keys_dir, mode=0o700)

    # Write private key with restricted permissions (atomic for safety)
    atomic_write(private_key_path, private_pem)
    private_key_path.chmod(DEFAULT_FILE_PERMS)

    # Write public key (atomic for safety)
    atomic_write(public_key_path, public_pem)
    public_key_path.chmod(DEFAULT_FILE_PERMS)  # Use same security level

    return private_key_path, public_key_path


def load_private_key_raw(key_path: Path) -> bytes:
    """Load a private key from PEM file and return raw 32-byte seed.

    Args:
        key_path: Path to PEM-encoded private key file

    Returns:
        bytes: Raw 32-byte private key seed for Ed25519
    """
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    pem_data = key_path.read_bytes()
    try:
        private_key = serialization.load_pem_private_key(pem_data, password=None, backend=default_backend())
    except Exception as e:
        raise ValueError(
            f"Failed to load private key from {key_path}: {e}\n"
            f"Ensure the key is in PEM format and is a valid Ed25519 key."
        ) from e

    # For Ed25519, we need to extract the raw private key bytes differently
    # The cryptography library stores Ed25519 private keys as 32-byte seeds
    if isinstance(private_key, ed25519.Ed25519PrivateKey):
        # Get the private key bytes in PKCS8 format and extract the seed
        pkcs8_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        # The Ed25519 seed is the last 32 bytes of the PKCS8 structure
        # PKCS8 format for Ed25519: version + algorithm OID + private key octets
        # The actual seed starts at byte 16 (after headers)
        return pkcs8_bytes[-32:]
    else:
        # Provide helpful error message for incompatible key types
        from cryptography.hazmat.primitives.asymmetric import dsa, ec, rsa

        key_type_name = "unknown"
        if isinstance(private_key, ec.EllipticCurvePrivateKey):
            key_type_name = "EC (Elliptic Curve)"
        elif isinstance(private_key, rsa.RSAPrivateKey):
            key_type_name = "RSA"
        elif isinstance(private_key, dsa.DSAPrivateKey):
            key_type_name = "DSA"
        else:
            key_type_name = type(private_key).__name__

        raise ValueError(
            f"Incompatible key type at {key_path}: Found {key_type_name} key, but Ed25519 is required.\n"
            f"PSPF packages require Ed25519 keys for signing.\n"
            f"To generate new Ed25519 keys, delete the existing keys and run:\n"
            f"  flavor keygen --output keys/"
        )


def load_public_key_raw(key_path: Path) -> bytes:
    """Load a public key from PEM file and return raw 32-byte key.

    Args:
        key_path: Path to PEM-encoded public key file

    Returns:
        bytes: Raw 32-byte public key for Ed25519
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import dsa, ec, ed25519, rsa

    pem_data = key_path.read_bytes()
    try:
        public_key = serialization.load_pem_public_key(pem_data)
    except Exception as e:
        raise ValueError(
            f"Failed to load public key from {key_path}: {e}\n"
            f"Ensure the key is in PEM format and is a valid Ed25519 key."
        ) from e

    # Check if it's Ed25519
    if isinstance(public_key, ed25519.Ed25519PublicKey):
        # Extract the raw 32-byte public key
        raw_public = public_key.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        return raw_public
    else:
        # Provide helpful error message for incompatible key types
        key_type_name = "unknown"
        if isinstance(public_key, ec.EllipticCurvePublicKey):
            key_type_name = "EC (Elliptic Curve)"
        elif isinstance(public_key, rsa.RSAPublicKey):
            key_type_name = "RSA"
        elif isinstance(public_key, dsa.DSAPublicKey):
            key_type_name = "DSA"
        else:
            key_type_name = type(public_key).__name__

        raise ValueError(
            f"Incompatible key type at {key_path}: Found {key_type_name} key, but Ed25519 is required.\n"
            f"PSPF packages require Ed25519 keys for signing.\n"
            f"To generate new Ed25519 keys, delete the existing keys and run:\n"
            f"  flavor keygen --output keys/"
        )


# 🌶️📦🔚
