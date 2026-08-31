#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Verify the committed cross-version format-compatibility fixtures.

These packages were built once, by an older toolchain, and are never rebuilt.
Every other test in the suite builds and verifies inside a single run, so both
sides of the comparison move together and a format change stays invisible. These
fixtures are the only thing that fails when a package built before a signing,
hashing, or layout change stops verifying after it.

See tests/fixtures/format_compat/README.md.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from flavor.psp.format_2025 import PSPFReader
from flavor.verification import FlavorVerifier

pytestmark = [
    pytest.mark.cross_language,
    pytest.mark.packaging,
    pytest.mark.security,
    pytest.mark.ci,
]

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "format_compat"
GENERATION = "v1"
FIXTURE_DIR = FIXTURE_ROOT / GENERATION


def _expected() -> dict[str, Any]:
    """Load the pinned facts for the current fixture generation."""
    pinned: dict[str, Any] = json.loads((FIXTURE_DIR / "expected.json").read_text(encoding="utf-8"))
    return pinned


EXPECTED = _expected()
FIXTURE_NAMES = sorted(EXPECTED["fixtures"])


@pytest.fixture(params=FIXTURE_NAMES)
def fixture_case(request: pytest.FixtureRequest) -> tuple[Path, dict[str, Any]]:
    """Yield each committed fixture together with the facts pinned for it."""
    name = request.param
    return FIXTURE_DIR / name, EXPECTED["fixtures"][name]


def test_fixtures_are_present() -> None:
    """Every fixture named in expected.json exists on disk."""
    assert FIXTURE_NAMES, "expected.json lists no fixtures"
    for name in FIXTURE_NAMES:
        assert (FIXTURE_DIR / name).is_file(), f"missing fixture: {name}"


def test_fixture_bytes_are_unchanged(fixture_case: tuple[Path, dict[str, Any]]) -> None:
    """The fixture is byte-identical to the one that was committed.

    Regenerating a fixture silently converts this whole file into a tautology,
    so the digest is pinned and any rebuild has to be argued for in review.
    """
    path, expected = fixture_case
    data = path.read_bytes()
    assert len(data) == expected["size"]
    assert hashlib.sha256(data).hexdigest() == expected["sha256"], (
        f"{path.name} was regenerated. That destroys the cross-version guarantee: "
        "the fixture is only evidence while it predates the code verifying it."
    )


def test_old_package_still_verifies(fixture_case: tuple[Path, dict[str, Any]]) -> None:
    """Today's Python verifier accepts a package built by an older toolchain."""
    path, _ = fixture_case
    result = FlavorVerifier.verify_package(path)

    assert result["valid"], f"{path.name} no longer verifies"
    assert result["checksums_valid"], f"{path.name}: checksums no longer match"
    assert result["signature_valid"], f"{path.name}: Ed25519 seal no longer verifies"


def test_package_identity_is_stable(fixture_case: tuple[Path, dict[str, Any]]) -> None:
    """Metadata and slot layout read back exactly as they were written."""
    path, expected = fixture_case
    result = FlavorVerifier.verify_package(path)

    assert result["format"] == "PSPF/2025"
    assert result["package"]["name"] == EXPECTED["package"]["name"]
    assert result["package"]["version"] == EXPECTED["package"]["version"]
    assert result["slot_count"] == expected["slot_count"]


def test_signing_key_material_is_stable(fixture_case: tuple[Path, dict[str, Any]]) -> None:
    """The embedded public key and its SHA-256 fingerprint are unchanged.

    Both are derived from the committed seed, so a drift here means key
    derivation or the digest behind the fingerprint has changed underneath us.
    """
    path, expected = fixture_case
    with PSPFReader(path) as reader:
        index = reader.read_index()

    assert index.public_key.hex() == expected["public_key"]
    assert index.attestation_key_fp.rstrip(b"\x00").decode("ascii") == expected["key_fingerprint"]


def test_payload_slot_round_trips(fixture_case: tuple[Path, dict[str, Any]]) -> None:
    """Slot 0 still decodes to the committed payload, byte for byte."""
    path, _ = fixture_case
    payload = (FIXTURE_DIR / "inputs" / "payload.txt").read_bytes()

    with PSPFReader(path) as reader:
        assert reader.read_slot(0) == payload


def test_every_producer_derives_the_same_key() -> None:
    """One seed produces one key across Python, Go and Rust.

    Deterministic key generation is only useful if it is deterministic across
    implementations, not merely within one.
    """
    keys = {name: EXPECTED["fixtures"][name]["public_key"] for name in FIXTURE_NAMES}
    assert len(set(keys.values())) == 1, f"producers disagree on the derived key: {keys}"


# 🌶️📦🔚
