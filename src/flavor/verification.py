#
# flavor/verification.py
#
"""Package verification for PSPF/2025 bundles."""

from pathlib import Path
from pyvider.telemetry import logger
from flavor.psp.format_2025 import PSPFReader


class FlavorVerifier:
    """Verifies PSPF/2025 packages only."""
    
    @classmethod
    def verify_package(cls, package_path: Path) -> dict:
        """
        Verify a PSPF/2025 package.
        
        Returns:
            dict: Verification results
        """
        reader = PSPFReader(package_path)
        
        # Verify magic
        if not reader.verify_magic():
            raise ValueError("Not a valid PSPF/2025 bundle")
        
        # Read and verify index
        index = reader.read_index()
        
        if not reader.verify_index():
            raise ValueError("Index checksum verification failed")
        
        # Read metadata
        metadata = reader.read_metadata()
        
        # Verify ephemeral signature
        signature_valid = reader.verify_signature()
        
        # Read slot table
        slots = reader.read_slot_table()
        
        return {
            "format": "PSPF/2025",
            "version": f"0x{index.format_version:08x}",
            "launcher_size": index.launcher_size,
            "signature_valid": signature_valid,
            "slot_count": index.slot_count,
            "package": metadata.get("package", {}),
            "slots": [
                {"index": i, "name": slot.name, "size": slot.size}
                for i, slot in enumerate(slots)
            ]
        }


# 🔍 📦 ✅