#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Shared pytest fixtures and helpers for FlavorPack tests."""

from __future__ import annotations

from collections.abc import Iterator
import os
from pathlib import Path
import shutil
import tempfile
from typing import TYPE_CHECKING

from cryptography.hazmat.primitives.asymmetric import ed25519
import provide.testkit  # noqa: F401 - Installs setproctitle blocker early
from provide.testkit.logger import reset_foundation_setup_for_testing
import pytest

from flavor.psp.format_2025.pspf_builder import PSPFBuilder

if TYPE_CHECKING:
    from flavor.psp.format_2025 import SlotMetadata

# Mock launcher data - matches approximate size of real launchers
# This should be validated against real launchers in integration tests
MOCK_LAUNCHER_SIZE = 124  # Simplified for unit tests
MOCK_LAUNCHER_DATA = b"FAKE_LAUNCHER_FOR_TEST" + b"\x00" * (MOCK_LAUNCHER_SIZE - 22)


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "requires_helpers: mark test as requiring real launcher binaries (auto-skipped if not available)",
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (may require real binaries)"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-skip tests marked requires_helpers if binaries not found."""
    # Check if launcher binaries are available
    binary_paths = [
        Path("dist/bin/flavor-rs-launcher-darwin_arm64"),
        Path("dist/bin/flavor-rs-launcher"),
        Path("helpers/bin/flavor-rs-launcher"),
        Path("helpers/bin/flavor-rs-launcher"),
        Path.cwd() / "dist" / "bin" / "flavor-rs-launcher-darwin_arm64",
        Path.cwd() / "dist" / "bin" / "flavor-rs-launcher",
    ]

    # Check environment variable
    env_launcher = os.environ.get("FLAVOR_LAUNCHER_BIN")
    if env_launcher:
        binary_paths.insert(0, Path(env_launcher))

    binaries_available = any(p.exists() for p in binary_paths)

    if not binaries_available:
        skip_helpers = pytest.mark.skip(
            reason=(
                "Launcher binaries not found. "
                "Run 'make build-helpers' or set FLAVOR_LAUNCHER_BIN environment variable. "
                f"Searched: {', '.join(str(p) for p in binary_paths[:3])}..."
            )
        )
        skipped_count = 0
        for item in items:
            # Skip tests marked with requires_helpers
            if "requires_helpers" in item.keywords or (
                "integration" in item.keywords and "requires_helpers" not in item.keywords
            ):
                item.add_marker(skip_helpers)
                skipped_count += 1

        if skipped_count > 0:
            print(f"\n⚠️  Skipping {skipped_count} integration tests (launcher binaries not found)")
            print("   Run 'make build-helpers' to enable integration tests")


@pytest.fixture(scope="session")
def key_pair() -> tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    """Fixture to generate a reusable Ed25519 key pair for the test session."""
    # Generate Ed25519 key pair to match the actual implementation
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


@pytest.fixture(autouse=True)
def reset_foundation_logging() -> Iterator[None]:
    """Reset foundation logging state before each test to avoid conflicts."""
    reset_foundation_setup_for_testing()
    yield
    # Reset again after test to ensure clean state
    reset_foundation_setup_for_testing()


@pytest.fixture(autouse=True)
def mock_launcher_loading(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Automatically mock launcher loading for non-integration tests.

    Tests marked with @pytest.mark.integration will skip this mock
    and require real launcher binaries.
    """
    # Skip mocking for integration tests
    if request.node.get_closest_marker("integration"):
        return  # Let integration tests use real binaries

    def mock_load_launcher(launcher_type: str) -> bytes:
        return MOCK_LAUNCHER_DATA

    # Patch where the function is used, not just where it's defined
    monkeypatch.setattr("flavor.psp.format_2025.metadata.assembly.load_launcher_binary", mock_load_launcher)
    monkeypatch.setattr("flavor.psp.format_2025.writer.load_launcher_binary", mock_load_launcher)


@pytest.fixture
def temp_dir() -> Iterator[Path]:
    """Create a temporary directory for tests.

    This fixture provides a clean temporary directory that is automatically
    cleaned up after the test completes.
    """
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def test_builder() -> PSPFBuilder:
    """Fixture to create a PSPFBuilder in test mode for reproducible tests.

    This builder uses mocked launchers (via mock_launcher_loading) and
    deterministic keys for reproducible test results.
    """
    # New API uses a fluent interface and explicit seeding for reproducibility
    return PSPFBuilder.create().with_keys(seed="pytest_reproducible_seed")


@pytest.fixture
def mock_test_package(temp_dir: Path, test_builder: PSPFBuilder) -> Path:
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


@pytest.fixture
def test_slots(temp_dir: Path, test_builder: PSPFBuilder) -> list[SlotMetadata]:
    """Create test slots with different properties for PSPF tests."""
    import hashlib
    import os

    from flavor.psp.format_2025 import SlotMetadata

    slots = []

    # Text file (compressible)
    text_path = temp_dir / "text.json"
    text_data = '{"key": "value"}' * 100
    text_path.write_text(text_data)

    slots.append(
        SlotMetadata(
            index=0,
            id="config",
            source=str(text_path),
            target="config",
            size=len(text_data),
            checksum=hashlib.sha256(text_data.encode()).hexdigest(),
            operations="gzip",
            purpose="config",
            lifecycle="runtime",
        )
    )

    # Binary file (less compressible)
    binary_path = temp_dir / "binary.so"
    binary_data = os.urandom(1024)
    binary_path.write_bytes(binary_data)

    slots.append(
        SlotMetadata(
            index=1,
            id="library",
            source=str(binary_path),
            target="library",
            size=len(binary_data),
            checksum=hashlib.sha256(binary_data).hexdigest(),
            operations="none",
            purpose="library",
            lifecycle="init",
        )
    )

    # Temporary file
    temp_path = temp_dir / "temp.whl"
    temp_data = b"WHEEL_DATA" * 50
    temp_path.write_bytes(temp_data)

    slots.append(
        SlotMetadata(
            index=2,
            id="wheel",
            source=str(temp_path),
            target="wheel",
            size=len(temp_data),
            checksum=hashlib.sha256(temp_data).hexdigest(),
            operations="none",
            purpose="payload",
            lifecycle="temp",
        )
    )

    return slots


# 🌶️📦🔚
