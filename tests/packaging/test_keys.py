#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test packaging/keys.py - Ed25519 key generation and loading."""

from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import dsa, ec, ed25519, rsa
import pytest

from flavor.packaging.keys import generate_key_pair, load_private_key_raw, load_public_key_raw


@pytest.mark.unit
class TestGenerateKeyPair:
    """Test Ed25519 key pair generation."""

    def test_generate_key_pair_success(self, tmp_path: Path) -> None:
        """Test successful key pair generation."""
        keys_dir = tmp_path / "keys"

        private_path, public_path = generate_key_pair(keys_dir)

        # Check paths are correct
        assert private_path == keys_dir / "flavor-private.key"
        assert public_path == keys_dir / "flavor-public.key"

        # Check files exist
        assert private_path.exists()
        assert public_path.exists()

        # Check files have content
        assert private_path.stat().st_size > 0
        assert public_path.stat().st_size > 0

    def test_generate_key_pair_creates_directory(self, tmp_path: Path) -> None:
        """Test key generation creates directory if it doesn't exist."""
        keys_dir = tmp_path / "new_keys"
        assert not keys_dir.exists()

        generate_key_pair(keys_dir)

        assert keys_dir.exists()
        assert keys_dir.is_dir()

    def test_generate_key_pair_pem_format(self, tmp_path: Path) -> None:
        """Test generated keys are in PEM format."""
        keys_dir = tmp_path / "keys"

        private_path, public_path = generate_key_pair(keys_dir)

        # Check PEM headers
        private_pem = private_path.read_text()
        public_pem = public_path.read_text()

        assert "-----BEGIN PRIVATE KEY-----" in private_pem
        assert "-----END PRIVATE KEY-----" in private_pem
        assert "-----BEGIN PUBLIC KEY-----" in public_pem
        assert "-----END PUBLIC KEY-----" in public_pem

    def test_generate_key_pair_ed25519_keys(self, tmp_path: Path) -> None:
        """Test generated keys are Ed25519."""
        keys_dir = tmp_path / "keys"

        private_path, public_path = generate_key_pair(keys_dir)

        # Load and verify private key type
        private_pem = private_path.read_bytes()
        private_key = serialization.load_pem_private_key(private_pem, password=None)
        assert isinstance(private_key, ed25519.Ed25519PrivateKey)

        # Load and verify public key type
        public_pem = public_path.read_bytes()
        public_key = serialization.load_pem_public_key(public_pem)
        assert isinstance(public_key, ed25519.Ed25519PublicKey)

    def test_generate_key_pair_keys_match(self, tmp_path: Path) -> None:
        """Test private and public keys are a matching pair."""
        keys_dir = tmp_path / "keys"

        private_path, public_path = generate_key_pair(keys_dir)

        # Load private key
        private_pem = private_path.read_bytes()
        private_key = serialization.load_pem_private_key(private_pem, password=None)

        # Derive public key from private key
        derived_public = private_key.public_key()  # type: ignore[attr-defined]

        # Load stored public key
        public_pem = public_path.read_bytes()
        stored_public = serialization.load_pem_public_key(public_pem)

        # Compare public key bytes
        derived_bytes = derived_public.public_bytes(  # type: ignore[attr-defined]
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        stored_bytes = stored_public.public_bytes(  # type: ignore[attr-defined]
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )

        assert derived_bytes == stored_bytes

    def test_generate_key_pair_file_permissions(self, tmp_path: Path) -> None:
        """Test generated keys have appropriate permissions."""
        keys_dir = tmp_path / "keys"

        private_path, public_path = generate_key_pair(keys_dir)

        # Both should have restricted permissions (from DEFAULT_FILE_PERMS)
        private_mode = private_path.stat().st_mode & 0o777
        public_mode = public_path.stat().st_mode & 0o777

        # Should have secure permissions set
        assert private_mode <= 0o600  # At most owner read/write
        assert public_mode <= 0o644  # Public key can be slightly more open


@pytest.mark.unit
class TestLoadPrivateKeyRaw:
    """Test loading private keys from PEM files."""

    def test_load_private_key_raw_success(self, tmp_path: Path) -> None:
        """Test successfully loading Ed25519 private key."""
        keys_dir = tmp_path / "keys"
        private_path, _ = generate_key_pair(keys_dir)

        raw_key = load_private_key_raw(private_path)

        # Ed25519 private key seed is 32 bytes
        assert isinstance(raw_key, bytes)
        assert len(raw_key) == 32

    def test_load_private_key_raw_invalid_file(self, tmp_path: Path) -> None:
        """Test loading invalid PEM file raises ValueError."""
        invalid_key = tmp_path / "invalid.key"
        invalid_key.write_text("not a valid PEM file")

        with pytest.raises(ValueError, match="Failed to load private key"):
            load_private_key_raw(invalid_key)

    def test_load_private_key_raw_file_not_found(self, tmp_path: Path) -> None:
        """Test loading non-existent file raises appropriate error."""
        nonexistent = tmp_path / "nonexistent.key"

        with pytest.raises((ValueError, FileNotFoundError)):
            load_private_key_raw(nonexistent)

    def test_load_private_key_raw_rsa_key_error(self, tmp_path: Path) -> None:
        """Test loading RSA key raises helpful error."""
        # Generate RSA key instead of Ed25519
        rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        rsa_pem = rsa_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        rsa_key_path = tmp_path / "rsa.key"
        rsa_key_path.write_bytes(rsa_pem)

        with pytest.raises(ValueError, match=r"Incompatible key type.*RSA"):
            load_private_key_raw(rsa_key_path)

    def test_load_private_key_raw_ec_key_error(self, tmp_path: Path) -> None:
        """Test loading EC key raises helpful error."""
        # Generate EC key
        ec_key = ec.generate_private_key(ec.SECP256R1())
        ec_pem = ec_key.private_bytes(  # type: ignore[attr-defined]
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        ec_key_path = tmp_path / "ec.key"
        ec_key_path.write_bytes(ec_pem)

        with pytest.raises(ValueError, match=r"Incompatible key type.*EC"):
            load_private_key_raw(ec_key_path)

    def test_load_private_key_raw_dsa_key_error(self, tmp_path: Path) -> None:
        """Test loading DSA key raises helpful error."""
        # Generate DSA key
        dsa_key = dsa.generate_private_key(key_size=2048)
        dsa_pem = dsa_key.private_bytes(  # type: ignore[attr-defined]
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        dsa_key_path = tmp_path / "dsa.key"
        dsa_key_path.write_bytes(dsa_pem)

        with pytest.raises(ValueError, match=r"Incompatible key type.*DSA"):
            load_private_key_raw(dsa_key_path)

    def test_load_private_key_raw_helpful_error_message(self, tmp_path: Path) -> None:
        """Test error messages include helpful recovery instructions."""
        rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        rsa_pem = rsa_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        rsa_key_path = tmp_path / "rsa.key"
        rsa_key_path.write_bytes(rsa_pem)

        with pytest.raises(ValueError) as exc_info:
            load_private_key_raw(rsa_key_path)

        error_msg = str(exc_info.value)
        assert "Ed25519 is required" in error_msg
        assert "flavor keygen" in error_msg


@pytest.mark.unit
class TestLoadPublicKeyRaw:
    """Test loading public keys from PEM files."""

    def test_load_public_key_raw_success(self, tmp_path: Path) -> None:
        """Test successfully loading Ed25519 public key."""
        keys_dir = tmp_path / "keys"
        _, public_path = generate_key_pair(keys_dir)

        raw_key = load_public_key_raw(public_path)

        # Ed25519 public key is 32 bytes
        assert isinstance(raw_key, bytes)
        assert len(raw_key) == 32

    def test_load_public_key_raw_invalid_file(self, tmp_path: Path) -> None:
        """Test loading invalid PEM file raises ValueError."""
        invalid_key = tmp_path / "invalid.key"
        invalid_key.write_text("not a valid PEM file")

        with pytest.raises(ValueError, match="Failed to load public key"):
            load_public_key_raw(invalid_key)

    def test_load_public_key_raw_file_not_found(self, tmp_path: Path) -> None:
        """Test loading non-existent file raises appropriate error."""
        nonexistent = tmp_path / "nonexistent.key"

        with pytest.raises((ValueError, FileNotFoundError)):
            load_public_key_raw(nonexistent)

    def test_load_public_key_raw_rsa_key_error(self, tmp_path: Path) -> None:
        """Test loading RSA public key raises helpful error."""
        # Generate RSA key and extract public key
        rsa_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        rsa_public = rsa_private.public_key()
        rsa_pub_pem = rsa_public.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        rsa_pub_path = tmp_path / "rsa_pub.key"
        rsa_pub_path.write_bytes(rsa_pub_pem)

        with pytest.raises(ValueError, match=r"Incompatible key type.*RSA"):
            load_public_key_raw(rsa_pub_path)

    def test_load_public_key_raw_ec_key_error(self, tmp_path: Path) -> None:
        """Test loading EC public key raises helpful error."""
        # Generate EC key and extract public key
        ec_private = ec.generate_private_key(ec.SECP256R1())
        ec_public = ec_private.public_key()
        ec_pub_pem = ec_public.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        ec_pub_path = tmp_path / "ec_pub.key"
        ec_pub_path.write_bytes(ec_pub_pem)

        with pytest.raises(ValueError, match=r"Incompatible key type.*EC"):
            load_public_key_raw(ec_pub_path)

    def test_load_public_key_raw_dsa_key_error(self, tmp_path: Path) -> None:
        """Test loading DSA public key raises helpful error."""
        # Generate DSA key and extract public key
        dsa_private = dsa.generate_private_key(key_size=2048)
        dsa_public = dsa_private.public_key()
        dsa_pub_pem = dsa_public.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        dsa_pub_path = tmp_path / "dsa_pub.key"
        dsa_pub_path.write_bytes(dsa_pub_pem)

        with pytest.raises(ValueError, match=r"Incompatible key type.*DSA"):
            load_public_key_raw(dsa_pub_path)

    def test_load_public_key_raw_helpful_error_message(self, tmp_path: Path) -> None:
        """Test error messages include helpful recovery instructions."""
        rsa_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        rsa_public = rsa_private.public_key()
        rsa_pub_pem = rsa_public.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        rsa_pub_path = tmp_path / "rsa_pub.key"
        rsa_pub_path.write_bytes(rsa_pub_pem)

        with pytest.raises(ValueError) as exc_info:
            load_public_key_raw(rsa_pub_path)

        error_msg = str(exc_info.value)
        assert "Ed25519 is required" in error_msg
        assert "flavor keygen" in error_msg


@pytest.mark.unit
class TestKeyPairIntegration:
    """Test integration between key generation and loading."""

    def test_generate_and_load_round_trip(self, tmp_path: Path) -> None:
        """Test keys can be generated and loaded back."""
        keys_dir = tmp_path / "keys"

        # Generate keys
        private_path, public_path = generate_key_pair(keys_dir)

        # Load them back
        private_raw = load_private_key_raw(private_path)
        public_raw = load_public_key_raw(public_path)

        # Verify correct sizes
        assert len(private_raw) == 32
        assert len(public_raw) == 32

    def test_loaded_keys_can_sign_and_verify(self, tmp_path: Path) -> None:
        """Test loaded keys can actually be used for signing."""
        keys_dir = tmp_path / "keys"

        # Generate and load keys
        private_path, public_path = generate_key_pair(keys_dir)
        private_raw = load_private_key_raw(private_path)
        public_raw = load_public_key_raw(public_path)

        # Reconstruct keys from raw bytes
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_raw)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_raw)

        # Sign a message
        message = b"test message"
        signature = private_key.sign(message)

        # Verify with public key (should not raise)
        public_key.verify(signature, message)

    def test_keys_consistent_across_loads(self, tmp_path: Path) -> None:
        """Test loading same key file multiple times gives same result."""
        keys_dir = tmp_path / "keys"
        private_path, public_path = generate_key_pair(keys_dir)

        # Load multiple times
        private1 = load_private_key_raw(private_path)
        private2 = load_private_key_raw(private_path)
        public1 = load_public_key_raw(public_path)
        public2 = load_public_key_raw(public_path)

        # Should be identical
        assert private1 == private2
        assert public1 == public2


# 🌶️📦🔚
