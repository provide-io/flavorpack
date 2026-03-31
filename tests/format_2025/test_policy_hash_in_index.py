#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests that PSPFBuilder writes policy_hash when a policy is declared."""

from __future__ import annotations

import hashlib
import json

from flavor.psp.format_2025.builder import create_index
from flavor.psp.format_2025.spec import BuildSpec


def test_create_index_writes_policy_hash() -> None:
    """create_index() writes SHA-256 of canonical JSON policy to attestation_policy_hash."""
    policy_raw = {"platforms": ["linux_amd64"], "refuse_root": True, "max_age_days": 365}
    spec = BuildSpec(
        metadata={"package": {"name": "policy-test", "version": "1.0.0"}, "policy": policy_raw},
    )

    index = create_index(spec, [], b"\x00" * 32)

    canonical = json.dumps(policy_raw, sort_keys=True, separators=(",", ":"))
    expected = hashlib.sha256(canonical.encode()).hexdigest()
    actual = index.attestation_policy_hash.rstrip(b"\x00").decode("ascii")
    assert actual == expected


def test_create_index_no_policy_leaves_policy_hash_empty() -> None:
    """If no policy is declared, attestation_policy_hash stays zero-filled."""
    spec = BuildSpec(
        metadata={"package": {"name": "no-policy-test", "version": "1.0.0"}},
    )

    index = create_index(spec, [], b"\x00" * 32)

    assert index.attestation_policy_hash == b"\x00" * 64


def test_policy_hash_is_64_bytes() -> None:
    """attestation_policy_hash field is exactly 64 bytes."""
    policy_raw = {"refuse_root": True}
    spec = BuildSpec(
        metadata={"package": {"name": "size-test", "version": "0.1"}, "policy": policy_raw},
    )

    index = create_index(spec, [], b"\x00" * 32)

    assert len(index.attestation_policy_hash) == 64


def test_policy_hash_deterministic_for_same_policy() -> None:
    """Same policy dict always produces same hash (canonical JSON ordering)."""
    policy_a = {"max_age_days": 90, "refuse_root": False, "platforms": ["darwin_amd64"]}
    policy_b = {"platforms": ["darwin_amd64"], "refuse_root": False, "max_age_days": 90}

    spec_a = BuildSpec(metadata={"package": {"name": "det-a", "version": "0.1"}, "policy": policy_a})
    spec_b = BuildSpec(metadata={"package": {"name": "det-b", "version": "0.1"}, "policy": policy_b})

    index_a = create_index(spec_a, [], b"\x00" * 32)
    index_b = create_index(spec_b, [], b"\x00" * 32)

    assert index_a.attestation_policy_hash == index_b.attestation_policy_hash


# 🌶️📦🔚
