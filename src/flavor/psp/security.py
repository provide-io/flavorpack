#!/usr/bin/env python3
"""
PSP Security - Integrity verification and cryptographic operations.

This module provides security-related functionality for PSP packages,
including integrity verification, signature validation, and tamper detection.
"""

import zlib
from pathlib import Path

from provide.foundation import logger
from provide.foundation.crypto.signatures import verify_signature

from flavor.psp.protocols import IntegrityResult, IntegrityVerifierProtocol
from flavor.psp.format_2025.reader import PSPFReader


class PSPFIntegrityVerifier:
    """
    PSPF package integrity verifier implementation.
    
    Provides comprehensive verification including signatures, checksums,
    and tamper detection using the Protocol pattern.
    """
    
    def __init__(self) -> None:
        """Initialize the verifier."""
        pass
    
    def verify_integrity(self, bundle_path: Path) -> IntegrityResult:
        """
        Verify the integrity of a PSPF package bundle.
        
        Args:
            bundle_path: Path to the package bundle file
            
        Returns:
            IntegrityResult dictionary with verification status
        """
        logger.debug(f"🔐 Verifying package integrity: {bundle_path}")
        
        try:
            # Open bundle for reading
            with PSPFReader(bundle_path) as reader:
                # Read index and metadata
                index = reader.read_index()
                metadata = reader.read_metadata()
                
                # Initialize verification state
                signature_valid = True
                tamper_detected = False
                
                # Verify signature if present
                if hasattr(index, 'integrity_signature') and hasattr(index, 'public_key'):
                    if (index.integrity_signature and 
                        index.public_key and
                        index.integrity_signature != b"\x00" * 64 and
                        index.public_key != b"\x00" * 32):
                        
                        # Create data to verify (metadata + slot table)
                        metadata_bytes = reader._read_metadata_bytes()
                        slot_table_bytes = reader._read_slot_table_bytes()
                        data_to_verify = metadata_bytes + slot_table_bytes
                        
                        # Verify Ed25519 signature
                        try:
                            signature_valid = verify_signature(
                                data_to_verify,
                                index.integrity_signature,
                                index.public_key
                            )
                            logger.debug(f"🔐 Signature validation result: {signature_valid}")
                        except Exception as e:
                            logger.error(f"❌ Signature verification error: {e}")
                            signature_valid = False
                            tamper_detected = True
                    else:
                        # Missing or null signatures
                        logger.debug("🔐 No valid signatures found")
                        signature_valid = False
                else:
                    # No signature fields in index
                    logger.debug("🔐 Index missing signature fields")
                    signature_valid = False
                
                # Verify slot checksums
                try:
                    slots_data = reader.read_slot_table()
                    for slot_info in slots_data:
                        slot_id = slot_info.get('id', f"slot_{slot_info.get('index', '?')}")
                        
                        # Read slot data and verify checksum
                        if 'checksum' in slot_info and slot_info['checksum']:
                            try:
                                slot_data = reader.read_slot_data(slot_info['index'])
                                calculated_checksum = zlib.adler32(slot_data) & 0xFFFFFFFF
                                expected_checksum = slot_info['checksum']
                                
                                if calculated_checksum != expected_checksum:
                                    logger.error(
                                        f"🗣️ Slot {slot_info['index']} checksum mismatch: "
                                        f"expected {expected_checksum:08x}, got {calculated_checksum:08x}"
                                    )
                                    tamper_detected = True
                                    signature_valid = False
                                else:
                                    logger.debug(f"🔐 Slot {slot_id} checksum valid")
                            except Exception as e:
                                logger.error(f"❌ Slot {slot_id} checksum verification error: {e}")
                                tamper_detected = True
                                signature_valid = False
                                
                except Exception as e:
                    logger.error(f"❌ Slot table verification error: {e}")
                    tamper_detected = True
                    signature_valid = False
                
                # Overall validity
                valid = signature_valid and not tamper_detected and metadata is not None
                
                result: IntegrityResult = {
                    "valid": valid,
                    "signature_valid": signature_valid,
                    "tamper_detected": tamper_detected
                }
                
                logger.debug(f"🔐 Integrity verification complete: {result}")
                return result
                
        except Exception as e:
            logger.error(f"❌ Integrity verification failed: {e}")
            return {
                "valid": False,
                "signature_valid": False, 
                "tamper_detected": True
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