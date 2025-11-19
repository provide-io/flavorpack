#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Comprehensive tests for flavor.verification module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from flavor.verification import FlavorVerifier


class TestFlavorVerifier:
    """Test suite for FlavorVerifier class."""

    def test_verify_package_success(self, tmp_path: Path) -> None:
        """Test successful package verification."""
        package_path = tmp_path / "test.psp"
        package_path.touch()

        # Mock PSPFReader to simulate a valid package
        with patch("flavor.verification.PSPFReader") as mock_reader_class:
            mock_reader = Mock()
            mock_reader_class.return_value = mock_reader

            # Mock successful verification
            mock_reader.verify_magic_trailer.return_value = True
            mock_reader.read_index.return_value = Mock(
                format_version=0x20250001, launcher_size=1024 * 100, slot_count=2
            )
            mock_reader.read_metadata.return_value = {
                "package": {"name": "test-pkg", "version": "1.0.0"},
                "build": {"timestamp": "2025-10-21"},
                "slots": [
                    {
                        "id": "runtime",
                        "size": 5000,
                        "operations": "tar+gzip",
                        "purpose": "runtime",
                        "lifecycle": "persistent",
                        "target": "/opt/runtime",
                        "type": "directory",
                        "permissions": "0755",
                        "checksum": "sha256:abc123",
                    },
                    {
                        "id": "app",
                        "size": 3000,
                        "operations": "tar+gzip",
                        "purpose": "application",
                        "lifecycle": "ephemeral",
                        "target": "/opt/app",
                        "type": "directory",
                        "permissions": "0755",
                        "checksum": "sha256:def456",
                    },
                ],
            }
            mock_reader.verify_integrity.return_value = {"signature_valid": True}

            # Verify package
            result = FlavorVerifier.verify_package(package_path)

            # Assertions
            assert result["format"] == "PSPF/2025"
            assert result["version"] == "0x20250001"
            assert result["launcher_size"] == 1024 * 100
            assert result["signature_valid"] is True
            assert result["slot_count"] == 2
            assert result["package"]["name"] == "test-pkg"
            assert result["package"]["version"] == "1.0.0"
            assert result["build"]["timestamp"] == "2025-10-21"
            assert len(result["slots"]) == 2

            # Verify slot information
            slot_0 = result["slots"][0]
            assert slot_0["index"] == 0
            assert slot_0["id"] == "runtime"
            assert slot_0["size"] == 5000
            assert slot_0["operations"] == "tar+gzip"
            assert slot_0["purpose"] == "runtime"
            assert slot_0["lifecycle"] == "persistent"
            assert slot_0["target"] == "/opt/runtime"
            assert slot_0["type"] == "directory"
            assert slot_0["permissions"] == "0755"
            assert slot_0["checksum"] == "sha256:abc123"

            slot_1 = result["slots"][1]
            assert slot_1["index"] == 1
            assert slot_1["id"] == "app"

            # Verify reader was called correctly
            mock_reader.verify_magic_trailer.assert_called_once()
            mock_reader.read_index.assert_called_once()
            mock_reader.read_metadata.assert_called_once()
            mock_reader.verify_integrity.assert_called_once()

    def test_verify_package_invalid_magic(self, tmp_path: Path) -> None:
        """Test verification failure with invalid magic bytes."""
        package_path = tmp_path / "invalid.psp"
        package_path.touch()

        with patch("flavor.verification.PSPFReader") as mock_reader_class:
            mock_reader = Mock()
            mock_reader_class.return_value = mock_reader
            mock_reader.verify_magic_trailer.return_value = False

            # Should raise ValueError for invalid magic
            with pytest.raises(ValueError, match="Not a valid PSPF/2025 bundle"):
                FlavorVerifier.verify_package(package_path)

            mock_reader.verify_magic_trailer.assert_called_once()
            # Other methods should not be called after magic verification fails
            mock_reader.read_index.assert_not_called()

    def test_verify_package_signature_invalid(self, tmp_path: Path) -> None:
        """Test verification with invalid signature."""
        package_path = tmp_path / "unsigned.psp"
        package_path.touch()

        with patch("flavor.verification.PSPFReader") as mock_reader_class:
            mock_reader = Mock()
            mock_reader_class.return_value = mock_reader

            mock_reader.verify_magic_trailer.return_value = True
            mock_reader.read_index.return_value = Mock(
                format_version=0x20250001, launcher_size=1024, slot_count=0
            )
            mock_reader.read_metadata.return_value = {
                "package": {},
                "build": {},
            }
            mock_reader.verify_integrity.return_value = {"signature_valid": False}

            result = FlavorVerifier.verify_package(package_path)

            assert result["signature_valid"] is False

    def test_verify_package_no_signature(self, tmp_path: Path) -> None:
        """Test verification when signature data is missing."""
        package_path = tmp_path / "no_sig.psp"
        package_path.touch()

        with patch("flavor.verification.PSPFReader") as mock_reader_class:
            mock_reader = Mock()
            mock_reader_class.return_value = mock_reader

            mock_reader.verify_magic_trailer.return_value = True
            mock_reader.read_index.return_value = Mock(
                format_version=0x20250001, launcher_size=1024, slot_count=0
            )
            mock_reader.read_metadata.return_value = {"package": {}, "build": {}}
            # Return empty dict (no signature_valid key)
            mock_reader.verify_integrity.return_value = {}

            result = FlavorVerifier.verify_package(package_path)

            # Should default to False when key is missing
            assert result["signature_valid"] is False

    def test_verify_package_with_minimal_metadata(self, tmp_path: Path) -> None:
        """Test verification with minimal metadata (no slots)."""
        package_path = tmp_path / "minimal.psp"
        package_path.touch()

        with patch("flavor.verification.PSPFReader") as mock_reader_class:
            mock_reader = Mock()
            mock_reader_class.return_value = mock_reader

            mock_reader.verify_magic_trailer.return_value = True
            mock_reader.read_index.return_value = Mock(
                format_version=0x20250001, launcher_size=2048, slot_count=0
            )
            # Metadata without slots
            mock_reader.read_metadata.return_value = {
                "package": {"name": "minimal"},
                "build": {},
            }
            mock_reader.verify_integrity.return_value = {"signature_valid": True}

            result = FlavorVerifier.verify_package(package_path)

            assert result["format"] == "PSPF/2025"
            assert result["slot_count"] == 0
            assert result["slots"] == []
            assert result["package"]["name"] == "minimal"

    def test_verify_package_slot_info_filtering(self, tmp_path: Path) -> None:
        """Test that empty optional slot fields are filtered out."""
        package_path = tmp_path / "test.psp"
        package_path.touch()

        with patch("flavor.verification.PSPFReader") as mock_reader_class:
            mock_reader = Mock()
            mock_reader_class.return_value = mock_reader

            mock_reader.verify_magic_trailer.return_value = True
            mock_reader.read_index.return_value = Mock(
                format_version=0x20250001, launcher_size=1024, slot_count=1
            )
            # Slot with some empty fields
            mock_reader.read_metadata.return_value = {
                "package": {},
                "build": {},
                "slots": [
                    {
                        "id": "test",
                        "size": 1000,
                        "codec": "raw",
                        "purpose": "",  # Empty - should be filtered
                        "lifecycle": "",  # Empty - should be filtered
                        "target": "/opt",
                        "type": "",  # Empty - should be filtered
                        "permissions": "",  # Empty - should be filtered
                        "checksum": "sha256:test",
                    }
                ],
            }
            mock_reader.verify_integrity.return_value = {"signature_valid": True}

            result = FlavorVerifier.verify_package(package_path)

            slot = result["slots"][0]
            # Required fields should always be present
            assert "index" in slot
            assert "id" in slot
            assert "size" in slot
            assert "operations" in slot
            # Empty optional fields should be filtered out
            assert "purpose" not in slot
            assert "lifecycle" not in slot
            assert "type" not in slot
            assert "permissions" not in slot
            # Non-empty optional fields should be present
            assert slot["target"] == "/opt"
            assert slot["checksum"] == "sha256:test"

    def test_verify_package_default_slot_values(self, tmp_path: Path) -> None:
        """Test that slots use default values when fields are missing."""
        package_path = tmp_path / "defaults.psp"
        package_path.touch()

        with patch("flavor.verification.PSPFReader") as mock_reader_class:
            mock_reader = Mock()
            mock_reader_class.return_value = mock_reader

            mock_reader.verify_magic_trailer.return_value = True
            mock_reader.read_index.return_value = Mock(
                format_version=0x20250001, launcher_size=1024, slot_count=1
            )
            # Slot missing optional fields
            mock_reader.read_metadata.return_value = {
                "package": {},
                "build": {},
                "slots": [
                    {
                        # Only required field
                        "size": 500,
                    }
                ],
            }
            mock_reader.verify_integrity.return_value = {"signature_valid": True}

            result = FlavorVerifier.verify_package(package_path)

            slot = result["slots"][0]
            assert slot["index"] == 0
            assert slot["id"] == "slot_0"  # Default when missing
            assert slot["size"] == 500
            assert slot["operations"] == "raw"  # Default when missing

    def test_verify_package_multiple_slots(self, tmp_path: Path) -> None:
        """Test verification with multiple slots."""
        package_path = tmp_path / "multi.psp"
        package_path.touch()

        with patch("flavor.verification.PSPFReader") as mock_reader_class:
            mock_reader = Mock()
            mock_reader_class.return_value = mock_reader

            mock_reader.verify_magic_trailer.return_value = True
            mock_reader.read_index.return_value = Mock(
                format_version=0x20250001, launcher_size=1024, slot_count=3
            )
            mock_reader.read_metadata.return_value = {
                "package": {},
                "build": {},
                "slots": [
                    {"id": "slot_0", "size": 100},
                    {"id": "slot_1", "size": 200},
                    {"id": "slot_2", "size": 300},
                ],
            }
            mock_reader.verify_integrity.return_value = {"signature_valid": True}

            result = FlavorVerifier.verify_package(package_path)

            assert len(result["slots"]) == 3
            assert result["slots"][0]["index"] == 0
            assert result["slots"][1]["index"] == 1
            assert result["slots"][2]["index"] == 2

    def test_verify_package_format_version_formatting(self, tmp_path: Path) -> None:
        """Test that format version is correctly formatted as hex."""
        package_path = tmp_path / "test.psp"
        package_path.touch()

        with patch("flavor.verification.PSPFReader") as mock_reader_class:
            mock_reader = Mock()
            mock_reader_class.return_value = mock_reader

            mock_reader.verify_magic_trailer.return_value = True
            mock_reader.read_index.return_value = Mock(
                format_version=0x20250001,  # Specific test value
                launcher_size=1024,
                slot_count=0,
            )
            mock_reader.read_metadata.return_value = {"package": {}, "build": {}}
            mock_reader.verify_integrity.return_value = {"signature_valid": True}

            result = FlavorVerifier.verify_package(package_path)

            # Verify hex formatting with leading 0x and 8 digits
            assert result["version"] == "0x20250001"

    def test_verify_package_reader_exception(self, tmp_path: Path) -> None:
        """Test that reader exceptions are propagated."""
        package_path = tmp_path / "corrupt.psp"
        package_path.touch()

        with patch("flavor.verification.PSPFReader") as mock_reader_class:
            mock_reader = Mock()
            mock_reader_class.return_value = mock_reader

            mock_reader.verify_magic_trailer.return_value = True
            # Simulate corruption during index read
            mock_reader.read_index.side_effect = RuntimeError("Corrupted index block")

            with pytest.raises(RuntimeError, match="Corrupted index block"):
                FlavorVerifier.verify_package(package_path)

    def test_verify_package_metadata_exception(self, tmp_path: Path) -> None:
        """Test exception during metadata reading."""
        package_path = tmp_path / "bad_meta.psp"
        package_path.touch()

        with patch("flavor.verification.PSPFReader") as mock_reader_class:
            mock_reader = Mock()
            mock_reader_class.return_value = mock_reader

            mock_reader.verify_magic_trailer.return_value = True
            mock_reader.read_index.return_value = Mock(
                format_version=0x20250001, launcher_size=1024, slot_count=0
            )
            # Simulate metadata read failure
            mock_reader.read_metadata.side_effect = ValueError("Invalid metadata JSON")

            with pytest.raises(ValueError, match="Invalid metadata JSON"):
                FlavorVerifier.verify_package(package_path)


# 🌶️📦🔚
