#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PSP Protocol Definitions - Type-safe interfaces for PSP operations.

Defines protocols for common PSP operations that can be implemented by different
format versions (PSPF/2025, future formats, etc.)."""

from pathlib import Path
from typing import Protocol, TypedDict


class IntegrityResult(TypedDict):  # pragma: no cover
    """Result of package integrity verification."""

    valid: bool
    signature_valid: bool
    tamper_detected: bool


class IntegrityVerifierProtocol(Protocol):
    """Protocol for package integrity verification.

    Any class that implements this protocol can verify package integrity,
    regardless of the underlying format implementation.
    """

    def verify_integrity(self, bundle_path: Path) -> IntegrityResult:  # pragma: no cover
        """Verify the integrity of a package bundle.

        Args:
            bundle_path: Path to the package bundle file

        Returns:
            IntegrityResult dictionary with verification status
        """
        ...


class ExtractorProtocol(Protocol):
    """Protocol for package slot extraction."""

    def extract_slot(  # pragma: no cover
        self, slot_index: int, dest_dir: Path, *, verify_checksum: bool = True
    ) -> Path:
        """Extract a specific slot to a directory.

        Args:
            slot_index: Index of the slot to extract
            dest_dir: Destination directory for extraction
            verify_checksum: Whether to verify checksums during extraction

        Returns:
            Path to the extracted content
        """
        ...


# 🌶️📦🔚
