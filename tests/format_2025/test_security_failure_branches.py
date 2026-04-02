#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Failure-branch coverage for PSPFIntegrityVerifier.verify_integrity.

Exercises the error/tamper branches via mocked PSPFReader internals:
unsigned bundles, missing signature fields, slot integrity failures,
and outer exception handlers across all ValidationLevel values.
"""

from __future__ import annotations

import gzip
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from flavor.psp.security import PSPFIntegrityVerifier, ValidationLevel


@pytest.mark.unit
class TestVerifyIntegrityFailureBranches:
    """Cover the error/tamper branches in verify_integrity."""

    def _verifier(self) -> PSPFIntegrityVerifier:
        return PSPFIntegrityVerifier()

    def _make_unsigned_index(self) -> MagicMock:
        """Index with null (all-zero) signature and public key."""
        idx = MagicMock()
        idx.integrity_signature = b"\x00" * 512
        idx.public_key = b"\x00" * 32
        idx.metadata_offset = 0
        idx.metadata_size = 10
        idx.slot_count = 0
        idx.slot_table_offset = 0
        return idx

    def _make_no_sig_fields_index(self) -> MagicMock:
        """Index without integrity_signature / public_key attributes at all."""
        idx = MagicMock(spec=["metadata_offset", "metadata_size", "slot_count", "slot_table_offset"])
        idx.metadata_offset = 0
        idx.metadata_size = 10
        idx.slot_count = 0
        idx.slot_table_offset = 0
        return idx

    def test_unsigned_bundle_standard_not_tampered(self, mock_test_package: Path) -> None:
        """Unsigned bundle (zero sig) with STANDARD → valid=True, signature_valid=False."""
        verifier = self._verifier()
        unsigned_idx = self._make_unsigned_index()

        with (
            patch("flavor.psp.security.get_validation_level", return_value=ValidationLevel.STANDARD),
            patch("flavor.psp.security.PSPFReader") as mock_reader_cls,
        ):
            mock_reader = MagicMock()
            mock_reader.__enter__ = MagicMock(return_value=mock_reader)
            mock_reader.__exit__ = MagicMock(return_value=False)
            mock_reader.read_index.return_value = unsigned_idx
            mock_reader.read_metadata.return_value = {"format": "PSPF/2025"}
            mock_reader.read_slot_descriptors.return_value = []
            mock_reader_cls.return_value = mock_reader

            result = verifier.verify_integrity(mock_test_package)

        assert result["signature_valid"] is False
        assert result["tamper_detected"] is False  # STANDARD doesn't set tamper_detected
        assert result["valid"] is True  # STANDARD only needs readable metadata

    def test_unsigned_bundle_strict_not_tampered(self, mock_test_package: Path) -> None:
        """Unsigned bundle (zero sig) with STRICT → signature_valid=False, valid=False."""
        verifier = self._verifier()
        unsigned_idx = self._make_unsigned_index()

        with (
            patch("flavor.psp.security.get_validation_level", return_value=ValidationLevel.STRICT),
            patch("flavor.psp.security.PSPFReader") as mock_reader_cls,
        ):
            mock_reader = MagicMock()
            mock_reader.__enter__ = MagicMock(return_value=mock_reader)
            mock_reader.__exit__ = MagicMock(return_value=False)
            mock_reader.read_index.return_value = unsigned_idx
            mock_reader.read_metadata.return_value = {"format": "PSPF/2025"}
            mock_reader.read_slot_descriptors.return_value = []
            mock_reader_cls.return_value = mock_reader

            result = verifier.verify_integrity(mock_test_package)

        assert result["signature_valid"] is False
        assert result["valid"] is False  # STRICT: valid = signature_valid AND ...

    def test_no_sig_fields_in_index_standard(self, mock_test_package: Path) -> None:
        """Index without integrity_signature attr → no_sig_fields branch, STANDARD."""
        verifier = self._verifier()
        bare_idx = self._make_no_sig_fields_index()

        with (
            patch("flavor.psp.security.get_validation_level", return_value=ValidationLevel.STANDARD),
            patch("flavor.psp.security.PSPFReader") as mock_reader_cls,
        ):
            mock_reader = MagicMock()
            mock_reader.__enter__ = MagicMock(return_value=mock_reader)
            mock_reader.__exit__ = MagicMock(return_value=False)
            mock_reader.read_index.return_value = bare_idx
            mock_reader.read_metadata.return_value = {"format": "PSPF/2025"}
            mock_reader.read_slot_descriptors.return_value = []
            mock_reader_cls.return_value = mock_reader

            result = verifier.verify_integrity(mock_test_package)

        assert result["signature_valid"] is False

    def test_no_sig_fields_in_index_strict(self, mock_test_package: Path) -> None:
        """Index without signature fields → strict branch logs error, valid=False."""
        verifier = self._verifier()
        bare_idx = self._make_no_sig_fields_index()

        with (
            patch("flavor.psp.security.get_validation_level", return_value=ValidationLevel.STRICT),
            patch("flavor.psp.security.PSPFReader") as mock_reader_cls,
        ):
            mock_reader = MagicMock()
            mock_reader.__enter__ = MagicMock(return_value=mock_reader)
            mock_reader.__exit__ = MagicMock(return_value=False)
            mock_reader.read_index.return_value = bare_idx
            mock_reader.read_metadata.return_value = {"format": "PSPF/2025"}
            mock_reader.read_slot_descriptors.return_value = []
            mock_reader_cls.return_value = mock_reader

            result = verifier.verify_integrity(mock_test_package)

        assert result["signature_valid"] is False
        assert result["valid"] is False  # STRICT: invalid sig → valid=False

    def _make_signed_index(self) -> MagicMock:
        """Index with non-zero signature that will fail verification."""
        idx = MagicMock()
        idx.integrity_signature = b"\xde\xad\xbe\xef" + b"\x00" * 508
        idx.public_key = b"\x01" * 32
        idx.metadata_offset = 0
        idx.metadata_size = 10
        idx.slot_count = 0
        idx.slot_table_offset = 0
        return idx

    def test_signature_exception_standard(self, mock_test_package: Path) -> None:
        """Ed25519Verifier raising on STANDARD → warns, continues, valid=True."""
        verifier = self._verifier()
        signed_idx = self._make_signed_index()
        compressed_meta = gzip.compress(b'{"format":"PSPF/2025"}')

        with (
            patch("flavor.psp.security.get_validation_level", return_value=ValidationLevel.STANDARD),
            patch("flavor.psp.security.PSPFReader") as mock_reader_cls,
            patch("flavor.psp.security.Ed25519Verifier") as mock_verifier_cls,
        ):
            mock_ed = MagicMock()
            mock_ed.verify.side_effect = RuntimeError("key format error")
            mock_verifier_cls.return_value = mock_ed

            mock_reader = MagicMock()
            mock_reader.__enter__ = MagicMock(return_value=mock_reader)
            mock_reader.__exit__ = MagicMock(return_value=False)
            mock_reader.read_index.return_value = signed_idx
            mock_reader.read_metadata.return_value = {"format": "PSPF/2025"}
            mock_reader.read_slot_descriptors.return_value = []
            mock_reader._backend = MagicMock()
            mock_reader._backend.read_at.return_value = compressed_meta
            mock_reader_cls.return_value = mock_reader

            result = verifier.verify_integrity(mock_test_package)

        # STANDARD: signature exception → warns, valid=True (metadata readable)
        assert result["signature_valid"] is False
        assert result["tamper_detected"] is False
        assert result["valid"] is True

    def test_signature_exception_strict_raises_internally(self, mock_test_package: Path) -> None:
        """Ed25519Verifier raising on STRICT → outer except catches → tamper_detected=True."""
        verifier = self._verifier()
        signed_idx = self._make_signed_index()
        compressed_meta = gzip.compress(b'{"format":"PSPF/2025"}')

        with (
            patch("flavor.psp.security.get_validation_level", return_value=ValidationLevel.STRICT),
            patch("flavor.psp.security.PSPFReader") as mock_reader_cls,
            patch("flavor.psp.security.Ed25519Verifier") as mock_verifier_cls,
        ):
            mock_ed = MagicMock()
            mock_ed.verify.side_effect = RuntimeError("key format error")
            mock_verifier_cls.return_value = mock_ed

            mock_reader = MagicMock()
            mock_reader.__enter__ = MagicMock(return_value=mock_reader)
            mock_reader.__exit__ = MagicMock(return_value=False)
            mock_reader.read_index.return_value = signed_idx
            mock_reader.read_metadata.return_value = {"format": "PSPF/2025"}
            mock_reader.read_slot_descriptors.return_value = []
            mock_reader._backend = MagicMock()
            mock_reader._backend.read_at.return_value = compressed_meta
            mock_reader_cls.return_value = mock_reader

            result = verifier.verify_integrity(mock_test_package)

        # STRICT: raises inside except → re-raise → outer except catches → tamper_detected
        assert result["tamper_detected"] is True
        assert result["valid"] is False

    def _slot_descriptor(self, name: str = "slot_0") -> MagicMock:
        d = MagicMock()
        d.name = name
        return d

    def test_slot_integrity_fails_strict(self, mock_test_package: Path) -> None:
        """Slot checksum failure on STRICT → tamper_detected=True."""
        verifier = self._verifier()
        unsigned_idx = self._make_unsigned_index()

        with (
            patch("flavor.psp.security.get_validation_level", return_value=ValidationLevel.STRICT),
            patch("flavor.psp.security.PSPFReader") as mock_reader_cls,
        ):
            mock_reader = MagicMock()
            mock_reader.__enter__ = MagicMock(return_value=mock_reader)
            mock_reader.__exit__ = MagicMock(return_value=False)
            mock_reader.read_index.return_value = unsigned_idx
            mock_reader.read_metadata.return_value = {"format": "PSPF/2025"}
            mock_reader.read_slot_descriptors.return_value = [self._slot_descriptor()]
            mock_reader.verify_slot_integrity.return_value = False
            mock_reader_cls.return_value = mock_reader

            result = verifier.verify_integrity(mock_test_package)

        assert result["tamper_detected"] is True
        assert result["signature_valid"] is False
        assert result["valid"] is False  # STRICT: tamper_detected → valid=False

    def test_slot_integrity_fails_standard(self, mock_test_package: Path) -> None:
        """Slot checksum failure on STANDARD → warns, tamper_detected stays False."""
        verifier = self._verifier()
        unsigned_idx = self._make_unsigned_index()

        with (
            patch("flavor.psp.security.get_validation_level", return_value=ValidationLevel.STANDARD),
            patch("flavor.psp.security.PSPFReader") as mock_reader_cls,
        ):
            mock_reader = MagicMock()
            mock_reader.__enter__ = MagicMock(return_value=mock_reader)
            mock_reader.__exit__ = MagicMock(return_value=False)
            mock_reader.read_index.return_value = unsigned_idx
            mock_reader.read_metadata.return_value = {"format": "PSPF/2025"}
            mock_reader.read_slot_descriptors.return_value = [self._slot_descriptor()]
            mock_reader.verify_slot_integrity.return_value = False
            mock_reader_cls.return_value = mock_reader

            result = verifier.verify_integrity(mock_test_package)

        assert result["tamper_detected"] is False
        assert result["valid"] is True  # STANDARD still valid if metadata readable

    def test_slot_integrity_fails_relaxed(self, mock_test_package: Path) -> None:
        """Slot checksum failure on RELAXED → warns, continues."""
        verifier = self._verifier()
        unsigned_idx = self._make_unsigned_index()

        with (
            patch("flavor.psp.security.get_validation_level", return_value=ValidationLevel.RELAXED),
            patch("flavor.psp.security.PSPFReader") as mock_reader_cls,
        ):
            mock_reader = MagicMock()
            mock_reader.__enter__ = MagicMock(return_value=mock_reader)
            mock_reader.__exit__ = MagicMock(return_value=False)
            mock_reader.read_index.return_value = unsigned_idx
            mock_reader.read_metadata.return_value = {"format": "PSPF/2025"}
            mock_reader.read_slot_descriptors.return_value = [self._slot_descriptor()]
            mock_reader.verify_slot_integrity.return_value = False
            mock_reader_cls.return_value = mock_reader

            result = verifier.verify_integrity(mock_test_package)

        assert result["valid"] is True

    def test_slot_integrity_raises_strict(self, mock_test_package: Path) -> None:
        """verify_slot_integrity raising on STRICT → tamper_detected."""
        verifier = self._verifier()
        unsigned_idx = self._make_unsigned_index()

        with (
            patch("flavor.psp.security.get_validation_level", return_value=ValidationLevel.STRICT),
            patch("flavor.psp.security.PSPFReader") as mock_reader_cls,
        ):
            mock_reader = MagicMock()
            mock_reader.__enter__ = MagicMock(return_value=mock_reader)
            mock_reader.__exit__ = MagicMock(return_value=False)
            mock_reader.read_index.return_value = unsigned_idx
            mock_reader.read_metadata.return_value = {"format": "PSPF/2025"}
            mock_reader.read_slot_descriptors.return_value = [self._slot_descriptor()]
            mock_reader.verify_slot_integrity.side_effect = RuntimeError("checksum error")
            mock_reader_cls.return_value = mock_reader

            result = verifier.verify_integrity(mock_test_package)

        assert result["tamper_detected"] is True

    def test_slot_integrity_raises_standard(self, mock_test_package: Path) -> None:
        """verify_slot_integrity raising on STANDARD → warns, continues."""
        verifier = self._verifier()
        unsigned_idx = self._make_unsigned_index()

        with (
            patch("flavor.psp.security.get_validation_level", return_value=ValidationLevel.STANDARD),
            patch("flavor.psp.security.PSPFReader") as mock_reader_cls,
        ):
            mock_reader = MagicMock()
            mock_reader.__enter__ = MagicMock(return_value=mock_reader)
            mock_reader.__exit__ = MagicMock(return_value=False)
            mock_reader.read_index.return_value = unsigned_idx
            mock_reader.read_metadata.return_value = {"format": "PSPF/2025"}
            mock_reader.read_slot_descriptors.return_value = [self._slot_descriptor()]
            mock_reader.verify_slot_integrity.side_effect = RuntimeError("io error")
            mock_reader_cls.return_value = mock_reader

            result = verifier.verify_integrity(mock_test_package)

        assert result["tamper_detected"] is False

    def test_read_slot_descriptors_raises_strict(self, mock_test_package: Path) -> None:
        """read_slot_descriptors raising on STRICT → tamper_detected."""
        verifier = self._verifier()
        unsigned_idx = self._make_unsigned_index()

        with (
            patch("flavor.psp.security.get_validation_level", return_value=ValidationLevel.STRICT),
            patch("flavor.psp.security.PSPFReader") as mock_reader_cls,
        ):
            mock_reader = MagicMock()
            mock_reader.__enter__ = MagicMock(return_value=mock_reader)
            mock_reader.__exit__ = MagicMock(return_value=False)
            mock_reader.read_index.return_value = unsigned_idx
            mock_reader.read_metadata.return_value = {"format": "PSPF/2025"}
            mock_reader.read_slot_descriptors.side_effect = RuntimeError("corrupted slot table")
            mock_reader_cls.return_value = mock_reader

            result = verifier.verify_integrity(mock_test_package)

        assert result["tamper_detected"] is True
        assert result["valid"] is False

    def test_read_slot_descriptors_raises_standard(self, mock_test_package: Path) -> None:
        """read_slot_descriptors raising on STANDARD → warns, valid=True."""
        verifier = self._verifier()
        unsigned_idx = self._make_unsigned_index()

        with (
            patch("flavor.psp.security.get_validation_level", return_value=ValidationLevel.STANDARD),
            patch("flavor.psp.security.PSPFReader") as mock_reader_cls,
        ):
            mock_reader = MagicMock()
            mock_reader.__enter__ = MagicMock(return_value=mock_reader)
            mock_reader.__exit__ = MagicMock(return_value=False)
            mock_reader.read_index.return_value = unsigned_idx
            mock_reader.read_metadata.return_value = {"format": "PSPF/2025"}
            mock_reader.read_slot_descriptors.side_effect = RuntimeError("corrupted")
            mock_reader_cls.return_value = mock_reader

            result = verifier.verify_integrity(mock_test_package)

        assert result["valid"] is True

    def test_outer_exception_strict_returns_tampered(self, mock_test_package: Path) -> None:
        """Outer exception (read_index fails) on STRICT → tamper_detected."""
        verifier = self._verifier()

        with (
            patch("flavor.psp.security.get_validation_level", return_value=ValidationLevel.STRICT),
            patch("flavor.psp.security.PSPFReader") as mock_reader_cls,
        ):
            mock_reader = MagicMock()
            mock_reader.__enter__ = MagicMock(side_effect=RuntimeError("cannot open bundle"))
            mock_reader.__exit__ = MagicMock(return_value=False)
            mock_reader_cls.return_value = mock_reader

            result = verifier.verify_integrity(mock_test_package)

        assert result["valid"] is False
        assert result["tamper_detected"] is True

    def test_outer_exception_standard_returns_invalid(self, mock_test_package: Path) -> None:
        """Outer exception on STANDARD → warns, returns valid=False, tamper=True (fail-closed)."""
        verifier = self._verifier()

        with (
            patch("flavor.psp.security.get_validation_level", return_value=ValidationLevel.STANDARD),
            patch("flavor.psp.security.PSPFReader") as mock_reader_cls,
        ):
            mock_reader = MagicMock()
            mock_reader.__enter__ = MagicMock(side_effect=RuntimeError("read error"))
            mock_reader.__exit__ = MagicMock(return_value=False)
            mock_reader_cls.return_value = mock_reader

            result = verifier.verify_integrity(mock_test_package)

        assert result["valid"] is False
        assert result["tamper_detected"] is True


# 🌶️📦🔚
