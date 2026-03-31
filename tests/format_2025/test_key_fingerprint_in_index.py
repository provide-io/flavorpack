#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests: key fingerprint is written into index.attestation_key_fp at build time."""

from __future__ import annotations

from collections.abc import Iterator
import hashlib
from pathlib import Path
import re
import tempfile

import pytest

from flavor.config.trust import compute_key_fingerprint
from flavor.psp.format_2025.builder import create_index
from flavor.psp.format_2025.keys import generate_deterministic_keys
from flavor.psp.format_2025.pspf_builder import PSPFBuilder
from flavor.psp.format_2025.spec import BuildSpec, KeyConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


def _make_public_key(seed: str = "test-fingerprint-seed") -> bytes:
    """Return deterministic 32-byte raw Ed25519 public key bytes."""
    _, pub = generate_deterministic_keys(seed)
    return pub


# ---------------------------------------------------------------------------
# Unit tests: create_index() directly
# ---------------------------------------------------------------------------


class TestCreateIndexFingerprint:
    """create_index() populates attestation_key_fp correctly."""

    def test_fingerprint_non_zero_for_real_key(self) -> None:
        """attestation_key_fp is not all-zeros when a real key is provided."""
        pub = _make_public_key()
        spec = BuildSpec(
            metadata={"package": {"name": "fp-test", "version": "0.1"}},
            keys=KeyConfig(key_seed="test-fingerprint-seed"),
        )
        index = create_index(spec, [], pub)

        assert index.attestation_key_fp != b"\x00" * 64

    def test_fingerprint_is_64_lowercase_hex_bytes(self) -> None:
        """attestation_key_fp encodes as 64 lowercase hex ASCII bytes."""
        pub = _make_public_key()
        spec = BuildSpec(
            metadata={"package": {"name": "fp-test", "version": "0.1"}},
        )
        index = create_index(spec, [], pub)

        fp_str = index.attestation_key_fp.decode("ascii")
        assert _HEX_RE.match(fp_str), f"Not 64 hex chars: {fp_str!r}"

    def test_fingerprint_matches_compute_key_fingerprint(self) -> None:
        """attestation_key_fp matches compute_key_fingerprint() of the same key."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        seed = "test-fingerprint-seed"
        _, pub_raw = generate_deterministic_keys(seed)

        # Reconstruct the Ed25519PublicKey object for compute_key_fingerprint
        priv_raw, _ = generate_deterministic_keys(seed)
        priv_obj = Ed25519PrivateKey.from_private_bytes(priv_raw)
        pub_obj = priv_obj.public_key()

        expected_fp = compute_key_fingerprint(pub_obj)

        spec = BuildSpec(metadata={"package": {"name": "fp-test", "version": "0.1"}})
        index = create_index(spec, [], pub_raw)

        assert index.attestation_key_fp.decode("ascii") == expected_fp

    def test_fingerprint_equals_sha256_of_raw_key(self) -> None:
        """attestation_key_fp is SHA-256 of the raw 32-byte key material."""
        pub = _make_public_key()
        expected = hashlib.sha256(pub).hexdigest().encode("ascii")

        spec = BuildSpec(metadata={"package": {"name": "fp-test", "version": "0.1"}})
        index = create_index(spec, [], pub)

        assert index.attestation_key_fp == expected

    def test_fingerprint_zero_when_no_key(self) -> None:
        """attestation_key_fp stays all-zeros when public_key is zero bytes."""
        spec = BuildSpec(metadata={"package": {"name": "fp-test", "version": "0.1"}})
        index = create_index(spec, [], b"\x00" * 32)

        assert index.attestation_key_fp == b"\x00" * 64

    def test_fingerprint_zero_when_empty_bytes(self) -> None:
        """attestation_key_fp stays all-zeros when public_key is empty bytes."""
        spec = BuildSpec(metadata={"package": {"name": "fp-test", "version": "0.1"}})
        index = create_index(spec, [], b"")

        assert index.attestation_key_fp == b"\x00" * 64


# ---------------------------------------------------------------------------
# Integration test: full PSPFBuilder round-trip
# ---------------------------------------------------------------------------


class TestBuilderFingerprintIntegration:
    """Full build pipeline writes fingerprint into the on-disk index."""

    @pytest.fixture
    def built_package(self) -> Iterator[Path]:
        """Build a minimal PSPF package and return its path."""
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "pkg.psp"
            result = (
                PSPFBuilder.create()
                .metadata(name="fp-integration", version="0.1")
                .add_slot(id="data", data=b"hello world")
                .with_keys(seed="integration-fp-seed")
                .build(output)
            )
            assert result.success, f"Build failed: {result.errors}"
            yield output

    def test_built_package_has_nonzero_fingerprint(self, built_package: Path) -> None:
        """The fingerprint in the on-disk index is not all zeros."""
        from flavor.psp.format_2025.reader import PSPFReader

        with PSPFReader(built_package) as reader:
            index = reader.read_index()

        assert index.attestation_key_fp != b"\x00" * 64

    def test_built_package_fingerprint_matches_key(self, built_package: Path) -> None:
        """The fingerprint in the on-disk index matches the signing key."""
        from flavor.psp.format_2025.reader import PSPFReader

        _, pub_raw = generate_deterministic_keys("integration-fp-seed")
        expected_fp = hashlib.sha256(pub_raw).hexdigest().encode("ascii")

        with PSPFReader(built_package) as reader:
            index = reader.read_index()

        assert index.attestation_key_fp == expected_fp

    def test_built_package_fingerprint_is_valid_hex(self, built_package: Path) -> None:
        """The fingerprint in the on-disk index is 64 lowercase hex ASCII bytes."""
        from flavor.psp.format_2025.reader import PSPFReader

        with PSPFReader(built_package) as reader:
            index = reader.read_index()

        fp_str = index.attestation_key_fp.decode("ascii")
        assert _HEX_RE.match(fp_str), f"Not 64 hex chars: {fp_str!r}"


# 🌶️📦🔚
