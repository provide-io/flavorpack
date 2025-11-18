#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for psp/format_2025/keys.py key resolution functions."""

from __future__ import annotations

from pathlib import Path

import pytest

from flavor.psp.format_2025.keys import (
    create_key_config,
    generate_deterministic_keys,
    generate_ephemeral_keys,
    load_keys_from_path,
    resolve_keys,
    save_keys_to_path,
)
from flavor.psp.format_2025.spec import KeyConfig


class TestResolveKeys:
    """Test resolve_keys function."""

    def test_resolve_explicit_keys(self) -> None:
        """Test resolution with explicit keys (priority 1)."""
        private_key = b"a" * 32
        public_key = b"b" * 32

        config = KeyConfig(
            private_key=private_key,
            public_key=public_key,
            key_seed=None,
            key_path=None,
        )

        priv, pub = resolve_keys(config)

        assert priv == private_key
        assert pub == public_key

    def test_resolve_from_seed(self) -> None:
        """Test resolution from seed (priority 2)."""
        config = KeyConfig(
            private_key=None,
            public_key=None,
            key_seed="test-seed-123",
            key_path=None,
        )

        priv, pub = resolve_keys(config)

        # Keys should be deterministic
        assert len(priv) == 32
        assert len(pub) == 32

        # Same seed should produce same keys
        priv2, pub2 = resolve_keys(config)
        assert priv == priv2
        assert pub == pub2

    def test_resolve_from_path(self, tmp_path: Path) -> None:
        """Test resolution from path (priority 3)."""
        # Create key files
        private_key = b"c" * 32
        public_key = b"d" * 32

        key_dir = tmp_path / "keys"
        key_dir.mkdir()
        (key_dir / "flavor-private.key").write_bytes(private_key)
        (key_dir / "flavor-public.key").write_bytes(public_key)

        config = KeyConfig(
            private_key=None,
            public_key=None,
            key_seed=None,
            key_path=key_dir,
        )

        priv, pub = resolve_keys(config)

        assert priv == private_key
        assert pub == public_key

    def test_resolve_ephemeral(self) -> None:
        """Test resolution with ephemeral generation (priority 4)."""
        config = KeyConfig(
            private_key=None,
            public_key=None,
            key_seed=None,
            key_path=None,
        )

        priv, pub = resolve_keys(config)

        # Keys should be valid
        assert len(priv) == 32
        assert len(pub) == 32

        # Ephemeral keys should be different each time
        priv2, pub2 = resolve_keys(config)
        assert priv != priv2
        assert pub != pub2

    def test_resolve_priority_explicit_over_seed(self) -> None:
        """Test that explicit keys take priority over seed."""
        private_key = b"e" * 32
        public_key = b"f" * 32

        config = KeyConfig(
            private_key=private_key,
            public_key=public_key,
            key_seed="should-be-ignored",
            key_path=None,
        )

        priv, pub = resolve_keys(config)

        # Should use explicit keys, not seed
        assert priv == private_key
        assert pub == public_key

    def test_resolve_priority_seed_over_path(self, tmp_path: Path) -> None:
        """Test that seed takes priority over path."""
        # Create key files
        key_dir = tmp_path / "keys"
        key_dir.mkdir()
        (key_dir / "flavor-private.key").write_bytes(b"g" * 32)
        (key_dir / "flavor-public.key").write_bytes(b"h" * 32)

        config = KeyConfig(
            private_key=None,
            public_key=None,
            key_seed="seed-takes-priority",
            key_path=key_dir,
        )

        priv, pub = resolve_keys(config)

        # Should use seed, not path
        # Verify by checking it's deterministic
        priv2, pub2 = generate_deterministic_keys("seed-takes-priority")
        assert priv == priv2
        assert pub == pub2


class TestGenerateDeterministicKeys:
    """Test generate_deterministic_keys function."""

    def test_generate_deterministic_keys_reproducible(self) -> None:
        """Test that same seed produces same keys."""
        seed = "my-test-seed"

        priv1, pub1 = generate_deterministic_keys(seed)
        priv2, pub2 = generate_deterministic_keys(seed)

        assert priv1 == priv2
        assert pub1 == pub2

    def test_generate_deterministic_keys_different_seeds(self) -> None:
        """Test that different seeds produce different keys."""
        priv1, pub1 = generate_deterministic_keys("seed1")
        priv2, pub2 = generate_deterministic_keys("seed2")

        assert priv1 != priv2
        assert pub1 != pub2

    def test_generate_deterministic_keys_valid_sizes(self) -> None:
        """Test that generated keys have correct sizes."""
        priv, pub = generate_deterministic_keys("test")

        assert len(priv) == 32
        assert len(pub) == 32

    def test_generate_deterministic_keys_unicode(self) -> None:
        """Test deterministic key generation with Unicode seed."""
        seed = "test-🔑-seed"

        priv, pub = generate_deterministic_keys(seed)

        assert len(priv) == 32
        assert len(pub) == 32

        # Should be reproducible
        priv2, pub2 = generate_deterministic_keys(seed)
        assert priv == priv2
        assert pub == pub2


class TestGenerateEphemeralKeys:
    """Test generate_ephemeral_keys function."""

    def test_generate_ephemeral_keys_valid_sizes(self) -> None:
        """Test that ephemeral keys have correct sizes."""
        priv, pub = generate_ephemeral_keys()

        assert len(priv) == 32
        assert len(pub) == 32

    def test_generate_ephemeral_keys_random(self) -> None:
        """Test that ephemeral keys are random."""
        priv1, pub1 = generate_ephemeral_keys()
        priv2, pub2 = generate_ephemeral_keys()

        assert priv1 != priv2
        assert pub1 != pub2

    def test_generate_ephemeral_keys_multiple(self) -> None:
        """Test generating multiple ephemeral key pairs."""
        keys = [generate_ephemeral_keys() for _ in range(5)]

        # All should be different
        private_keys = [priv for priv, _ in keys]
        public_keys = [pub for _, pub in keys]

        assert len(set(private_keys)) == 5
        assert len(set(public_keys)) == 5


class TestLoadKeysFromPath:
    """Test load_keys_from_path function."""

    def test_load_keys_success(self, tmp_path: Path) -> None:
        """Test successfully loading keys from path."""
        private_key = b"i" * 32
        public_key = b"j" * 32

        key_dir = tmp_path / "keys"
        key_dir.mkdir()
        (key_dir / "flavor-private.key").write_bytes(private_key)
        (key_dir / "flavor-public.key").write_bytes(public_key)

        priv, pub = load_keys_from_path(key_dir)

        assert priv == private_key
        assert pub == public_key

    def test_load_keys_private_not_found(self, tmp_path: Path) -> None:
        """Test loading keys when private key doesn't exist."""
        key_dir = tmp_path / "keys"
        key_dir.mkdir()
        (key_dir / "flavor-public.key").write_bytes(b"k" * 32)

        with pytest.raises(FileNotFoundError, match=r"Private key not found"):
            load_keys_from_path(key_dir)

    def test_load_keys_public_not_found(self, tmp_path: Path) -> None:
        """Test loading keys when public key doesn't exist."""
        key_dir = tmp_path / "keys"
        key_dir.mkdir()
        (key_dir / "flavor-private.key").write_bytes(b"l" * 32)

        with pytest.raises(FileNotFoundError, match=r"Public key not found"):
            load_keys_from_path(key_dir)

    def test_load_keys_invalid_private_size(self, tmp_path: Path) -> None:
        """Test loading keys with invalid private key size."""
        key_dir = tmp_path / "keys"
        key_dir.mkdir()
        (key_dir / "flavor-private.key").write_bytes(b"m" * 16)  # Wrong size
        (key_dir / "flavor-public.key").write_bytes(b"n" * 32)

        with pytest.raises(ValueError, match=r"Invalid private key size"):
            load_keys_from_path(key_dir)

    def test_load_keys_invalid_public_size(self, tmp_path: Path) -> None:
        """Test loading keys with invalid public key size."""
        key_dir = tmp_path / "keys"
        key_dir.mkdir()
        (key_dir / "flavor-private.key").write_bytes(b"o" * 32)
        (key_dir / "flavor-public.key").write_bytes(b"p" * 16)  # Wrong size

        with pytest.raises(ValueError, match=r"Invalid public key size"):
            load_keys_from_path(key_dir)


class TestSaveKeysToPath:
    """Test save_keys_to_path function."""

    def test_save_keys_success(self, tmp_path: Path) -> None:
        """Test successfully saving keys to path."""
        private_key = b"q" * 32
        public_key = b"r" * 32

        key_dir = tmp_path / "keys"

        save_keys_to_path(private_key, public_key, key_dir)

        # Verify directory was created
        assert key_dir.exists()

        # Verify keys were saved
        assert (key_dir / "flavor-private.key").read_bytes() == private_key
        assert (key_dir / "flavor-public.key").read_bytes() == public_key

        # Verify private key has restrictive permissions
        import stat

        mode = (key_dir / "flavor-private.key").stat().st_mode
        # Should have restrictive permissions (owner only)
        assert mode & stat.S_IRWXG == 0  # No group permissions
        assert mode & stat.S_IRWXO == 0  # No other permissions

    def test_save_keys_creates_directory(self, tmp_path: Path) -> None:
        """Test that save_keys creates directory if it doesn't exist."""
        private_key = b"s" * 32
        public_key = b"t" * 32

        key_dir = tmp_path / "nested" / "keys" / "dir"

        save_keys_to_path(private_key, public_key, key_dir)

        # Verify nested directory was created
        assert key_dir.exists()
        assert (key_dir / "flavor-private.key").exists()
        assert (key_dir / "flavor-public.key").exists()

    def test_save_keys_overwrites_existing(self, tmp_path: Path) -> None:
        """Test that save_keys overwrites existing key files."""
        key_dir = tmp_path / "keys"
        key_dir.mkdir()

        # Write initial keys
        old_private = b"u" * 32
        old_public = b"v" * 32
        (key_dir / "flavor-private.key").write_bytes(old_private)
        (key_dir / "flavor-public.key").write_bytes(old_public)

        # Overwrite with new keys
        new_private = b"w" * 32
        new_public = b"x" * 32
        save_keys_to_path(new_private, new_public, key_dir)

        # Verify keys were overwritten
        assert (key_dir / "flavor-private.key").read_bytes() == new_private
        assert (key_dir / "flavor-public.key").read_bytes() == new_public


class TestCreateKeyConfig:
    """Test create_key_config function."""

    def test_create_key_config_explicit_keys(self) -> None:
        """Test creating config with explicit keys."""
        private_key = b"y" * 32
        public_key = b"z" * 32

        config = create_key_config(private_key=private_key, public_key=public_key)

        assert config.private_key == private_key
        assert config.public_key == public_key
        assert config.key_seed is None
        assert config.key_path is None

    def test_create_key_config_seed(self) -> None:
        """Test creating config with seed."""
        config = create_key_config(seed="test-seed")

        assert config.private_key is None
        assert config.public_key is None
        assert config.key_seed == "test-seed"
        assert config.key_path is None

    def test_create_key_config_path(self, tmp_path: Path) -> None:
        """Test creating config with path."""
        key_path = tmp_path / "keys"

        config = create_key_config(key_path=key_path)

        assert config.private_key is None
        assert config.public_key is None
        assert config.key_seed is None
        assert config.key_path == key_path

    def test_create_key_config_empty(self) -> None:
        """Test creating config with no parameters (for ephemeral)."""
        config = create_key_config()

        assert config.private_key is None
        assert config.public_key is None
        assert config.key_seed is None
        assert config.key_path is None

    def test_create_key_config_only_private_key_error(self) -> None:
        """Test error when only private key provided."""
        with pytest.raises(ValueError, match=r"Both private and public keys must be provided"):
            create_key_config(private_key=b"a" * 32)

    def test_create_key_config_only_public_key_error(self) -> None:
        """Test error when only public key provided."""
        with pytest.raises(ValueError, match=r"Both private and public keys must be provided"):
            create_key_config(public_key=b"b" * 32)

    def test_create_key_config_multiple_sources_error(self) -> None:
        """Test error when multiple key sources specified."""
        with pytest.raises(ValueError, match=r"Only one key source can be specified"):
            create_key_config(
                private_key=b"c" * 32,
                public_key=b"d" * 32,
                seed="should-not-mix",
            )

    def test_create_key_config_seed_and_path_error(self, tmp_path: Path) -> None:
        """Test error when both seed and path specified."""
        with pytest.raises(ValueError, match=r"Only one key source can be specified"):
            create_key_config(seed="test-seed", key_path=tmp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# 🌶️📦🔚
