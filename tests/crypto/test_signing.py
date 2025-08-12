"""Tests for the signing module."""

from cryptography.hazmat.primitives.asymmetric import ec
import pytest

from flavor.crypto import sign_payload_hash
from flavor.exceptions import SigningError


def test_sign_payload_hash_invalid_input(
    private_key: ec.EllipticCurvePrivateKey,
) -> None:
    """Tests that sign_payload_hash raises SigningError for invalid hash."""
    with pytest.raises(
        SigningError, match="Payload hash must be a 32-byte SHA-256 hash."
    ):
        sign_payload_hash(b"not a 32-byte hash", private_key)


# 📦🍜🧪🪄
