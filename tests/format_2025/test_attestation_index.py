# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for attestation fields in the PSPFIndex block."""

from flavor.psp.format_2025.index import PSPFIndex


def test_attestation_fields_default_to_zero() -> None:
    """New PSPFIndex has zero-filled attestation fields."""
    idx = PSPFIndex()
    assert idx.attestation_key_fp == b"\x00" * 64
    assert idx.attestation_sbom_digest == b"\x00" * 64
    assert idx.attestation_policy_hash == b"\x00" * 64


def test_attestation_round_trip() -> None:
    """Attestation fields survive pack/unpack unchanged."""
    idx = PSPFIndex()
    idx.attestation_key_fp = b"a" * 64
    idx.attestation_sbom_digest = b"b" * 64
    idx.attestation_policy_hash = b"c" * 64

    packed = idx.pack()
    assert len(packed) == 8192

    idx2 = PSPFIndex.unpack(packed)
    assert idx2.attestation_key_fp == b"a" * 64
    assert idx2.attestation_sbom_digest == b"b" * 64
    assert idx2.attestation_policy_hash == b"c" * 64


def test_reserved_region_shrunk_correctly() -> None:
    """Reserved region is now 6624 bytes (6816 - 192)."""
    idx = PSPFIndex()
    assert len(idx.reserved) == 6624


def test_total_pack_size_unchanged() -> None:
    """Packed index is still exactly 8192 bytes."""
    idx = PSPFIndex()
    assert len(idx.pack()) == 8192


def test_zero_attestation_fields_in_packed_bytes() -> None:
    """Default index has zeros in attestation region."""
    idx = PSPFIndex()
    packed = idx.pack()
    # Attestation region starts at 8192 - 6816 = 1376
    attestation_region = packed[1376 : 1376 + 192]
    assert attestation_region == b"\x00" * 192
