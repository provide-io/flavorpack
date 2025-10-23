"""
Shared fixtures for PSPF 2025 format tests.
"""

import hashlib
import os

import pytest

from flavor.psp.format_2025 import SlotMetadata


@pytest.fixture
def test_slots(temp_dir, test_builder):
    """Create test slots with different properties."""
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
            operations="none",  # Binary files often don't compress well
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
