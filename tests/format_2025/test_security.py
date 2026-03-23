#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for psp.security using real signed PSPF bundles.

Uses mock_test_package (a real signed bundle built with PSPFBuilder + Ed25519 keys)
to exercise signature verification, slot integrity, and validation level branches.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from flavor.psp.security import (
    PSPFIntegrityVerifier,
    ValidationLevel,
    get_validation_level,
    verify_package_integrity,
)

# ---------------------------------------------------------------------------
# get_validation_level
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetValidationLevel:
    """Tests for get_validation_level() config dispatch."""

    @pytest.mark.parametrize(
        "val,expected",
        [
            ("strict", ValidationLevel.STRICT),
            ("relaxed", ValidationLevel.RELAXED),
            ("minimal", ValidationLevel.MINIMAL),
            ("standard", ValidationLevel.STANDARD),
            ("unknown", ValidationLevel.STANDARD),
        ],
    )
    def test_level_from_config(self, val: str, expected: ValidationLevel) -> None:
        """Config value maps to the correct ValidationLevel."""
        mock_cfg = MagicMock()
        mock_cfg.system.security.validation_level = val
        with patch("flavor.psp.security.get_flavor_config", return_value=mock_cfg):
            assert get_validation_level() == expected

    def test_none_level_warns_and_returns(self) -> None:
        """'none' logs warnings and returns NONE."""
        mock_cfg = MagicMock()
        mock_cfg.system.security.validation_level = "none"
        with patch("flavor.psp.security.get_flavor_config", return_value=mock_cfg):
            assert get_validation_level() == ValidationLevel.NONE


# ---------------------------------------------------------------------------
# PSPFIntegrityVerifier — using real signed bundle (mock_test_package)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestVerifyIntegrityValidBundle:
    """verify_integrity on a properly signed, untampered bundle."""

    def _verifier(self) -> PSPFIntegrityVerifier:
        return PSPFIntegrityVerifier()

    def test_none_level_skips_all_checks(self, mock_test_package: Path) -> None:
        """ValidationLevel.NONE returns valid=True without reading the bundle."""
        verifier = self._verifier()
        with patch("flavor.psp.security.get_validation_level", return_value=ValidationLevel.NONE):
            result = verifier.verify_integrity(mock_test_package)
        assert result["valid"] is True
        assert result["signature_valid"] is True
        assert result["tamper_detected"] is False

    def test_standard_level_valid_bundle_passes(self, mock_test_package: Path) -> None:
        """STANDARD validation on a real signed bundle succeeds."""
        verifier = self._verifier()
        with patch("flavor.psp.security.get_validation_level", return_value=ValidationLevel.STANDARD):
            result = verifier.verify_integrity(mock_test_package)
        assert result["valid"] is True

    def test_strict_level_valid_bundle_passes(self, mock_test_package: Path) -> None:
        """STRICT validation on a real signed bundle with correct checksums passes."""
        verifier = self._verifier()
        with patch("flavor.psp.security.get_validation_level", return_value=ValidationLevel.STRICT):
            result = verifier.verify_integrity(mock_test_package)
        assert result["valid"] is True
        assert result["signature_valid"] is True
        assert result["tamper_detected"] is False

    def test_relaxed_level_skips_signature(self, mock_test_package: Path) -> None:
        """RELAXED validation skips signature check, runs slot checks."""
        verifier = self._verifier()
        with patch("flavor.psp.security.get_validation_level", return_value=ValidationLevel.RELAXED):
            result = verifier.verify_integrity(mock_test_package)
        assert result["valid"] is True

    def test_minimal_level_skips_slot_checks(self, mock_test_package: Path) -> None:
        """MINIMAL validation reads metadata but skips both signature and slot checks."""
        verifier = self._verifier()
        with patch("flavor.psp.security.get_validation_level", return_value=ValidationLevel.MINIMAL):
            result = verifier.verify_integrity(mock_test_package)
        assert result["valid"] is True

    def test_convenience_function_delegates(self, mock_test_package: Path) -> None:
        """verify_package_integrity delegates to the module-level verifier."""
        with patch("flavor.psp.security.get_validation_level", return_value=ValidationLevel.MINIMAL):
            result = verify_package_integrity(mock_test_package)
        assert "valid" in result
        assert "signature_valid" in result
        assert "tamper_detected" in result


# 🌶️📦🔚
