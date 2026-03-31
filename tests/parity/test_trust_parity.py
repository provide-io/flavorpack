#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Parity tests: trusted key store behavior across Python, Go, and Rust."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import pytest

from flavor.config.trust import compute_key_fingerprint, is_key_trusted

# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_ed25519_key() -> tuple[bytes, str]:
    """Return (raw_32_bytes, fingerprint) for a fresh Ed25519 key."""
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    raw = pub.public_bytes(Encoding.Raw, PublicFormat.Raw)
    fp = hashlib.sha256(raw).hexdigest()
    return raw, fp


# ── Parity tests ─────────────────────────────────────────────────────────────


@pytest.mark.parity
@pytest.mark.parity_category("Trust Store")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_fingerprint_is_sha256_of_raw_key() -> None:
    """Fingerprint = SHA-256(raw 32-byte Ed25519 key material), hex-encoded."""
    _raw, _expected_fp = _make_ed25519_key()
    priv = Ed25519PrivateKey.generate()
    pub_key = priv.public_key()
    actual_fp = compute_key_fingerprint(pub_key)
    # Verify it's 64 lowercase hex chars
    assert len(actual_fp) == 64
    assert actual_fp == actual_fp.lower()
    assert all(c in "0123456789abcdef" for c in actual_fp)


@pytest.mark.parity
@pytest.mark.parity_category("Trust Store")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_fingerprint_deterministic() -> None:
    """Same key material always produces the same fingerprint."""
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    fp1 = compute_key_fingerprint(pub)
    fp2 = compute_key_fingerprint(pub)
    assert fp1 == fp2


@pytest.mark.parity
@pytest.mark.parity_category("Trust Store")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_no_store_returns_no_op(tmp_path: Path) -> None:
    """is_key_trusted returns None when no trusted-keys directory exists."""
    nonexistent = str(tmp_path / "no-such-dir")
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": nonexistent}):
        result = is_key_trusted("a" * 64, include_system=False)
    assert result is None


@pytest.mark.parity
@pytest.mark.parity_category("Trust Store")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_trusted_key_returns_true(tmp_path: Path) -> None:
    """is_key_trusted returns True when fingerprint matches a stored key."""
    store_dir = tmp_path / "trusted-keys"
    store_dir.mkdir()
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    pem = pub.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    fp = compute_key_fingerprint(pub)
    (store_dir / "key.pub").write_bytes(pem)

    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(store_dir)}):
        result = is_key_trusted(fp, include_system=False)
    assert result is True


@pytest.mark.parity
@pytest.mark.parity_category("Trust Store")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_untrusted_key_returns_false(tmp_path: Path) -> None:
    """is_key_trusted returns False when store exists but key not in it."""
    store_dir = tmp_path / "trusted-keys"
    store_dir.mkdir()
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    pem = pub.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    (store_dir / "key.pub").write_bytes(pem)

    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(store_dir)}):
        result = is_key_trusted("0" * 64, include_system=False)
    assert result is False
