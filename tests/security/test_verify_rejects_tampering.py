#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""The verification contract, asserted against the committed fixtures.

Mirrors `src/flavor-rs/tests/verify_rejects_tampering.rs` and the Go tests in
`launcher_cli_verify_test.go`. All three implementations must give the same
verdict on the same bytes.

The interesting case is a package where every unkeyed checksum still adds up
and only the Ed25519 seal is wrong — which is exactly what someone who can
rewrite the file produces, and what Go's `verify` used to accept.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import zlib

import pytest

from flavor.verification import FlavorVerifier

pytestmark = [
    pytest.mark.security,
    pytest.mark.adversarial,
    pytest.mark.cross_language,
    pytest.mark.ci,
]

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "format_compat" / "v1"

# Trailer layout, from the format constants: 📦 + 8192-byte index + 🪄.
MAGIC_TRAILER_SIZE = 8200
HEADER_SIZE = 8192
CHECKSUM_OFFSET = 4
SIGNATURE_OFFSET = 128


def _fixture_names() -> list[str]:
    """Names of the committed fixtures, from the file that pins them."""
    expected = json.loads((FIXTURE_DIR / "expected.json").read_text(encoding="utf-8"))
    return sorted(expected["fixtures"])


def _tamper_with_the_seal(source: Path, destination: Path) -> None:
    """Flip a signature bit, then repair the index checksum.

    Repairing the checksum is the point: without it the package would fail on
    the index instead, and the test would prove nothing about the seal.
    """
    data = bytearray(source.read_bytes())
    index_start = len(data) - MAGIC_TRAILER_SIZE + 4

    data[index_start + SIGNATURE_OFFSET] ^= 0xFF

    index = bytearray(data[index_start : index_start + HEADER_SIZE])
    index[CHECKSUM_OFFSET : CHECKSUM_OFFSET + 4] = b"\x00\x00\x00\x00"
    checksum = zlib.adler32(bytes(index)) & 0xFFFFFFFF
    data[index_start + CHECKSUM_OFFSET : index_start + CHECKSUM_OFFSET + 4] = checksum.to_bytes(4, "little")

    destination.write_bytes(bytes(data))


@pytest.fixture(params=_fixture_names())
def fixture_name(request: pytest.FixtureRequest) -> str:
    """Each committed fixture in turn."""
    return str(request.param)


def test_an_untouched_fixture_still_verifies(fixture_name: str) -> None:
    """The control: the fixtures verify before anything is done to them."""
    result = FlavorVerifier.verify_package(FIXTURE_DIR / fixture_name)

    assert result["valid"], f"{fixture_name} no longer verifies"
    assert result["signature_valid"], f"{fixture_name}: seal no longer verifies"


def test_a_tampered_seal_is_rejected(fixture_name: str, tmp_path: Path) -> None:
    """A broken signature is refused even though every checksum still matches."""
    tampered = tmp_path / fixture_name
    _tamper_with_the_seal(FIXTURE_DIR / fixture_name, tampered)

    result = FlavorVerifier.verify_package(tampered)

    assert not result["signature_valid"], (
        f"{fixture_name}: a corrupted Ed25519 signature was reported as valid"
    )
    assert not result["valid"], (
        f"{fixture_name}: a package with a broken seal was reported as verified, "
        "even though every unkeyed checksum in it still adds up"
    )
    assert result["checksums_valid"], (
        f"{fixture_name}: the tampering was supposed to leave the checksums intact, "
        "so this test is no longer isolating the signature"
    )


def test_a_truncated_package_is_rejected(fixture_name: str, tmp_path: Path) -> None:
    """Losing the trailer is refused rather than read as an unsigned package."""
    truncated = tmp_path / fixture_name
    shutil.copyfile(FIXTURE_DIR / fixture_name, truncated)
    data = truncated.read_bytes()
    truncated.write_bytes(data[: -MAGIC_TRAILER_SIZE // 2])

    with pytest.raises(Exception):  # noqa: B017 - any refusal is acceptable, silence is not
        result = FlavorVerifier.verify_package(truncated)
        assert not result["valid"], f"{fixture_name}: a truncated package verified"


# 🌶️📦🔚
