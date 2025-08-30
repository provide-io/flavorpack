from cryptography.hazmat.primitives.asymmetric import ed25519
import pytest
import tempfile
import shutil
from pathlib import Path
from flavor.psp.format_2025.builder import PSPFBuilder

# Mock launcher data - matches approximate size of real launchers
# This should be validated against real launchers in integration tests
MOCK_LAUNCHER_SIZE = 124  # Simplified for unit tests
MOCK_LAUNCHER_DATA = b"FAKE_LAUNCHER_FOR_TEST" + b"\x00" * (MOCK_LAUNCHER_SIZE - 22)


@pytest.fixture(scope="session")
def key_pair() -> tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    """Fixture to generate a reusable Ed25519 key pair for the test session."""
    # Generate Ed25519 key pair to match the actual implementation
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


@pytest.fixture(autouse=True)
def mock_launcher_loading(monkeypatch):
    """Automatically mock launcher loading for all tests.

    This fixture is applied to ALL tests automatically. Tests that need
    real launchers should be marked with @pytest.mark.integration and
    explicitly disable this fixture.
    """

    def mock_load_launcher(launcher_type):
        return MOCK_LAUNCHER_DATA

    from flavor.psp.format_2025.metadata import assembly

    monkeypatch.setattr(assembly, "load_launcher_binary", mock_load_launcher)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests.

    This fixture provides a clean temporary directory that is automatically
    cleaned up after the test completes.
    """
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def test_builder():
    """Fixture to create a PSPFBuilder in test mode for reproducible tests.

    This builder uses mocked launchers (via mock_launcher_loading) and
    deterministic keys for reproducible test results.
    """
    # New API uses a fluent interface and explicit seeding for reproducibility
    return PSPFBuilder.create().with_keys(seed="pytest_reproducible_seed")
