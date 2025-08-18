#!/usr/bin/env python3
#
# flavor/packaging/keys.py
#
"""Key generation for PSPF packages using Ed25519."""

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


def generate_key_pair(keys_dir: Path) -> tuple[Path, Path]:
    """Generates a new Ed25519 key pair and saves them to the specified directory.
    
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

    keys_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    
    # Write private key with restricted permissions
    private_key_path.write_bytes(private_pem)
    private_key_path.chmod(0o600)
    
    # Write public key
    public_key_path.write_bytes(public_pem)
    public_key_path.chmod(0o644)  # Public key can be readable

    return private_key_path, public_key_path