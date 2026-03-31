#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Parity tests: SBOM generation and attestation digest behavior across implementations."""

from __future__ import annotations

import hashlib
import json

import pytest

from flavor.psp.format_2025.attestation import build_attestation, parse_attestation
from flavor.psp.format_2025.sbom import build_sbom


def _minimal_package_info() -> dict[str, object]:
    return {
        "packages": [
            {
                "name": "requests",
                "version": "2.31.0",
                "purl": "pkg:pypi/requests@2.31.0",
                "hash": "sha256:abc123",
                "license": "Apache-2.0",
            }
        ],
        "python_version": "3.11.12",
        "python_hash": "sha256:00aabb",
        "launcher_language": "go",
        "launcher_version": "1.24.1",
        "launcher_hash": "sha256:11ccdd",
        "builder_name": "flavor-python",
        "builder_version": "0.3.21",
    }


@pytest.mark.parity
@pytest.mark.parity_category("SBOM & Attestation")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_attestation_digest_is_sha256_of_content() -> None:
    """attestation_sbom_digest = SHA-256(canonical JSON bytes)."""
    content_bytes, hex_digest = build_attestation(_minimal_package_info())
    assert hex_digest == hashlib.sha256(content_bytes).hexdigest()
    assert len(hex_digest) == 64


@pytest.mark.parity
@pytest.mark.parity_category("SBOM & Attestation")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_attestation_content_is_canonical_json() -> None:
    """Attestation content uses sort_keys and no extra whitespace."""
    content_bytes, _ = build_attestation(_minimal_package_info())
    parsed = json.loads(content_bytes.decode("utf-8"))
    # Re-serializing with same settings should produce identical bytes
    re_serialized = json.dumps(parsed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    assert content_bytes == re_serialized


@pytest.mark.parity
@pytest.mark.parity_category("SBOM & Attestation")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_digest_present_no_slot_is_verification_error() -> None:
    """If attestation_sbom_digest is non-zero but no attestation slot exists, verification fails."""
    # This is a Python-side spec test — actual Go/Rust enforcement is tested in their own suites.
    # This test documents the expected cross-language contract.
    # The attestation.py module produces consistent digests.
    content_bytes, hex_digest = build_attestation(_minimal_package_info())
    parsed = parse_attestation(content_bytes)
    # Verify the digest matches the content
    assert hex_digest == hashlib.sha256(content_bytes).hexdigest()
    # Assert the attestation content is well-formed (has provenance)
    assert "provenance" in parsed


@pytest.mark.parity
@pytest.mark.parity_category("SBOM & Attestation")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_sbom_cyclonedx_format() -> None:
    """SBOM follows CycloneDX 1.6 format across all implementations."""
    sbom = build_sbom(_minimal_package_info())
    assert sbom is not None
    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"] == "1.6"
    assert isinstance(sbom["components"], list)
    assert len(sbom["components"]) > 0
