#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests: builder creates an attestation slot and binds its digest to the index."""

from __future__ import annotations

from collections.abc import Iterator
import contextlib
import gc
from pathlib import Path
import re
import tempfile

import pytest

from flavor.psp.format_2025.constants import LIFECYCLE_ATTESTATION
from flavor.psp.format_2025.pspf_builder import PSPFBuilder
from flavor.psp.format_2025.reader import PSPFReader

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_dir() -> Iterator[Path]:
    """Temporary directory for test files."""
    tmpdir_obj = tempfile.TemporaryDirectory()
    tmpdir = Path(tmpdir_obj.name)
    yield tmpdir
    gc.collect()
    with contextlib.suppress(PermissionError, OSError):
        tmpdir_obj.cleanup()


def _build_minimal_package(temp_dir: Path) -> Path:
    """Build the smallest valid package and return its path."""
    output = temp_dir / "attested.psp"
    result = (
        PSPFBuilder.create()
        .metadata(name="attestation-test", version="1.0.0")
        .add_slot(id="data", data=b"hello attestation")
        .with_keys(seed="test-attestation")
        .build(output)
    )
    assert result.success, f"Build failed: {result.errors}"
    return output


# ---------------------------------------------------------------------------
# Index-level assertions
# ---------------------------------------------------------------------------


class TestAttestationDigestInIndex:
    """attestation_sbom_digest is populated in the package index."""

    def test_digest_is_not_zero(self, temp_dir: Path) -> None:
        """Built package has a non-zero attestation_sbom_digest."""
        pkg = _build_minimal_package(temp_dir)
        reader = PSPFReader(pkg)
        index = reader.read_index()
        assert index.attestation_sbom_digest != b"\x00" * 64

    def test_digest_is_64_hex_chars(self, temp_dir: Path) -> None:
        """attestation_sbom_digest is exactly 64 ASCII hex chars."""
        pkg = _build_minimal_package(temp_dir)
        reader = PSPFReader(pkg)
        index = reader.read_index()
        raw = index.attestation_sbom_digest.rstrip(b"\x00")
        assert len(raw) == 64
        assert re.fullmatch(rb"[0-9a-f]{64}", raw), f"Not valid hex: {raw!r}"

    def test_digest_matches_sha256_of_slot_content(self, temp_dir: Path) -> None:
        """The index digest equals SHA-256 of the attestation slot bytes."""
        import hashlib
        import json

        pkg = _build_minimal_package(temp_dir)
        reader = PSPFReader(pkg)
        index = reader.read_index()
        stored_digest = index.attestation_sbom_digest.rstrip(b"\x00").decode("ascii")

        # Find the attestation slot index
        descriptors = reader.read_slot_descriptors()
        attestation_idx = next(
            (i for i, d in enumerate(descriptors) if d.lifecycle == LIFECYCLE_ATTESTATION),
            None,
        )
        assert attestation_idx is not None, "No attestation slot found in package"

        slot_bytes = reader.read_slot(attestation_idx)
        computed = hashlib.sha256(slot_bytes).hexdigest()
        assert computed == stored_digest

        # Also verify it is valid JSON with provenance
        parsed = json.loads(slot_bytes)
        assert "provenance" in parsed


# ---------------------------------------------------------------------------
# Slot-level assertions
# ---------------------------------------------------------------------------


class TestAttestationSlotPresent:
    """Package contains exactly one slot with lifecycle=LIFECYCLE_ATTESTATION."""

    def test_attestation_slot_exists(self, temp_dir: Path) -> None:
        """At least one slot has lifecycle == 11 (LIFECYCLE_ATTESTATION)."""
        pkg = _build_minimal_package(temp_dir)
        reader = PSPFReader(pkg)
        descriptors = reader.read_slot_descriptors()
        attestation_slots = [d for d in descriptors if d.lifecycle == LIFECYCLE_ATTESTATION]
        assert len(attestation_slots) == 1

    def test_attestation_slot_is_last(self, temp_dir: Path) -> None:
        """The attestation slot is the last slot in the table."""
        pkg = _build_minimal_package(temp_dir)
        reader = PSPFReader(pkg)
        descriptors = reader.read_slot_descriptors()
        assert descriptors[-1].lifecycle == LIFECYCLE_ATTESTATION

    def test_attestation_slot_count_correct(self, temp_dir: Path) -> None:
        """index.slot_count includes the attestation slot."""
        pkg = _build_minimal_package(temp_dir)
        reader = PSPFReader(pkg)
        index = reader.read_index()
        descriptors = reader.read_slot_descriptors()
        # 1 user slot + 1 attestation slot
        assert index.slot_count == 2
        assert len(descriptors) == 2


# ---------------------------------------------------------------------------
# Signing key fingerprint propagation
# ---------------------------------------------------------------------------


class TestAttestationKeyFp:
    """Key fingerprint is propagated into the attestation slot provenance."""

    def test_provenance_fingerprint_matches_index(self, temp_dir: Path) -> None:
        """Provenance signing_attestation_key_fp matches index.attestation_key_fp."""
        import json

        pkg = _build_minimal_package(temp_dir)
        reader = PSPFReader(pkg)
        index = reader.read_index()

        # Read index fingerprint
        raw_fp = index.attestation_key_fp.rstrip(b"\x00")
        index_fp = raw_fp.decode("ascii") if raw_fp != b"" else None

        # Read provenance from slot
        descriptors = reader.read_slot_descriptors()
        attestation_idx = next(i for i, d in enumerate(descriptors) if d.lifecycle == LIFECYCLE_ATTESTATION)
        slot_bytes = reader.read_slot(attestation_idx)
        parsed = json.loads(slot_bytes)
        prov_fp = parsed["provenance"]["signing_attestation_key_fp"]

        if index_fp:
            assert prov_fp == f"sha256:{index_fp}"
        else:
            assert prov_fp is None
