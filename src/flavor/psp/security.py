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
        pass

    def verify_integrity(self, bundle_path: Path) -> IntegrityResult:  # noqa: C901
        """
        Verify the integrity of a PSPF package bundle.

        Args:
            bundle_path: Path to the package bundle file

        Returns:
            IntegrityResult dictionary with verification status
        """
        logger.debug(f"🔐 Verifying package integrity: {bundle_path}")

        # Get current validation level
        validation_level = get_validation_level()

        # Skip all validation if level is NONE
        if validation_level == ValidationLevel.NONE:
            logger.warning("⚠️ VALIDATION DISABLED: Skipping integrity verification")
            return {
                "valid": True,
                "signature_valid": True,
                "tamper_detected": False,
            }

        try:
            # Open bundle for reading
            with PSPFReader(bundle_path) as reader:
                # Read index and metadata
                index = reader.read_index()
                metadata = reader.read_metadata()

                # Initialize verification state
                signature_valid = True
                tamper_detected = False

                # Skip signature verification for relaxed/minimal levels
                if validation_level in (
                    ValidationLevel.RELAXED,
                    ValidationLevel.MINIMAL,
                ):
                    logger.debug("🔐 Skipping signature verification due to validation level")
                    signature_valid = True
                else:
                    # Verify signature if present
                    if hasattr(index, "integrity_signature") and hasattr(index, "public_key"):
                        if (
                            index.integrity_signature
                            and index.public_key
                            and index.integrity_signature != b"\x00" * 512
                            and index.public_key != b"\x00" * 32
                        ):
                            # Get the original metadata JSON that was signed during building
                            # Read compressed metadata from file
                            assert reader._backend is not None
                            metadata_compressed = reader._backend.read_at(
                                index.metadata_offset, index.metadata_size
                            )

                            # Convert to bytes if memoryview
                            if isinstance(metadata_compressed, memoryview):
                                metadata_compressed = bytes(metadata_compressed)

                            # Decompress to get the original JSON that was signed
                            import gzip

                            metadata_json = gzip.decompress(metadata_compressed)

                            # Verify Ed25519 signature
                            try:
                                # Extract first 64 bytes for Ed25519 signature
                                ed25519_signature = index.integrity_signature[:64]

                                verifier = Ed25519Verifier(index.public_key)
                                signature_valid = verifier.verify(metadata_json, ed25519_signature)
                                logger.debug(f"🔐 Signature validation result: {signature_valid}")

                            except Exception as e:
                                # Handle signature validation failure based on level
                                signature_valid = False
                                if validation_level == ValidationLevel.STRICT:
                                    logger.error(f"❌ Signature verification error: {e}")
                                    tamper_detected = True
                                    raise
                                elif validation_level == ValidationLevel.STANDARD:
                                    logger.warning(f"⚠️ Signature verification error: {e}")
                                    logger.warning(
                                        "🚨 SECURITY WARNING: Package integrity verification failed"
                                    )
                                    logger.warning("🚨 Package may be corrupted or tampered with")
                                    logger.warning(
                                        "🚨 Continuing with standard validation (use FLAVOR_VALIDATION=strict to enforce)"
                                    )
                                else:
                                    logger.warning(f"⚠️ Signature verification error: {e}")
                                    logger.warning("⚠️ Continuing due to validation level")
                        else:
                            # Missing or null signatures
                            if validation_level == ValidationLevel.STRICT:
                                logger.error("🔐 No valid signatures found - package unsigned")
                                signature_valid = False
                            else:
                                logger.debug("🔐 No valid signatures found")
                                signature_valid = False
                    else:
                        # No signature fields in index
                        if validation_level == ValidationLevel.STRICT:
                            logger.error("🔐 Index missing signature fields")
                            signature_valid = False
                        else:
                            logger.debug("🔐 Index missing signature fields")
                            signature_valid = False

                # Verify slot checksums (skip for minimal level)
                if validation_level != ValidationLevel.MINIMAL:
                    try:
                        slot_descriptors = reader.read_slot_descriptors()
                        for i, descriptor in enumerate(slot_descriptors):
                            slot_id = descriptor.name or f"slot_{i}"

                            # Verify slot integrity using reader's built-in method
                            try:
                                is_valid = reader.verify_slot_integrity(i)
                                if not is_valid:
                                    if validation_level == ValidationLevel.STRICT:
                                        logger.error(f"❌ Slot {i} integrity check failed - package corrupted")
                                        tamper_detected = True
                                        signature_valid = False
                                    elif validation_level == ValidationLevel.STANDARD:
                                        logger.warning(f"🚨 SECURITY WARNING: Slot {i} integrity check failed")
                                        logger.warning("🚨 Slot may be corrupted or tampered with")
                                        logger.warning(
                                            "🚨 Continuing with standard validation (use FLAVOR_VALIDATION=strict to enforce)"
                                        )
                                        # Don't set tamper_detected for standard level
                                    else:  # RELAXED
                                        logger.warning(f"⚠️ Slot {i} integrity check failed")
                                        logger.warning("⚠️ Continuing due to relaxed validation")
                                else:
                                    logger.debug(f"🔐 Slot {slot_id} integrity valid")
                            except Exception as e:
                                if validation_level == ValidationLevel.STRICT:
                                    logger.error(f"❌ Slot {slot_id} integrity check error: {e}")
                                    tamper_detected = True
                                    signature_valid = False
                                else:
                                    logger.warning(f"⚠️ Slot {slot_id} integrity check error: {e}")
                                    logger.warning("⚠️ Continuing due to validation level")

                    except Exception as e:
                        if validation_level == ValidationLevel.STRICT:
                            logger.error(f"❌ Slot verification error: {e}")
                            tamper_detected = True
                            signature_valid = False
                        else:
                            logger.warning(f"⚠️ Slot verification error: {e}")
                            logger.warning("⚠️ Continuing due to validation level")
                else:
                    logger.debug("🔐 Skipping slot verification due to minimal validation level")

                # Overall validity depends on validation level
                if validation_level == ValidationLevel.STRICT:
                    # Strict: must have valid signature and no tampering
                    valid = signature_valid and not tamper_detected and metadata is not None
                    if not valid:
                        logger.error("❌ Package integrity verification failed under strict validation")
                elif validation_level in (
                    ValidationLevel.STANDARD,
                    ValidationLevel.RELAXED,
                ):
                    # Standard/Relaxed: metadata must be readable, warnings for other issues
                    valid = metadata is not None
                    if not signature_valid or tamper_detected:
                        logger.debug("🔐 Package has integrity issues but continuing due to validation level")
                else:  # MINIMAL
                    # Minimal: only check if we can read metadata
                    valid = metadata is not None

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
                return {
                    "valid": False,
                    "signature_valid": False,
                    "tamper_detected": True,
                }
            else:
                logger.warning(f"⚠️ Integrity verification error: {e}")
                logger.warning("⚠️ Continuing due to validation level")
                return {
                    "valid": True,
                    "signature_valid": False,
                    "tamper_detected": False,
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
