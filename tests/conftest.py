from cryptography.hazmat.primitives.asymmetric import ed25519
import pytest


@pytest.fixture(scope="session")
def key_pair() -> tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    """Fixture to generate a reusable Ed25519 key pair for the test session."""
    # Generate Ed25519 key pair to match the actual implementation
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key