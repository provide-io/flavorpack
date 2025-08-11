#
# flavor/crypto.py
#
"""
Centralized cryptographic operations for the Pyvider builder.
"""

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils

from .exceptions import SigningError


def generate_keys() -> tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
    """Generates a new P-256 ECDSA key pair."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    return private_key, private_key.public_key()


def sign_payload_hash(
    payload_hash: bytes, private_key: ec.EllipticCurvePrivateKey
) -> bytes:
    """Signs a 32-byte hash using ECDSA."""
    if not isinstance(payload_hash, bytes) or len(payload_hash) != 32:
        raise SigningError("Payload hash must be a 32-byte SHA-256 hash.")

    return private_key.sign(
        payload_hash,
        # The data is already hashed, so we use Prehashed.
        ec.ECDSA(utils.Prehashed(hashes.SHA256())),
    )


# 🔒 🔐 🗝️


# 📦🍜📄🪄
