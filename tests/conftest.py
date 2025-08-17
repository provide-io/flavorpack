from cryptography.hazmat.primitives.asymmetric import ed25519
import pytest
from flavor.psp.format_2025.builder import PSPFBuilder


@pytest.fixture(scope="session")
def key_pair() -> tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    """Fixture to generate a reusable Ed25519 key pair for the test session."""
    # Generate Ed25519 key pair to match the actual implementation
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


@pytest.fixture
def test_builder():
    """Fixture to create a PSPFBuilder in test mode for reproducible tests."""
    # New API uses a fluent interface and explicit seeding for reproducibility
    return PSPFBuilder.create().with_keys(seed="pytest_reproducible_seed")