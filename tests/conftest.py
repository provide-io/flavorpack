from pathlib import Path
import shutil
import tempfile

from cryptography.hazmat.primitives.asymmetric import ed25519
from provide.testkit.logger import reset_foundation_setup_for_testing
import pytest

from flavor.psp.format_2025.pspf_builder import PSPFBuilder

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
def reset_foundation_logging():
    """Reset foundation logging state before each test to avoid conflicts."""
    reset_foundation_setup_for_testing()
    yield
    # Reset again after test to ensure clean state
    reset_foundation_setup_for_testing()


@pytest.fixture(autouse=True)
def mock_launcher_loading(monkeypatch) -> None:
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


@pytest.fixture
def mock_test_package(temp_dir, test_builder):
    """Create a complete test PSPF package with multiple slots for testing.

    This fixture creates a test package with:
    - Mock launcher
    - Multiple slots with different encodings
    - Proper metadata for testing inspect/extract commands

    Returns:
        Path: Path to the created test package
    """
    import gzip
    import tarfile

    # Create test content for slots
    slot0_content = b"#!/usr/bin/env python3\nprint('Hello from slot 0')\n"
    slot1_content = b"Configuration data for slot 1\n"
    slot2_content = b"Some wheel content for testing\n" * 100  # Make it larger

    # Create slot files
    slot0_file = temp_dir / "main.py"
    slot0_file.write_bytes(slot0_content)

    slot1_file = temp_dir / "config.txt"
    slot1_file.write_bytes(slot1_content)

    # Create a gzipped slot
    slot1_gz = temp_dir / "config.gz"
    with gzip.open(slot1_gz, "wb") as f:
        f.write(slot1_content)

    # Create a tar archive for slot 2 (wheels)
    slot2_tar = temp_dir / "wheels.tar"
    with tarfile.open(slot2_tar, "w") as tar:
        # Add a fake wheel file
        wheel_file = temp_dir / "test_package-1.0.0-py3-none-any.whl"
        wheel_file.write_bytes(slot2_content)
        tar.add(wheel_file, arcname=wheel_file.name)

    # Build the package
    package_path = temp_dir / "test_package.psp"

    builder = test_builder.metadata(
        format="PSPF/2025",
        package={
            "name": "test-package",
            "version": "1.0.0",
            "description": "Test package for extract/inspect commands",
        },
        build={
            "builder": "pytest/mock-builder",
            "timestamp": "2025-01-01T00:00:00Z",
            "host": "test-host",
        },
        execution={
            "command": "/usr/bin/python3 {slot:0}",
            "primary_slot": 0,
            "environment": {"TEST_VAR": "test_value"},
        },
    )

    # Add slots with different encodings
    builder = builder.add_slot(
        id="main",
        data=slot0_file,
        purpose="payload",
        lifecycle="runtime",
        operations="none",
    )

    builder = builder.add_slot(
        id="config",
        data=slot1_gz,
        purpose="config",
        lifecycle="runtime",
        operations="gzip",
    )

    builder = builder.add_slot(
        id="wheels",
        data=slot2_tar,
        purpose="library",
        lifecycle="cache",
        operations="tar",
    )

    # Build the package
    builder.build(output_path=package_path)

    return package_path
