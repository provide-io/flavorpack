#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for the trusted key store."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from flavor.config.trust import (
    _load_keys_from_dir,
    compute_key_fingerprint,
    is_key_trusted,
    load_trusted_keys,
)


def _make_pub_key_pem(tmp_path: Path, name: str | None = None) -> tuple[Path, str]:
    """Generate an Ed25519 key, write .pub PEM, return (path, fingerprint)."""
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    pub_bytes = public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    raw = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    fingerprint = hashlib.sha256(raw).hexdigest()
    label = f"# Name: {name}\n".encode() if name else b""
    content = label + pub_bytes
    pub_file = tmp_path / f"{fingerprint[:8]}.pub"
    pub_file.write_bytes(content)
    return pub_file, fingerprint


def test_compute_key_fingerprint() -> None:
    """Fingerprint is deterministic SHA-256 hex of raw key bytes."""
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    raw = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    expected = hashlib.sha256(raw).hexdigest()
    assert compute_key_fingerprint(public_key) == expected
    assert len(compute_key_fingerprint(public_key)) == 64


def test_load_trusted_keys_empty_dir(tmp_path: Path) -> None:
    """Loading keys from an empty directory returns an empty dict."""
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(tmp_path), "FLAVOR_CONFIG_DIR": ""}):
        keys = load_trusted_keys(include_system=False)
    assert keys == {}


def test_load_trusted_keys_reads_pub_files(tmp_path: Path) -> None:
    """Loading keys from a directory with .pub files returns them keyed by fingerprint."""
    _pub_file, fingerprint = _make_pub_key_pem(tmp_path)
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(tmp_path), "FLAVOR_CONFIG_DIR": ""}):
        keys = load_trusted_keys(include_system=False)
    assert fingerprint in keys
    assert len(keys) == 1


def test_load_trusted_keys_missing_dir_returns_empty() -> None:
    """Loading keys from a nonexistent directory returns an empty dict."""
    with mock.patch.dict(
        os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": "/nonexistent/path/xyz", "FLAVOR_CONFIG_DIR": ""}
    ):
        keys = load_trusted_keys(include_system=False)
    assert keys == {}


def test_is_key_trusted_match(tmp_path: Path) -> None:
    """is_key_trusted returns True when the fingerprint is in the store."""
    _pub_file, fingerprint = _make_pub_key_pem(tmp_path)
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(tmp_path), "FLAVOR_CONFIG_DIR": ""}):
        result = is_key_trusted(fingerprint, include_system=False)
    assert result is True


def test_is_key_trusted_no_match(tmp_path: Path) -> None:
    """is_key_trusted returns False when the store exists but fingerprint is absent."""
    _make_pub_key_pem(tmp_path)
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(tmp_path), "FLAVOR_CONFIG_DIR": ""}):
        result = is_key_trusted("a" * 64, include_system=False)
    assert result is False


def test_is_key_trusted_no_store_returns_none() -> None:
    """is_key_trusted returns None when no store directories exist."""
    with (
        mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": "/nonexistent/xyz", "FLAVOR_CONFIG_DIR": ""}),
        mock.patch("flavor.config.trust.get_system_config_dir") as mock_sys,
    ):
        mock_sys.return_value = Path("/nonexistent/system/xyz")
        result = is_key_trusted("a" * 64, include_system=True)
    assert result is None


def test_load_keys_from_dir_non_ed25519_key(tmp_path: Path) -> None:
    """Non-Ed25519 keys are skipped with a warning."""
    from cryptography.hazmat.backends import default_backend

    rsa_key = generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    rsa_pub = rsa_key.public_key()
    pub_bytes = rsa_pub.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    pub_file = tmp_path / "rsa_key.pub"
    pub_file.write_bytes(pub_bytes)

    result = _load_keys_from_dir(tmp_path)
    assert result == {}


def test_load_keys_from_dir_malformed_file(tmp_path: Path) -> None:
    """Malformed .pub files are skipped with a warning."""
    bad_file = tmp_path / "bad.pub"
    bad_file.write_bytes(b"this is not a valid PEM key at all")

    result = _load_keys_from_dir(tmp_path)
    assert result == {}


def test_load_trusted_keys_include_system_false(tmp_path: Path) -> None:
    """include_system=False loads only user keys, skipping system dir."""
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    system_dir = tmp_path / "system"
    system_dir.mkdir()

    _make_pub_key_pem(user_dir, name="user-key")
    _make_pub_key_pem(system_dir, name="system-key")

    with (
        mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(user_dir), "FLAVOR_CONFIG_DIR": ""}),
        mock.patch("flavor.config.trust.get_system_config_dir") as mock_sys,
    ):
        mock_sys.return_value = system_dir.parent  # system dir would be parent / "trusted-keys"
        keys = load_trusted_keys(include_system=False)

    # Only user keys should be loaded
    assert len(keys) == 1
    for entry in keys.values():
        assert entry["name"] == "user-key"


def test_is_key_trusted_include_system_false(tmp_path: Path) -> None:
    """is_key_trusted with include_system=False only checks user store."""
    user_dir = tmp_path / "user"
    user_dir.mkdir()

    _pub_file, fingerprint = _make_pub_key_pem(user_dir)

    with (
        mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(user_dir), "FLAVOR_CONFIG_DIR": ""}),
        mock.patch("flavor.config.trust.get_system_config_dir") as mock_sys,
    ):
        mock_sys.return_value = Path("/nonexistent/system")
        result = is_key_trusted(fingerprint, include_system=False)
    assert result is True


def test_load_keys_name_extracted_correctly(tmp_path: Path) -> None:
    """The # Name: comment is extracted and stored in the key entry."""
    _pub_file, fingerprint = _make_pub_key_pem(tmp_path, name="my-signing-key")

    result = _load_keys_from_dir(tmp_path)
    assert fingerprint in result
    assert result[fingerprint]["name"] == "my-signing-key"


def test_load_keys_no_name_is_none(tmp_path: Path) -> None:
    """Keys without a # Name: comment have name=None."""
    _pub_file, fingerprint = _make_pub_key_pem(tmp_path, name=None)

    result = _load_keys_from_dir(tmp_path)
    assert fingerprint in result
    assert result[fingerprint]["name"] is None


def test_load_keys_path_stored_correctly(tmp_path: Path) -> None:
    """The path to the .pub file is stored in the key entry."""
    pub_file, fingerprint = _make_pub_key_pem(tmp_path)

    result = _load_keys_from_dir(tmp_path)
    assert result[fingerprint]["path"] == pub_file


def test_load_trusted_keys_include_system_merges(tmp_path: Path) -> None:
    """include_system=True merges system and user keys."""
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    system_dir = tmp_path / "system" / "trusted-keys"
    system_dir.mkdir(parents=True)

    _pub_file1, fp1 = _make_pub_key_pem(user_dir, name="user-key")
    _pub_file2, fp2 = _make_pub_key_pem(system_dir, name="system-key")

    with (
        mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(user_dir), "FLAVOR_CONFIG_DIR": ""}),
        mock.patch("flavor.config.trust.get_system_config_dir") as mock_sys,
    ):
        mock_sys.return_value = system_dir.parent
        keys = load_trusted_keys(include_system=True)

    assert fp1 in keys
    assert fp2 in keys
    assert len(keys) == 2


def test_load_keys_from_dir_not_a_dir(tmp_path: Path) -> None:
    """Passing a path that is not a directory returns empty dict."""
    result = _load_keys_from_dir(tmp_path / "nonexistent")
    assert result == {}


def test_is_key_trusted_system_store_only(tmp_path: Path) -> None:
    """is_key_trusted returns correct result when only system store exists."""
    system_dir = tmp_path / "trusted-keys"
    system_dir.mkdir()
    _pub_file, fingerprint = _make_pub_key_pem(system_dir, name="system-key")

    with (
        mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": "/nonexistent/user", "FLAVOR_CONFIG_DIR": ""}),
        mock.patch("flavor.config.trust.get_system_config_dir") as mock_sys,
    ):
        mock_sys.return_value = tmp_path
        result = is_key_trusted(fingerprint, include_system=True)
    assert result is True


def test_is_key_trusted_no_store_include_system_false() -> None:
    """is_key_trusted returns None when user store doesn't exist and include_system=False."""
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": "/nonexistent/xyz", "FLAVOR_CONFIG_DIR": ""}):
        result = is_key_trusted("a" * 64, include_system=False)
    assert result is None


def test_load_keys_trace_logging(tmp_path: Path) -> None:
    """log.trace is called when trace logging is enabled."""
    _pub_file, fingerprint = _make_pub_key_pem(tmp_path, name="trace-key")

    with mock.patch("flavor.config.trust.log") as mock_log:
        mock_log.is_trace_enabled.return_value = True
        result = _load_keys_from_dir(tmp_path)

    assert fingerprint in result
    mock_log.trace.assert_called_once()
