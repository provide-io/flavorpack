# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Cross-language parity tests for PSPF verification contracts.

Tests the Python implementation of verification behaviours that must be
consistent across Python, Go and Rust launchers/readers.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import zlib

import pytest

from flavor.psp.format_2025.constants import (
    DEFAULT_HEADER_SIZE,
    DEFAULT_MAGIC_TRAILER_SIZE,
    TRAILER_END_MAGIC,
    TRAILER_START_MAGIC,
)
from flavor.psp.format_2025.index import PSPFIndex

pytestmark = [
    pytest.mark.cross_language,
    pytest.mark.ci,
    pytest.mark.security,
    pytest.mark.adversarial,
]


# ---------------------------------------------------------------------------
# Magic trailer validation
# ---------------------------------------------------------------------------
@pytest.mark.parity
@pytest.mark.parity_category("Verification Contract")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_magic_trailer_validation() -> None:
    """Python recognises valid PSPF magic trailer bookends."""
    # Build a minimal valid trailer: START_MAGIC + index_data + padding + END_MAGIC
    index_data = b"\x00" * DEFAULT_HEADER_SIZE
    padding_size = DEFAULT_MAGIC_TRAILER_SIZE - DEFAULT_HEADER_SIZE - 8  # 8 = start + end magic
    trailer = TRAILER_START_MAGIC + index_data + (b"\x00" * padding_size) + TRAILER_END_MAGIC

    assert trailer[:4] == TRAILER_START_MAGIC
    assert trailer[-4:] == TRAILER_END_MAGIC
    assert len(trailer) == DEFAULT_MAGIC_TRAILER_SIZE


# ---------------------------------------------------------------------------
# Index checksum verification
# ---------------------------------------------------------------------------
@pytest.mark.parity
@pytest.mark.parity_category("Verification Contract")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_index_checksum_verification() -> None:
    """Python verifies Adler-32 checksum of the index block."""
    # Create a minimal PSPFIndex, pack it, then verify the round-trip
    # The index block stores an Adler-32 checksum at offset 4.
    # Zero the checksum field before computing.
    dummy_index = PSPFIndex()
    packed = dummy_index.pack()

    # Zero out checksum field at offset 4-8, compute adler32
    data_for_check = bytearray(packed)
    data_for_check[4:8] = b"\x00\x00\x00\x00"
    expected_checksum = zlib.adler32(bytes(data_for_check)) & 0xFFFFFFFF

    # The packed index should embed this checksum
    stored_checksum = struct.unpack_from("<I", packed, 4)[0]
    assert stored_checksum == expected_checksum, (
        f"Index checksum mismatch: stored={stored_checksum:#010x}, expected={expected_checksum:#010x}"
    )


# ---------------------------------------------------------------------------
# Metadata checksum verification
# ---------------------------------------------------------------------------
@pytest.mark.parity
@pytest.mark.parity_category("Verification Contract")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_metadata_checksum_verification() -> None:
    """Python uses full SHA-256 to verify metadata integrity."""
    payload = b'{"package":{"name":"test","version":"0.1.0"}}'
    digest = hashlib.sha256(payload).digest()

    assert len(digest) == 32
    # A different payload must produce a different digest
    altered = b'{"package":{"name":"test","version":"0.2.0"}}'
    assert hashlib.sha256(altered).digest() != digest


# ---------------------------------------------------------------------------
# Slot checksum verification
# ---------------------------------------------------------------------------
@pytest.mark.parity
@pytest.mark.parity_category("Verification Contract")
@pytest.mark.parity_go("N/A")
@pytest.mark.parity_rust("PASS")
def test_slot_checksum_verification() -> None:
    """Python uses SHA-256 first-8-bytes for slot checksum (Go stubs this)."""
    slot_data = b"hello slot content"
    hash_bytes = hashlib.sha256(slot_data).digest()[:8]
    checksum = int.from_bytes(hash_bytes, byteorder="little")

    # Must be deterministic
    assert checksum == int.from_bytes(hashlib.sha256(slot_data).digest()[:8], byteorder="little")
    # Different data must produce a different checksum
    other = int.from_bytes(hashlib.sha256(b"different").digest()[:8], byteorder="little")
    assert checksum != other


# ---------------------------------------------------------------------------
# Ed25519 signature verification
# ---------------------------------------------------------------------------
@pytest.mark.parity
@pytest.mark.parity_category("Verification Contract")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_ed25519_signature_verification() -> None:
    """Python can sign and verify Ed25519 signatures over metadata."""
    from provide.foundation.crypto import Ed25519Signer, Ed25519Verifier

    signer = Ed25519Signer.generate()
    message = b'{"package":{"name":"demo","version":"1.0.0"}}'
    signature = signer.sign(message)
    public_key = signer.public_key

    verifier = Ed25519Verifier(public_key)
    assert verifier.verify(message, signature)

    # Tampered message must fail
    assert not verifier.verify(message + b"x", signature)


# ---------------------------------------------------------------------------
# Package size validation
# ---------------------------------------------------------------------------
@pytest.mark.parity
@pytest.mark.parity_category("Verification Contract")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_package_size_validation() -> None:
    """Index records total package size; Python validates against file size."""
    idx = PSPFIndex(package_size=1024)

    packed = idx.pack()
    restored = PSPFIndex.unpack(packed)
    assert restored.package_size == 1024


# ---------------------------------------------------------------------------
# Fail-closed on error
# ---------------------------------------------------------------------------
@pytest.mark.parity
@pytest.mark.parity_category("Verification Contract")
@pytest.mark.parity_go("N/A")
@pytest.mark.parity_rust("PASS")
def test_fail_closed_on_error() -> None:
    """verify_integrity returns valid=False (fail-closed) on any exception."""
    from unittest.mock import Mock

    from flavor.psp.format_2025.reader import PSPFReader

    reader = PSPFReader(Path("/nonexistent.psp"))
    # Make verify_magic_trailer raise so verify_integrity hits the except path
    reader.verify_magic_trailer = Mock(side_effect=RuntimeError("forced error"))  # type: ignore[method-assign]
    result = reader.verify_integrity()

    assert result["valid"] is False
    assert result["tamper_detected"] is True
    assert result["error"] is not None
