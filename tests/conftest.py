import sys
from pathlib import Path
from typing import Callable

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from flavor.packaging.keys import generate_key_pair as generate_keys


@pytest.fixture(scope="session")
def key_pair() -> tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
    """Fixture to generate a reusable ECDSA key pair for the test session."""
    # This is a placeholder as the real keygen is in Go.
    # We generate a key here for Python-side signing tests.
    priv, pub = ec.generate_private_key(ec.SECP256R1()), None
    pub = priv.public_key()
    return priv, pub


@pytest.fixture(scope="session")
def private_key(key_pair: tuple) -> ec.EllipticCurvePrivateKey:
    """Fixture to provide the private key from the session key pair."""
    return key_pair[0]


@pytest.fixture(scope="session")
def public_key(key_pair: tuple) -> ec.EllipticCurvePublicKey:
    """Fixture to provide the public key from the session key pair."""
    return key_pair[1]


@pytest.fixture(scope="session")
def private_key_pem(private_key: ec.EllipticCurvePrivateKey) -> bytes:
    """Fixture to provide the private key as PEM bytes."""
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


@pytest.fixture(scope="session")
def public_key_pem(public_key: ec.EllipticCurvePublicKey) -> bytes:
    """Fixture to provide the public key as PEM bytes."""
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


# 📦🍜🧪🪄
