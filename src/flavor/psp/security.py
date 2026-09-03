#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PSP Security - Integrity verification and cryptographic operations.

This module provides security-related functionality for PSP packages,
including integrity verification, signature validation, and tamper detection."""

from enum import IntEnum
import gzip
from pathlib import Path
from typing import Any

from provide.foundation import logger
from provide.foundation.crypto import Ed25519Verifier

from flavor.config import get_flavor_config
from flavor.config.defaults import (
    ENV_VALIDATION,
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
        logger.warning(f"⚠️ SECURITY WARNING: Validation disabled ({ENV_VALIDATION}=none)")
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
        pass

    def _verify_signature(self, reader: PSPFReader, index: Any, level: ValidationLevel) -> tuple[bool, bool]:
        """Check the Ed25519 seal over the stored metadata.

        Returns (signature_valid, tamper_detected).

        Relaxed and minimal do not check the seal at all, so they report it
        valid rather than unknown -- the level is a statement that the caller
        does not want it checked.
        """
        if level in (ValidationLevel.RELAXED, ValidationLevel.MINIMAL):
            logger.debug("🔐 Skipping signature verification due to validation level")
            return True, False

        if not (hasattr(index, "integrity_signature") and hasattr(index, "public_key")):
            if level == ValidationLevel.STRICT:
                logger.error("🔐 Index missing signature fields")
            else:
                logger.debug("🔐 Index missing signature fields")
            return False, False

        signed = (
            index.integrity_signature
            and index.public_key
            and index.integrity_signature != b"\x00" * 512
            and index.public_key != b"\x00" * 32
        )
        if not signed:
            if level == ValidationLevel.STRICT:
                logger.error("🔐 No valid signatures found - package unsigned")
            else:
                logger.debug("🔐 No valid signatures found")
            return False, False

        try:
            # The seal covers the stored metadata bytes, so read them back
            # rather than re-serialising what was parsed from them.
            assert reader._backend is not None
            metadata_compressed = reader._backend.read_at(index.metadata_offset, index.metadata_size)
            if isinstance(metadata_compressed, memoryview):
                metadata_compressed = bytes(metadata_compressed)
            metadata_json = gzip.decompress(metadata_compressed)

            verifier = Ed25519Verifier(index.public_key)
            # Ed25519 occupies the first 64 bytes of the 512-byte field.
            signature_valid = verifier.verify(metadata_json, index.integrity_signature[:64])
            logger.debug(f"🔐 Signature validation result: {signature_valid}")
            return signature_valid, False

        except Exception as e:
            if level == ValidationLevel.STRICT:
                logger.error(f"❌ Signature verification error: {e}")
                raise
            if level == ValidationLevel.STANDARD:
                logger.warning(f"⚠️ Signature verification error: {e}")
                logger.warning("🚨 SECURITY WARNING: Package integrity verification failed")
                logger.warning("🚨 Package may be corrupted or tampered with")
                logger.warning(
                    f"🚨 Continuing with standard validation (use {ENV_VALIDATION}=strict to enforce)"
                )
            else:
                logger.warning(f"⚠️ Signature verification error: {e}")
                logger.warning("⚠️ Continuing due to validation level")
            return False, False

    def _verify_one_slot(
        self, reader: PSPFReader, index_of_slot: int, slot_id: str, level: ValidationLevel
    ) -> tuple[bool, bool]:
        """Check one slot's checksum. Returns (ok, tamper_detected)."""
        try:
            if reader.verify_slot_integrity(index_of_slot):
                logger.debug(f"🔐 Slot {slot_id} integrity valid")
                return True, False

            if level == ValidationLevel.STRICT:
                logger.error(f"❌ Slot {index_of_slot} integrity check failed - package corrupted")
                return False, True
            if level == ValidationLevel.STANDARD:
                logger.warning(f"🚨 SECURITY WARNING: Slot {index_of_slot} integrity check failed")
                logger.warning("🚨 Slot may be corrupted or tampered with")
                logger.warning(
                    f"🚨 Continuing with standard validation (use {ENV_VALIDATION}=strict to enforce)"
                )
            else:  # RELAXED
                logger.warning(f"⚠️ Slot {index_of_slot} integrity check failed")
                logger.warning("⚠️ Continuing due to relaxed validation")
            return True, False

        except Exception as e:
            if level == ValidationLevel.STRICT:
                logger.error(f"❌ Slot {slot_id} integrity check error: {e}")
                return False, True
            logger.warning(f"⚠️ Slot {slot_id} integrity check error: {e}")
            logger.warning("⚠️ Continuing due to validation level")
            return True, False

    def _verify_slots(self, reader: PSPFReader, level: ValidationLevel) -> tuple[bool, bool]:
        """Check every slot's checksum. Returns (ok, tamper_detected)."""
        if level == ValidationLevel.MINIMAL:
            logger.debug("🔐 Skipping slot verification due to minimal validation level")
            return True, False

        try:
            slot_descriptors = reader.read_slot_descriptors()
        except Exception as e:
            if level == ValidationLevel.STRICT:
                logger.error(f"❌ Slot verification error: {e}")
                return False, True
            logger.warning(f"⚠️ Slot verification error: {e}")
            logger.warning("⚠️ Continuing due to validation level")
            return True, False

        ok = True
        tamper_detected = False
        for i, descriptor in enumerate(slot_descriptors):
            slot_ok, slot_tampered = self._verify_one_slot(reader, i, descriptor.name or f"slot_{i}", level)
            ok = ok and slot_ok
            tamper_detected = tamper_detected or slot_tampered

        return ok, tamper_detected

    @staticmethod
    def _overall_validity(
        level: ValidationLevel, signature_valid: bool, tamper_detected: bool, readable: bool
    ) -> bool:
        """Decide whether the package passes, given what the level enforces.

        Only strict turns a failed signature or detected tampering into a
        failure. The other levels warn and require the metadata to be readable,
        which is the tiering the warnings above tell the operator about.
        """
        if level == ValidationLevel.STRICT:
            valid = signature_valid and not tamper_detected and readable
            if not valid:
                logger.error("❌ Package integrity verification failed under strict validation")
            return valid

        if level in (ValidationLevel.STANDARD, ValidationLevel.RELAXED):
            if not signature_valid or tamper_detected:
                logger.debug("🔐 Package has integrity issues but continuing due to validation level")
            return readable

        return readable  # MINIMAL

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
            return {
                "valid": True,
                "signature_valid": True,
                "tamper_detected": False,
            }

        try:
            with PSPFReader(bundle_path) as reader:
                index = reader.read_index()
                metadata = reader.read_metadata()

                signature_valid, tamper_detected = self._verify_signature(reader, index, validation_level)
                slots_ok, slots_tampered = self._verify_slots(reader, validation_level)

                signature_valid = signature_valid and slots_ok
                tamper_detected = tamper_detected or slots_tampered

                result: IntegrityResult = {
                    "valid": self._overall_validity(
                        validation_level, signature_valid, tamper_detected, metadata is not None
                    ),
                    "signature_valid": signature_valid,
                    "tamper_detected": tamper_detected,
                }

                logger.debug(f"🔐 Integrity verification complete: {result} (level: {validation_level.name})")
                return result

        except Exception as e:
            # A verification that could not complete is a failure at every
            # level; only how loudly it is reported differs.
            if validation_level == ValidationLevel.STRICT:
                logger.error(f"❌ Integrity verification failed: {e}")
            else:
                logger.warning(f"⚠️ Integrity verification error: {e}")
            return {
                "valid": False,
                "signature_valid": False,
                "tamper_detected": True,
            }


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
