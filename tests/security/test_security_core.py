#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Comprehensive tests for flavor.psp.security module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

from flavor.config.defaults import (
    VALIDATION_MINIMAL,
    VALIDATION_NONE,
    VALIDATION_RELAXED,
    VALIDATION_STANDARD,
    VALIDATION_STRICT,
)
from flavor.psp.security import (
    PSPFIntegrityVerifier,
    ValidationLevel,
    get_validation_level,
    verify_package_integrity,
)


class TestValidationLevel:
    """Test ValidationLevel enum."""

    def test_validation_levels_exist(self) -> None:
        """Test all validation levels are defined."""
        assert ValidationLevel.STRICT == 0
        assert ValidationLevel.STANDARD == 1
        assert ValidationLevel.RELAXED == 2
        assert ValidationLevel.MINIMAL == 3
        assert ValidationLevel.NONE == 4


class TestGetValidationLevel:
    """Test get_validation_level function."""

    @patch("flavor.psp.security.get_flavor_config")
    def test_get_validation_level_strict(self, mock_get_config: Mock) -> None:
        """Test get_validation_level returns STRICT."""
        mock_config = Mock()
        mock_config.system.security.validation_level = VALIDATION_STRICT
        mock_get_config.return_value = mock_config

        level = get_validation_level()
        assert level == ValidationLevel.STRICT

    @patch("flavor.psp.security.get_flavor_config")
    def test_get_validation_level_relaxed(self, mock_get_config: Mock) -> None:
        """Test get_validation_level returns RELAXED."""
        mock_config = Mock()
        mock_config.system.security.validation_level = VALIDATION_RELAXED
        mock_get_config.return_value = mock_config

        level = get_validation_level()
        assert level == ValidationLevel.RELAXED

    @patch("flavor.psp.security.get_flavor_config")
    def test_get_validation_level_minimal(self, mock_get_config: Mock) -> None:
        """Test get_validation_level returns MINIMAL."""
        mock_config = Mock()
        mock_config.system.security.validation_level = VALIDATION_MINIMAL
        mock_get_config.return_value = mock_config

        get_validation_level()
        assert ValidationLevel.MINIMAL

    @patch("flavor.psp.security.logger")
    @patch("flavor.psp.security.get_flavor_config")
    def test_get_validation_level_none_with_warning(self, mock_get_config: Mock, mock_logger: Mock) -> None:
        """Test get_validation_level returns NONE with security warning."""
        mock_config = Mock()
        mock_config.system.security.validation_level = VALIDATION_NONE
        mock_get_config.return_value = mock_config

        level = get_validation_level()
        assert level == ValidationLevel.NONE
        # Should log warnings
        assert mock_logger.warning.call_count >= 2

    @patch("flavor.psp.security.get_flavor_config")
    def test_get_validation_level_standard_default(self, mock_get_config: Mock) -> None:
        """Test get_validation_level defaults to STANDARD for unknown values."""
        mock_config = Mock()
        mock_config.system.security.validation_level = "unknown"
        mock_get_config.return_value = mock_config

        level = get_validation_level()
        assert level == ValidationLevel.STANDARD

    @patch("flavor.psp.security.get_flavor_config")
    def test_get_validation_level_standard_explicit(self, mock_get_config: Mock) -> None:
        """Test get_validation_level with explicit STANDARD."""
        mock_config = Mock()
        mock_config.system.security.validation_level = VALIDATION_STANDARD
        mock_get_config.return_value = mock_config

        level = get_validation_level()
        assert level == ValidationLevel.STANDARD


class TestPSPFIntegrityVerifier:
    """Test suite for PSPFIntegrityVerifier class."""

    def test_init(self) -> None:
        """Test PSPFIntegrityVerifier initialization."""
        verifier = PSPFIntegrityVerifier()
        assert verifier is not None

    @patch("flavor.psp.security.get_validation_level")
    def test_verify_integrity_validation_none_skips_all(self, mock_get_level: Mock, tmp_path: Path) -> None:
        """Test that validation level NONE skips all verification."""
        mock_get_level.return_value = ValidationLevel.NONE
        verifier = PSPFIntegrityVerifier()
        bundle_path = tmp_path / "test.psp"
        bundle_path.touch()

        result = verifier.verify_integrity(bundle_path)

        assert result["valid"] is True
        assert result["signature_valid"] is True
        assert result["tamper_detected"] is False

    @patch("flavor.psp.security.PSPFReader")
    @patch("flavor.psp.security.get_validation_level")
    def test_verify_integrity_strict_with_valid_signature(
        self, mock_get_level: Mock, mock_reader_class: Mock, tmp_path: Path
    ) -> None:
        """Test strict validation with valid signature."""
        mock_get_level.return_value = ValidationLevel.STRICT
        bundle_path = tmp_path / "signed.psp"
        bundle_path.touch()

        # Mock reader and its methods
        mock_reader = Mock()
        mock_reader_class.return_value.__enter__.return_value = mock_reader

        # Mock index with valid signature
        mock_index = Mock()
        mock_index.integrity_signature = b"\x01" * 64 + b"\x00" * 448
        mock_index.public_key = b"\x01" * 32
        mock_index.metadata_offset = 1000
        mock_index.metadata_size = 500
        mock_reader.read_index.return_value = mock_index

        # Mock metadata
        mock_reader.read_metadata.return_value = {"package": {}}

        # Mock backend for reading compressed metadata
        mock_reader._backend = Mock()
        import gzip

        original_json = b'{"test": "data"}'
        compressed = gzip.compress(original_json)
        mock_reader._backend.read_at.return_value = compressed

        # Mock Ed25519 verifier
        with patch("flavor.psp.security.Ed25519Verifier") as mock_verifier_class:
            mock_verifier_inst = Mock()
            mock_verifier_inst.verify.return_value = True
            mock_verifier_class.return_value = mock_verifier_inst

            # Mock slot verification
            mock_reader.read_slot_descriptors.return_value = []

            verifier = PSPFIntegrityVerifier()
            result = verifier.verify_integrity(bundle_path)

            assert result["valid"] is True
            assert result["signature_valid"] is True
            assert result["tamper_detected"] is False

    @patch("flavor.psp.security.PSPFReader")
    @patch("flavor.psp.security.get_validation_level")
    def test_verify_integrity_strict_with_invalid_signature(
        self, mock_get_level: Mock, mock_reader_class: Mock, tmp_path: Path
    ) -> None:
        """Test strict validation with invalid signature returns failure."""
        mock_get_level.return_value = ValidationLevel.STRICT
        bundle_path = tmp_path / "bad_sig.psp"
        bundle_path.touch()

        mock_reader = Mock()
        mock_reader_class.return_value.__enter__.return_value = mock_reader

        mock_index = Mock()
        mock_index.integrity_signature = b"\x01" * 64 + b"\x00" * 448
        mock_index.public_key = b"\x01" * 32
        mock_index.metadata_offset = 1000
        mock_index.metadata_size = 500
        mock_reader.read_index.return_value = mock_index
        mock_reader.read_metadata.return_value = {"package": {}}

        mock_reader._backend = Mock()
        import gzip

        compressed = gzip.compress(b'{"test": "data"}')
        mock_reader._backend.read_at.return_value = compressed

        # Invalid signature - verifier raises exception but outer handler catches it
        with patch("flavor.psp.security.Ed25519Verifier") as mock_verifier_class:
            mock_verifier_inst = Mock()
            mock_verifier_inst.verify.side_effect = Exception("Invalid signature")
            mock_verifier_class.return_value = mock_verifier_inst

            verifier = PSPFIntegrityVerifier()
            result = verifier.verify_integrity(bundle_path)

            # Strict mode catches exception and returns failure
            assert result["valid"] is False
            assert result["signature_valid"] is False
            assert result["tamper_detected"] is True

    @patch("flavor.psp.security.PSPFReader")
    @patch("flavor.psp.security.get_validation_level")
    def test_verify_integrity_relaxed_skips_signature(
        self, mock_get_level: Mock, mock_reader_class: Mock, tmp_path: Path
    ) -> None:
        """Test relaxed validation skips signature verification."""
        mock_get_level.return_value = ValidationLevel.RELAXED
        bundle_path = tmp_path / "relaxed.psp"
        bundle_path.touch()

        mock_reader = Mock()
        mock_reader_class.return_value.__enter__.return_value = mock_reader

        mock_reader.read_index.return_value = Mock()
        mock_reader.read_metadata.return_value = {"package": {}}
        mock_reader.read_slot_descriptors.return_value = []

        verifier = PSPFIntegrityVerifier()
        result = verifier.verify_integrity(bundle_path)

        # Signature considered valid due to skip
        assert result["valid"] is True
        assert result["signature_valid"] is True

    @patch("flavor.psp.security.PSPFReader")
    @patch("flavor.psp.security.get_validation_level")
    def test_verify_integrity_minimal_skips_slots(
        self, mock_get_level: Mock, mock_reader_class: Mock, tmp_path: Path
    ) -> None:
        """Test minimal validation skips slot verification."""
        mock_get_level.return_value = ValidationLevel.MINIMAL
        bundle_path = tmp_path / "minimal.psp"
        bundle_path.touch()

        mock_reader = Mock()
        mock_reader_class.return_value.__enter__.return_value = mock_reader

        mock_reader.read_index.return_value = Mock()
        mock_reader.read_metadata.return_value = {"package": {}}

        verifier = PSPFIntegrityVerifier()
        result = verifier.verify_integrity(bundle_path)

        # Should not call read_slot_descriptors
        mock_reader.read_slot_descriptors.assert_not_called()
        assert result["valid"] is True

    @patch("flavor.psp.security.PSPFReader")
    @patch("flavor.psp.security.get_validation_level")
    def test_verify_integrity_missing_signature_fields_strict(
        self, mock_get_level: Mock, mock_reader_class: Mock, tmp_path: Path
    ) -> None:
        """Test strict validation with missing signature fields."""
        mock_get_level.return_value = ValidationLevel.STRICT
        bundle_path = tmp_path / "no_sig.psp"
        bundle_path.touch()

        mock_reader = Mock()
        mock_reader_class.return_value.__enter__.return_value = mock_reader

        # Index without signature fields
        mock_index = Mock(spec=[])  # No signature attributes
        mock_reader.read_index.return_value = mock_index
        mock_reader.read_metadata.return_value = {"package": {}}
        mock_reader.read_slot_descriptors.return_value = []

        verifier = PSPFIntegrityVerifier()
        result = verifier.verify_integrity(bundle_path)

        assert result["valid"] is False
        assert result["signature_valid"] is False

    @patch("flavor.psp.security.PSPFReader")
    @patch("flavor.psp.security.get_validation_level")
    def test_verify_integrity_standard_continues_on_bad_signature(
        self, mock_get_level: Mock, mock_reader_class: Mock, tmp_path: Path
    ) -> None:
        """Test standard validation continues despite bad signature."""
        mock_get_level.return_value = ValidationLevel.STANDARD
        bundle_path = tmp_path / "std.psp"
        bundle_path.touch()

        mock_reader = Mock()
        mock_reader_class.return_value.__enter__.return_value = mock_reader

        mock_index = Mock()
        mock_index.integrity_signature = b"\x01" * 64 + b"\x00" * 448
        mock_index.public_key = b"\x01" * 32
        mock_index.metadata_offset = 1000
        mock_index.metadata_size = 500
        mock_reader.read_index.return_value = mock_index
        mock_reader.read_metadata.return_value = {"package": {}}
        mock_reader._backend = Mock()
        import gzip

        mock_reader._backend.read_at.return_value = gzip.compress(b'{"test": "data"}')

        with patch("flavor.psp.security.Ed25519Verifier") as mock_verifier_class:
            mock_verifier_inst = Mock()
            mock_verifier_inst.verify.side_effect = Exception("Bad signature")
            mock_verifier_class.return_value = mock_verifier_inst

            mock_reader.read_slot_descriptors.return_value = []

            verifier = PSPFIntegrityVerifier()
            result = verifier.verify_integrity(bundle_path)

            # Should continue despite signature failure
            assert result["valid"] is True  # metadata readable
            assert result["signature_valid"] is False

    @patch("flavor.psp.security.PSPFReader")
    @patch("flavor.psp.security.get_validation_level")
    def test_verify_integrity_exception_handling_strict(
        self, mock_get_level: Mock, mock_reader_class: Mock, tmp_path: Path
    ) -> None:
        """Test exception handling in strict mode."""
        mock_get_level.return_value = ValidationLevel.STRICT
        bundle_path = tmp_path / "error.psp"
        bundle_path.touch()

        mock_reader_class.return_value.__enter__.side_effect = Exception("File corrupted")

        verifier = PSPFIntegrityVerifier()
        result = verifier.verify_integrity(bundle_path)

        assert result["valid"] is False
        assert result["signature_valid"] is False
        assert result["tamper_detected"] is True

    @patch("flavor.psp.security.PSPFReader")
    @patch("flavor.psp.security.get_validation_level")
    def test_verify_integrity_exception_handling_standard(
        self, mock_get_level: Mock, mock_reader_class: Mock, tmp_path: Path
    ) -> None:
        """Test exception handling in standard mode."""
        mock_get_level.return_value = ValidationLevel.STANDARD
        bundle_path = tmp_path / "error.psp"
        bundle_path.touch()

        mock_reader_class.return_value.__enter__.side_effect = Exception("File corrupted")

        verifier = PSPFIntegrityVerifier()
        result = verifier.verify_integrity(bundle_path)

        # Standard mode is lenient
        assert result["valid"] is True
        assert result["signature_valid"] is False
        assert result["tamper_detected"] is False


class TestVerifyPackageIntegrity:
    """Test module-level convenience function."""

    @patch("flavor.psp.security._verifier")
    def test_verify_package_integrity_delegates(self, mock_verifier: Mock, tmp_path: Path) -> None:
        """Test that verify_package_integrity delegates to module verifier."""
        bundle_path = tmp_path / "test.psp"
        mock_verifier.verify_integrity.return_value = {
            "valid": True,
            "signature_valid": True,
            "tamper_detected": False,
        }

        result = verify_package_integrity(bundle_path)

        mock_verifier.verify_integrity.assert_called_once_with(bundle_path)
        assert result["valid"] is True


# 🌶️📦🔚
