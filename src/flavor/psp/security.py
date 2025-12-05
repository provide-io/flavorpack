#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PSP Security - Integrity verification and cryptographic operations.

This module provides security-related functionality for PSP packages,
including integrity verification, signature validation, and tamper detection."""

from enum import IntEnum
from pathlib import Path

from provide.foundation import logger
from provide.foundation.crypto import Ed25519Verifier

from flavor.config import get_flavor_config
from flavor.config.defaults import (
    VALIDATION_MINIMAL,
    VALIDATION_NONE,
    VALIDATION_RELAXED,
    VALIDATION_STRICT,
)
from flavor.psp.format_2025.reader import PSPFReader
from flavor.psp.protocols import IntegrityResult


class ValidationLevel(IntEnum):
    """Validation levels matching Go/Rust implementations."""

    STRICT = 0  # Full security, fail on any issue
    STANDARD = 1  # Normal validation, warn on minor issues
    RELAXED = 2  # Skip signatures, warn on checksums
    MINIMAL = 3  # Critical checks only
    NONE = 4  # Skip all (testing only)


def get_validation_level() -> ValidationLevel:
    """
    Get validation level from Foundation config, matching Go/Rust behavior.

    Returns:
        ValidationLevel: The current validation level
    """
    # Get validation level from Foundation config system
    config = get_flavor_config()
    val = config.system.security.validation_level.lower()

    if val == VALIDATION_STRICT:
        return ValidationLevel.STRICT
    elif val == VALIDATION_RELAXED:
        return ValidationLevel.RELAXED
    elif val == VALIDATION_MINIMAL:
        return ValidationLevel.MINIMAL
    elif val == VALIDATION_NONE:
        logger.warning("⚠️ SECURITY WARNING: Validation disabled (FLAVOR_VALIDATION=none)")
        logger.warning("⚠️ This is NOT RECOMMENDED for production use")
        return ValidationLevel.NONE
    else:  # VALIDATION_STANDARD or unknown
        return ValidationLevel.STANDARD


class PSPFIntegrityVerifier:
    """
    PSPF package integrity verifier implementation.

    Provides comprehensive verification including signatures, checksums,
    and tamper detection using the Protocol pattern.
    """

    def __init__(self) -> None:
        """Initialize the verifier."""

    def _has_valid_signature_fields(self, index: object) -> bool:
        """Check if index has valid signature fields populated."""
        if not (hasattr(index, "integrity_signature") and hasattr(index, "public_key")):
            return False
        return bool(
            index.integrity_signature
            and index.public_key
            and index.integrity_signature != b"\x00" * 512
            and index.public_key != b"\x00" * 32
        )

    def _verify_signature(
        self, reader: PSPFReader, index: object, validation_level: ValidationLevel
    ) -> tuple[bool, bool]:
        """Verify package signature. Returns (signature_valid, tamper_detected)."""
        import gzip

        if not self._has_valid_signature_fields(index):
            if validation_level == ValidationLevel.STRICT:
                logger.error("🔐 No valid signatures found - package unsigned")
            else:
                logger.debug("🔐 No valid signatures found")
            return False, False

        # Read and decompress metadata for signature verification
        assert reader._backend is not None
        metadata_compressed = reader._backend.read_at(index.metadata_offset, index.metadata_size)
        if isinstance(metadata_compressed, memoryview):
            metadata_compressed = bytes(metadata_compressed)
        metadata_json = gzip.decompress(metadata_compressed)

        try:
            ed25519_signature = index.integrity_signature[:64]
            verifier = Ed25519Verifier(index.public_key)
            signature_valid = verifier.verify(metadata_json, ed25519_signature)
            logger.debug(f"🔐 Signature validation result: {signature_valid}")
            return signature_valid, False
        except Exception as e:
            return self._handle_signature_error(e, validation_level)

    def _handle_signature_error(
        self, error: Exception, validation_level: ValidationLevel
    ) -> tuple[bool, bool]:
        """Handle signature verification error based on validation level."""
        if validation_level == ValidationLevel.STRICT:
            logger.error(f"❌ Signature verification error: {error}")
            raise
        if validation_level == ValidationLevel.STANDARD:
            logger.warning(f"⚠️ Signature verification error: {error}")
            logger.warning("🚨 SECURITY WARNING: Package integrity verification failed")
            logger.warning("🚨 Package may be corrupted or tampered with")
            logger.warning("🚨 Continuing with standard validation (use FLAVOR_VALIDATION=strict to enforce)")
        else:
            logger.warning(f"⚠️ Signature verification error: {error}")
            logger.warning("⚠️ Continuing due to validation level")
        return False, False

    def _verify_slot(
        self, reader: PSPFReader, slot_index: int, slot_id: str, validation_level: ValidationLevel
    ) -> tuple[bool, bool]:
        """Verify a single slot. Returns (signature_valid_update, tamper_detected)."""
        try:
            is_valid = reader.verify_slot_integrity(slot_index)
            if is_valid:
                logger.debug(f"🔐 Slot {slot_id} integrity valid")
                return True, False
            return self._handle_slot_failure(slot_index, validation_level)
        except Exception as e:
            return self._handle_slot_error(slot_id, e, validation_level)

    def _handle_slot_failure(self, slot_index: int, validation_level: ValidationLevel) -> tuple[bool, bool]:
        """Handle slot verification failure based on validation level."""
        if validation_level == ValidationLevel.STRICT:
            logger.error(f"❌ Slot {slot_index} integrity check failed - package corrupted")
            return False, True
        if validation_level == ValidationLevel.STANDARD:
            logger.warning(f"🚨 SECURITY WARNING: Slot {slot_index} integrity check failed")
            logger.warning("🚨 Slot may be corrupted or tampered with")
            logger.warning("🚨 Continuing with standard validation (use FLAVOR_VALIDATION=strict to enforce)")
        else:
            logger.warning(f"⚠️ Slot {slot_index} integrity check failed")
            logger.warning("⚠️ Continuing due to relaxed validation")
        return True, False

    def _handle_slot_error(
        self, slot_id: str, error: Exception, validation_level: ValidationLevel
    ) -> tuple[bool, bool]:
        """Handle slot verification error based on validation level."""
        if validation_level == ValidationLevel.STRICT:
            logger.error(f"❌ Slot {slot_id} integrity check error: {error}")
            return False, True
        logger.warning(f"⚠️ Slot {slot_id} integrity check error: {error}")
        logger.warning("⚠️ Continuing due to validation level")
        return True, False

    def _verify_all_slots(self, reader: PSPFReader, validation_level: ValidationLevel) -> tuple[bool, bool]:
        """Verify all slots. Returns (signature_valid, tamper_detected)."""
        try:
            slot_descriptors = reader.read_slot_descriptors()
            signature_valid = True
            tamper_detected = False

            for i, descriptor in enumerate(slot_descriptors):
                slot_id = descriptor.name or f"slot_{i}"
                sig_valid, tamper = self._verify_slot(reader, i, slot_id, validation_level)
                if not sig_valid:
                    signature_valid = False
                if tamper:
                    tamper_detected = True

            return signature_valid, tamper_detected
        except Exception as e:
            if validation_level == ValidationLevel.STRICT:
                logger.error(f"❌ Slot verification error: {e}")
                return False, True
            logger.warning(f"⚠️ Slot verification error: {e}")
            logger.warning("⚠️ Continuing due to validation level")
            return True, False

    def _determine_validity(
        self, validation_level: ValidationLevel, metadata: object, signature_valid: bool, tamper_detected: bool
    ) -> bool:
        """Determine overall validity based on validation level."""
        if validation_level == ValidationLevel.STRICT:
            valid = signature_valid and not tamper_detected and metadata is not None
            if not valid:
                logger.error("❌ Package integrity verification failed under strict validation")
            return valid
        if validation_level in (ValidationLevel.STANDARD, ValidationLevel.RELAXED):
            if not signature_valid or tamper_detected:
                logger.debug("🔐 Package has integrity issues but continuing due to validation level")
            return metadata is not None
        # MINIMAL: only check if we can read metadata
        return metadata is not None

    def verify_integrity(self, bundle_path: Path) -> IntegrityResult:
        """
        Verify the integrity of a PSPF package bundle.

        Args:
            bundle_path: Path to the package bundle file

        Returns:
            IntegrityResult dictionary with verification status
        """
        logger.debug(f"🔐 Verifying package integrity: {bundle_path}")
        validation_level = get_validation_level()

        if validation_level == ValidationLevel.NONE:
            logger.warning("⚠️ VALIDATION DISABLED: Skipping integrity verification")
            return {"valid": True, "signature_valid": True, "tamper_detected": False}

        try:
            with PSPFReader(bundle_path) as reader:
                index = reader.read_index()
                metadata = reader.read_metadata()

                signature_valid = True
                tamper_detected = False

                # Signature verification
                if validation_level in (ValidationLevel.RELAXED, ValidationLevel.MINIMAL):
                    logger.debug("🔐 Skipping signature verification due to validation level")
                else:
                    signature_valid, tamper_detected = self._verify_signature(reader, index, validation_level)

                # Slot verification
                if validation_level != ValidationLevel.MINIMAL:
                    slot_sig_valid, slot_tamper = self._verify_all_slots(reader, validation_level)
                    if not slot_sig_valid:
                        signature_valid = False
                    if slot_tamper:
                        tamper_detected = True
                else:
                    logger.debug("🔐 Skipping slot verification due to minimal validation level")

                valid = self._determine_validity(validation_level, metadata, signature_valid, tamper_detected)

                result: IntegrityResult = {
                    "valid": valid,
                    "signature_valid": signature_valid,
                    "tamper_detected": tamper_detected,
                }
                logger.debug(f"🔐 Integrity verification complete: {result} (level: {validation_level.name})")
                return result

        except Exception as e:
            if validation_level == ValidationLevel.STRICT:
                logger.error(f"❌ Integrity verification failed: {e}")
                return {"valid": False, "signature_valid": False, "tamper_detected": True}
            logger.warning(f"⚠️ Integrity verification error: {e}")
            logger.warning("⚠️ Continuing due to validation level")
            return {"valid": True, "signature_valid": False, "tamper_detected": False}


# Create a module-level verifier instance for convenience
_verifier = PSPFIntegrityVerifier()


def verify_package_integrity(bundle_path: Path) -> IntegrityResult:
    """
    Convenience function to verify package integrity.

    Args:
        bundle_path: Path to the package bundle file

    Returns:
        IntegrityResult dictionary with verification status
    """
    return _verifier.verify_integrity(bundle_path)


# 🌶️📦🔚
