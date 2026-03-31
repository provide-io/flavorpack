#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for attestation slot assembly and digest computation."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from flavor.psp.format_2025.attestation import build_attestation, parse_attestation


def _minimal_package_info() -> dict[str, Any]:
    """Return a minimal but complete package_info dict for testing."""
    return {
        "packages": [
            {
                "name": "requests",
                "version": "2.31.0",
                "purl": "pkg:pypi/requests@2.31.0",
                "hash": "sha256:" + "ab" * 32,
                "license": "Apache-2.0",
            }
        ],
        "python_version": "3.11.12",
        "python_hash": "sha256:" + "00" * 32,
        "launcher_language": "go",
        "launcher_version": "1.24.1",
        "launcher_hash": "sha256:" + "11" * 32,
        "builder_name": "flavor-python",
        "builder_version": "0.3.21",
        "build_timestamp": 1743379200,
        "platform_os": "linux",
        "platform_arch": "amd64",
    }


def test_build_attestation_returns_bytes_and_digest() -> None:
    """build_attestation returns a (bytes, str) 2-tuple."""
    result = build_attestation(_minimal_package_info())
    assert isinstance(result, tuple)
    assert len(result) == 2
    content_bytes, hex_digest = result
    assert isinstance(content_bytes, bytes)
    assert isinstance(hex_digest, str)


def test_attestation_digest_matches_sha256_of_content() -> None:
    """The returned hex_digest is exactly sha256(content_bytes)."""
    content_bytes, hex_digest = build_attestation(_minimal_package_info())
    expected = hashlib.sha256(content_bytes).hexdigest()
    assert hex_digest == expected
    assert len(hex_digest) == 64


def test_attestation_has_sbom_key() -> None:
    """When sbom_enabled=True (default), content contains 'sbom' key."""
    content_bytes, _ = build_attestation(_minimal_package_info(), sbom_enabled=True)
    data = json.loads(content_bytes)
    assert "sbom" in data


def test_attestation_no_sbom_when_disabled() -> None:
    """When sbom_enabled=False, content has no 'sbom' key."""
    content_bytes, _ = build_attestation(_minimal_package_info(), sbom_enabled=False)
    data = json.loads(content_bytes)
    assert "sbom" not in data


def test_attestation_has_provenance_key() -> None:
    """Content always has a 'provenance' key regardless of sbom_enabled."""
    for enabled in (True, False):
        content_bytes, _ = build_attestation(_minimal_package_info(), sbom_enabled=enabled)
        data = json.loads(content_bytes)
        assert "provenance" in data


def test_attestation_with_signing_key_fingerprint() -> None:
    """signing_key_fingerprint is stored inside the provenance sub-record."""
    fp = "cd" * 32
    content_bytes, _ = build_attestation(_minimal_package_info(), signing_key_fingerprint=fp)
    data = json.loads(content_bytes)
    assert data["provenance"]["signing_key_fingerprint"] == fp


def test_parse_attestation_roundtrip() -> None:
    """parse_attestation(content_bytes) recovers the same structure as json.loads."""
    content_bytes, _ = build_attestation(_minimal_package_info())
    parsed = parse_attestation(content_bytes)
    expected = json.loads(content_bytes)
    assert parsed == expected
    assert "provenance" in parsed


def test_attestation_is_canonical_json() -> None:
    """Content bytes are compact JSON with sorted keys (no extra spaces)."""
    content_bytes, _ = build_attestation(_minimal_package_info())
    text = content_bytes.decode("utf-8")
    # Compact separators: no ", " or ": "
    assert ": " not in text
    assert ", " not in text
    # Re-serialising with the same settings must produce identical output
    data = json.loads(text)
    reserialised = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    assert content_bytes == reserialised


def test_attestation_provenance_has_builder_fields() -> None:
    """Provenance sub-record reflects builder_name and builder_version."""
    info = _minimal_package_info()
    content_bytes, _ = build_attestation(info)
    data = json.loads(content_bytes)
    prov = data["provenance"]
    assert prov["builder"] == info["builder_name"]
    assert prov["builder_version"] == info["builder_version"]


def test_attestation_provenance_platform() -> None:
    """Provenance sub-record reflects platform_os and platform_arch."""
    info = _minimal_package_info()
    content_bytes, _ = build_attestation(info)
    data = json.loads(content_bytes)
    platform = data["provenance"]["platform"]
    assert platform["os"] == info["platform_os"]
    assert platform["arch"] == info["platform_arch"]


def test_attestation_no_signing_key_defaults_to_empty_string() -> None:
    """When signing_key_fingerprint is None, provenance stores empty string."""
    content_bytes, _ = build_attestation(_minimal_package_info(), signing_key_fingerprint=None)
    data = json.loads(content_bytes)
    assert data["provenance"]["signing_key_fingerprint"] == ""


def test_attestation_empty_package_info_uses_defaults() -> None:
    """build_attestation works with a minimal/empty package_info (uses defaults)."""
    content_bytes, hex_digest = build_attestation({})
    assert isinstance(content_bytes, bytes)
    assert len(hex_digest) == 64
    data = json.loads(content_bytes)
    assert "provenance" in data
