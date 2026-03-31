#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for PSPFReader.verify_attestation_policy_hash()."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from unittest import mock

import pytest

from flavor.psp.format_2025.index import PSPFIndex
from flavor.psp.format_2025.reader import PSPFReader


def _make_reader(*, policy_hash: bytes = b"\x00" * 64, metadata: dict[str, Any] | None = None) -> PSPFReader:
    """Build a PSPFReader with mocked read_index and read_metadata."""
    index = PSPFIndex.__new__(PSPFIndex)
    object.__setattr__(index, "attestation_policy_hash", policy_hash)

    reader = PSPFReader.__new__(PSPFReader)
    reader._index = index
    reader._metadata = metadata if metadata is not None else {}

    reader.read_index = mock.MagicMock(return_value=index)  # type: ignore[method-assign]
    reader.read_metadata = mock.MagicMock(return_value=reader._metadata)  # type: ignore[method-assign]
    return reader


def _policy_hash(policy: dict[str, Any]) -> bytes:
    canonical = json.dumps(policy, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest().encode("ascii")


class TestVerifyAttestationPolicyHash:
    def test_zero_field_is_noop(self) -> None:
        """Zero-filled attestation_policy_hash → no-op, no exception."""
        reader = _make_reader(policy_hash=b"\x00" * 64, metadata={})
        reader.verify_attestation_policy_hash()  # must not raise

    def test_matching_hash_passes(self) -> None:
        """Correct hash in index → passes without exception."""
        policy = {"refuse_root": True, "max_age_days": 365}
        h = _policy_hash(policy)
        reader = _make_reader(
            policy_hash=h.ljust(64, b"\x00")[:64],
            metadata={"policy": policy},
        )
        reader.verify_attestation_policy_hash()  # must not raise

    def test_mismatch_raises(self) -> None:
        """Wrong hash in index → raises ValueError."""
        policy = {"refuse_root": True}
        wrong_hash = b"a" * 64
        reader = _make_reader(
            policy_hash=wrong_hash,
            metadata={"policy": policy},
        )
        with pytest.raises(ValueError, match="attestation_policy_hash mismatch"):
            reader.verify_attestation_policy_hash()

    def test_hash_set_but_no_policy_raises(self) -> None:
        """Non-zero hash but no 'policy' key in metadata → raises ValueError."""
        policy = {"refuse_root": True}
        h = _policy_hash(policy)
        reader = _make_reader(
            policy_hash=h.ljust(64, b"\x00")[:64],
            metadata={},  # no "policy" key
        )
        with pytest.raises(ValueError, match="no 'policy' key"):
            reader.verify_attestation_policy_hash()

    def test_hash_set_but_empty_policy_raises(self) -> None:
        """Non-zero hash but empty policy dict → raises ValueError."""
        policy = {"refuse_root": True}
        h = _policy_hash(policy)
        reader = _make_reader(
            policy_hash=h.ljust(64, b"\x00")[:64],
            metadata={"policy": {}},  # empty dict is falsy
        )
        with pytest.raises(ValueError, match="no 'policy' key"):
            reader.verify_attestation_policy_hash()

    def test_canonical_json_ordering(self) -> None:
        """Hash is stable regardless of dict key insertion order."""
        policy_a = {"max_age_days": 90, "refuse_root": False, "platforms": ["linux_amd64"]}
        policy_b = {"platforms": ["linux_amd64"], "refuse_root": False, "max_age_days": 90}
        h = _policy_hash(policy_a)

        reader = _make_reader(
            policy_hash=h.ljust(64, b"\x00")[:64],
            metadata={"policy": policy_b},  # different key order, same content
        )
        reader.verify_attestation_policy_hash()  # must not raise


# 🌶️📦🔚
