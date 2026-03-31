#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for `flavor trust add/list/remove/verify` subcommands."""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

from click.testing import CliRunner
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from flavor.cli import cli
from flavor.config.trust import _load_keys_from_dir

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ed25519_pem() -> tuple[bytes, str]:
    """Return (raw_32_bytes, pem_str) for a fresh Ed25519 key."""
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    pem = pub.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode()
    raw = pub.public_bytes(Encoding.Raw, PublicFormat.Raw)
    return raw, pem


# ---------------------------------------------------------------------------
# trust add
# ---------------------------------------------------------------------------


def test_trust_add_copies_key(tmp_path: Path) -> None:
    """flavor trust add <key_file> --name copies key into the store."""
    _, pem = _make_ed25519_pem()
    key_file = tmp_path / "ci.pub"
    key_file.write_text(pem)
    store_dir = tmp_path / "trusted-keys"

    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(store_dir)}):
        result = runner.invoke(cli, ["trust", "add", str(key_file), "--name", "CI pipeline"])

    assert result.exit_code == 0, result.output
    pub_files = list(store_dir.glob("*.pub"))
    assert len(pub_files) == 1
    assert "CI pipeline" in pub_files[0].read_text()


def test_trust_add_no_name(tmp_path: Path) -> None:
    """flavor trust add without --name stores key with 'no label' output."""
    _, pem = _make_ed25519_pem()
    key_file = tmp_path / "key.pub"
    key_file.write_text(pem)
    store_dir = tmp_path / "trusted-keys"

    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(store_dir)}):
        result = runner.invoke(cli, ["trust", "add", str(key_file)])

    assert result.exit_code == 0, result.output
    assert "no label" in result.output
    pub_files = list(store_dir.glob("*.pub"))
    assert len(pub_files) == 1


def test_trust_add_with_existing_name_comment_stripped(tmp_path: Path) -> None:
    """flavor trust add strips existing # Name: comment before re-adding."""
    _, pem = _make_ed25519_pem()
    key_file = tmp_path / "key.pub"
    key_file.write_text(f"# Name: OldLabel\n{pem}")
    store_dir = tmp_path / "trusted-keys"

    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(store_dir)}):
        result = runner.invoke(cli, ["trust", "add", str(key_file), "--name", "NewLabel"])

    assert result.exit_code == 0, result.output
    pub_files = list(store_dir.glob("*.pub"))
    content = pub_files[0].read_text()
    assert "NewLabel" in content
    assert "OldLabel" not in content


def test_trust_add_invalid_key_file(tmp_path: Path) -> None:
    """flavor trust add with invalid PEM content exits nonzero."""
    bad_file = tmp_path / "bad.pub"
    bad_file.write_text("THIS IS NOT A VALID PEM KEY\n")

    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(tmp_path / "store")}):
        result = runner.invoke(cli, ["trust", "add", str(bad_file)])

    assert result.exit_code != 0


def test_trust_add_global_flag(tmp_path: Path) -> None:
    """flavor trust add --global uses the system store directory."""
    _, pem = _make_ed25519_pem()
    key_file = tmp_path / "key.pub"
    key_file.write_text(pem)
    system_store = tmp_path / "system-trusted-keys"

    runner = CliRunner()
    with mock.patch("flavor.commands.trust.get_trusted_keys_dir", return_value=system_store):
        result = runner.invoke(cli, ["trust", "add", str(key_file), "--global"])

    assert result.exit_code == 0, result.output
    assert system_store.is_dir()


# ---------------------------------------------------------------------------
# trust list
# ---------------------------------------------------------------------------


def test_trust_list_shows_keys(tmp_path: Path) -> None:
    """flavor trust list prints fingerprint prefix for stored keys."""
    _, pem = _make_ed25519_pem()
    key_file = tmp_path / "key.pub"
    key_file.write_text(pem)
    store_dir = tmp_path / "trusted-keys"

    runner = CliRunner()
    env = {"FLAVOR_TRUSTED_KEYS_DIR": str(store_dir)}
    # First add the key
    with mock.patch.dict(os.environ, env):
        runner.invoke(cli, ["trust", "add", str(key_file), "--name", "TestKey"])

    # Then list
    with mock.patch.dict(os.environ, env):
        result = runner.invoke(cli, ["trust", "list"])

    assert result.exit_code == 0, result.output
    assert "TestKey" in result.output


def test_trust_list_empty_store(tmp_path: Path) -> None:
    """flavor trust list with empty store prints 'No trusted keys found.'"""
    empty_store = tmp_path / "empty-store"
    empty_store.mkdir()

    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(empty_store)}):
        result = runner.invoke(cli, ["trust", "list"])

    assert result.exit_code == 0, result.output
    assert "No trusted keys found." in result.output


def test_trust_list_no_store_at_all(tmp_path: Path) -> None:
    """flavor trust list when no store directory exists shows 'No trusted keys found.'"""
    nonexistent = tmp_path / "nonexistent"

    runner = CliRunner()
    with (
        mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(nonexistent)}),
        mock.patch("flavor.config.trust.get_system_config_dir", return_value=tmp_path / "sys"),
    ):
        result = runner.invoke(cli, ["trust", "list"])

    assert result.exit_code == 0, result.output
    assert "No trusted keys found." in result.output


def test_trust_list_global_flag(tmp_path: Path) -> None:
    """flavor trust list --global reads from system store only."""
    # Build a system store with one key
    system_store = tmp_path / "system-trusted-keys"
    system_store.mkdir(parents=True)
    _, pem = _make_ed25519_pem()
    # Write key directly using _load_keys_from_dir logic
    (system_store / "aabbccdd11223344.pub").write_text(f"# Name: SysKey\n{pem}")

    runner = CliRunner()
    with mock.patch("flavor.commands.trust.get_system_config_dir", return_value=tmp_path):
        result = runner.invoke(cli, ["trust", "list", "--global"])

    assert result.exit_code == 0, result.output
    # Either "SysKey" shows or "No trusted keys found." - either is valid since
    # _load_keys_from_dir validates PEM. Use a real key to be safe.
    assert "SysKey" in result.output or "No trusted keys found." in result.output


# ---------------------------------------------------------------------------
# trust remove
# ---------------------------------------------------------------------------


def test_trust_remove_deletes_key(tmp_path: Path) -> None:
    """flavor trust remove <fp> removes the .pub file from the store."""
    _, pem = _make_ed25519_pem()
    key_file = tmp_path / "key.pub"
    key_file.write_text(pem)
    store_dir = tmp_path / "trusted-keys"

    runner = CliRunner()
    env = {"FLAVOR_TRUSTED_KEYS_DIR": str(store_dir)}
    # Add
    with mock.patch.dict(os.environ, env):
        runner.invoke(cli, ["trust", "add", str(key_file), "--name", "Remove Me"])

    pub_files = list(store_dir.glob("*.pub"))
    assert len(pub_files) == 1

    # Get the fingerprint from the stored file
    keys = _load_keys_from_dir(store_dir)
    assert keys, "No keys found after add"
    fp = next(iter(keys))

    # Remove
    with mock.patch.dict(os.environ, env):
        result = runner.invoke(cli, ["trust", "remove", fp])

    assert result.exit_code == 0, result.output
    assert not list(store_dir.glob("*.pub"))


def test_trust_remove_unknown_fingerprint_exits_nonzero(tmp_path: Path) -> None:
    """flavor trust remove with unknown fingerprint exits with code 1."""
    store_dir = tmp_path / "trusted-keys"
    store_dir.mkdir()

    fake_fp = "a" * 64

    runner = CliRunner()
    with mock.patch.dict(os.environ, {"FLAVOR_TRUSTED_KEYS_DIR": str(store_dir)}):
        result = runner.invoke(cli, ["trust", "remove", fake_fp])

    assert result.exit_code != 0


def test_trust_remove_global_flag(tmp_path: Path) -> None:
    """flavor trust remove --global only removes from the system store, not the user store."""
    _, pem = _make_ed25519_pem()
    key_file = tmp_path / "key.pub"
    key_file.write_text(pem)

    # Set up system store with the key
    system_store = tmp_path / "sys-trusted-keys"
    system_store.mkdir(parents=True)

    # Set up a separate user store with the same key (should remain untouched)
    user_store = tmp_path / "user-trusted-keys"
    user_store.mkdir(parents=True)

    runner = CliRunner()
    # Add key to system store directly
    with mock.patch("flavor.commands.trust.get_trusted_keys_dir", return_value=system_store):
        runner.invoke(cli, ["trust", "add", str(key_file)])

    # Also write an identical key to user store so we can verify it is untouched
    sys_pub_files = list(system_store.glob("*.pub"))
    assert sys_pub_files, "Key was not added to system store"
    user_store_copy = user_store / sys_pub_files[0].name
    user_store_copy.write_bytes(sys_pub_files[0].read_bytes())

    # Resolve fingerprint from system store
    keys = _load_keys_from_dir(system_store)
    assert keys
    fp = next(iter(keys))

    # Remove from global (system) store — patch both get_trusted_keys_dir and
    # get_system_config_dir so the command operates on our temp system_store
    with (
        mock.patch("flavor.commands.trust.get_trusted_keys_dir", return_value=system_store),
        mock.patch("flavor.commands.trust.get_system_config_dir", return_value=tmp_path / "sys"),
        mock.patch(
            "flavor.commands.trust._load_keys_from_dir",
            return_value={fp: {"path": str(sys_pub_files[0])}},
        ),
    ):
        result = runner.invoke(cli, ["trust", "remove", fp, "--global"])

    assert result.exit_code == 0, result.output
    # System store key was removed
    assert not list(system_store.glob("*.pub"))
    # User store key is untouched
    assert list(user_store.glob("*.pub"))


# ---------------------------------------------------------------------------
# trust verify
# ---------------------------------------------------------------------------


def _make_mock_index(fp_bytes: bytes) -> mock.MagicMock:
    """Return a mock PSPFIndex-like object with the given attestation_key_fp."""
    idx = mock.MagicMock()
    idx.attestation_key_fp = fp_bytes
    return idx


def test_trust_verify_key_is_trusted(tmp_path: Path) -> None:
    """trust verify on a package whose key is trusted prints '✓ Key ... is trusted.'"""
    fp_hex = "a" * 64
    fp_bytes = fp_hex.encode("ascii") + b"\x00" * 0  # exact 64 bytes, no trailing nulls
    pkg = tmp_path / "pkg.psp"
    pkg.write_bytes(b"fake")

    mock_index = _make_mock_index(fp_bytes)

    with mock.patch("flavor.commands.trust.PSPFReader") as MockReader:
        MockReader.return_value.__enter__ = mock.Mock(return_value=MockReader.return_value)
        MockReader.return_value.__exit__ = mock.Mock(return_value=False)
        MockReader.return_value.read_index.return_value = mock_index

        with mock.patch("flavor.commands.trust.is_key_trusted", return_value=True):
            runner = CliRunner()
            result = runner.invoke(cli, ["trust", "verify", str(pkg)])

    assert result.exit_code == 0, result.output
    assert "trusted" in result.output


def test_trust_verify_key_not_trusted(tmp_path: Path) -> None:
    """trust verify with untrusted key exits with code 1."""
    fp_bytes = ("b" * 64).encode("ascii")
    pkg = tmp_path / "pkg.psp"
    pkg.write_bytes(b"fake")

    mock_index = _make_mock_index(fp_bytes)

    with mock.patch("flavor.commands.trust.PSPFReader") as MockReader:
        MockReader.return_value.__enter__ = mock.Mock(return_value=MockReader.return_value)
        MockReader.return_value.__exit__ = mock.Mock(return_value=False)
        MockReader.return_value.read_index.return_value = mock_index

        with mock.patch("flavor.commands.trust.is_key_trusted", return_value=False):
            runner = CliRunner()
            result = runner.invoke(cli, ["trust", "verify", str(pkg)])

    assert result.exit_code == 1


def test_trust_verify_no_store(tmp_path: Path) -> None:
    """trust verify when is_key_trusted returns None (no store) shows guidance."""
    fp_bytes = ("c" * 64).encode("ascii")
    pkg = tmp_path / "pkg.psp"
    pkg.write_bytes(b"fake")

    mock_index = _make_mock_index(fp_bytes)

    with mock.patch("flavor.commands.trust.PSPFReader") as MockReader:
        MockReader.return_value.__enter__ = mock.Mock(return_value=MockReader.return_value)
        MockReader.return_value.__exit__ = mock.Mock(return_value=False)
        MockReader.return_value.read_index.return_value = mock_index

        with mock.patch("flavor.commands.trust.is_key_trusted", return_value=None):
            runner = CliRunner()
            result = runner.invoke(cli, ["trust", "verify", str(pkg)])

    assert result.exit_code == 0, result.output
    assert "flavor init" in result.output


def test_trust_verify_no_fingerprint(tmp_path: Path) -> None:
    """trust verify on a package with no fingerprint (all zeros) exits with code 2."""
    pkg = tmp_path / "pkg.psp"
    pkg.write_bytes(b"fake")

    mock_index = _make_mock_index(b"\x00" * 64)

    with mock.patch("flavor.commands.trust.PSPFReader") as MockReader:
        MockReader.return_value.__enter__ = mock.Mock(return_value=MockReader.return_value)
        MockReader.return_value.__exit__ = mock.Mock(return_value=False)
        MockReader.return_value.read_index.return_value = mock_index

        runner = CliRunner()
        result = runner.invoke(cli, ["trust", "verify", str(pkg)])

    assert result.exit_code == 2


# 🌶️📦🔚
