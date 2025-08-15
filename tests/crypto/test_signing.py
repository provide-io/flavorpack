"""Tests for the signing module."""

from cryptography.hazmat.primitives.asymmetric import ed25519
import pytest

from flavor.crypto import sign_payload_hash
from flavor.exceptions import SigningError


def test_sign_payload_hash_invalid_input(
    key_pair: tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey],
) -> None:
    """Tests that sign_payload_hash raises SigningError for invalid hash."""
    private_key, _ = key_pair
    with pytest.raises(
        SigningError, match="Payload hash must be a 32-byte SHA-256 hash."
    ):
        sign_payload_hash(b"not a 32-byte hash", private_key)


# 📦🍜🧪🪄
