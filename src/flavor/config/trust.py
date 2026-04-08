#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Trusted key store for Flavorpack package signature verification."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    load_pem_public_key,
)

from flavor.config.dirs import get_system_config_dir, get_trusted_keys_dir
from flavor.console import get_command_logger

log = get_command_logger("config.trust")


def compute_key_fingerprint(public_key: Ed25519PublicKey) -> str:
    """Return the SHA-256 fingerprint of an Ed25519 public key.

    The fingerprint is SHA-256 of the raw 32-byte key material, hex-encoded
    (64 ASCII characters, lowercase).
    """
    raw = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    return hashlib.sha256(raw).hexdigest()


def _load_keys_from_dir(keys_dir: Path) -> dict[str, dict[str, Any]]:
    """Load all .pub files from a directory."""
    if not keys_dir.is_dir():
        return {}

    result: dict[str, dict[str, Any]] = {}
    for pub_file in sorted(keys_dir.glob("*.pub")):
        try:
            content = pub_file.read_bytes()
            name: str | None = None

            lines = content.decode("utf-8", errors="replace").splitlines()
            pem_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("# Name:"):
                    name = stripped[len("# Name:") :].strip()
                else:
                    pem_lines.append(line)
            pem_content = "\n".join(pem_lines).encode()

            key = load_pem_public_key(pem_content)
            if not isinstance(key, Ed25519PublicKey):
                log.warning("Skipping non-Ed25519 key", path=str(pub_file))
                continue

            fingerprint = compute_key_fingerprint(key)
            result[fingerprint] = {"name": name, "path": pub_file, "key": key}
            if log.is_trace_enabled():
                log.trace("Loaded trusted key", fingerprint=fingerprint[:16], name=name)
        except Exception as exc:
            log.warning("Failed to load key file", path=str(pub_file), error=str(exc))

    return result


def load_trusted_keys(*, include_system: bool = True) -> dict[str, dict[str, Any]]:
    """Load all trusted keys from user and (optionally) system stores."""
    keys: dict[str, dict[str, Any]] = {}

    if include_system:
        system_keys_dir = get_system_config_dir() / "trusted-keys"
        keys.update(_load_keys_from_dir(system_keys_dir))

    user_keys_dir = get_trusted_keys_dir(system=False)
    keys.update(_load_keys_from_dir(user_keys_dir))

    return keys


def is_key_trusted(fingerprint: str, *, include_system: bool = True) -> bool | None:
    """Check whether a key fingerprint is in the trusted store.

    Returns:
        True  — fingerprint found in store
        False — store exists but fingerprint not found
        None  — no store directories exist (no-op / backwards-compat mode)
    """
    user_keys_dir = get_trusted_keys_dir(system=False)
    system_keys_dir = get_system_config_dir() / "trusted-keys"

    store_exists = user_keys_dir.is_dir() or (include_system and system_keys_dir.is_dir())
    if not store_exists:
        return None

    keys = load_trusted_keys(include_system=include_system)
    return fingerprint in keys


# 🌶️📦🔚
