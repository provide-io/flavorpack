# SPDX-FileCopyrightText: Copyright (c) 2026 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# tests/parity/test_lifecycle_constants.py
"""Parity test: LIFECYCLE_ATTESTATION = 11 across all three implementations."""

import pytest

from flavor.psp.format_2025.constants import (
    LIFECYCLE_ATTESTATION,
    LIFECYCLE_FROM_STRING,
    LIFECYCLE_NAMES,
)

pytestmark = [pytest.mark.cross_language, pytest.mark.ci, pytest.mark.unit]


@pytest.mark.parity
@pytest.mark.parity_category("Format Constants")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_lifecycle_attestation_value() -> None:
    """LIFECYCLE_ATTESTATION must equal 11 in all three implementations."""
    assert LIFECYCLE_ATTESTATION == 11


@pytest.mark.parity
@pytest.mark.parity_category("Format Constants")
@pytest.mark.parity_go("PASS")
@pytest.mark.parity_rust("PASS")
def test_lifecycle_attestation_in_names() -> None:
    """LIFECYCLE_NAMES must contain 11 -> 'attestation' mapping."""
    assert LIFECYCLE_NAMES[11] == "attestation"
    assert LIFECYCLE_FROM_STRING["attestation"] == 11
