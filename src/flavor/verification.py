#
# flavor/verification.py
#
"""Package verification for PSPF/2025 bundles."""

from pathlib import Path

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

        # Read and verify index (read_index performs the check)
        index = reader.read_index()

        # Read metadata
        metadata = reader.read_metadata()

        # Verify integrity using reader's method
        integrity_result = reader.verify_integrity()
        signature_valid = integrity_result.get("signature_valid", False)

        # Extract slot information from metadata
        slots_info = []
        if "slots" in metadata:
            for i, slot_data in enumerate(metadata["slots"]):
                slots_info.append(
                    {
                        "index": i,
                        "name": slot_data.get("name", "unknown"),
                        "size": slot_data.get("size", 0),
                    }
                )

        return {
            "format": "PSPF/2025",
            "version": f"0x{index.format_version:08x}",
            "launcher_size": index.launcher_size,
            "signature_valid": signature_valid,
            "slot_count": index.slot_count,
            "package": metadata.get("package", {}),
            "slots": slots_info,
        }


# 🔍 📦 ✅
