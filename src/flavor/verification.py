#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Package verification for PSPF/2025 bundles."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flavor.psp.format_2025 import PSPFReader


class FlavorVerifier:
    """Verifies PSPF/2025 packages only."""

    @classmethod
    def verify_package(cls, package_path: Path) -> dict[str, Any]:
        """
        Verify a PSPF/2025 package.

        Returns:
            dict: Verification results
        """
        reader = PSPFReader(package_path)

        # Verify magic
        if not reader.verify_magic_trailer():
            raise ValueError("Not a valid PSPF/2025 bundle")

        # Read and verify index (read_index performs the check)
        index = reader.read_index()

        # Read metadata
        metadata = reader.read_metadata()

        # Verify integrity using reader's method
        integrity_result = reader.verify_integrity()
        signature_valid = integrity_result.get("signature_valid", False)

        # Extract comprehensive slot information from metadata
        slots_info = []
        if "slots" in metadata:
            for i, slot_data in enumerate(metadata["slots"]):
                slot_info = {
                    "index": i,
                    "id": slot_data.get("id", f"slot_{i}"),
                    "size": slot_data.get("size", 0),
                    "operations": slot_data.get("operations", "raw"),
                    "purpose": slot_data.get("purpose", ""),
                    "lifecycle": slot_data.get("lifecycle", ""),
                    "target": slot_data.get("target", ""),
                    "type": slot_data.get("type", ""),
                    "permissions": slot_data.get("permissions", ""),
                    "checksum": slot_data.get("checksum", ""),
                }
                # Remove empty optional fields
                slot_info = {
                    k: v for k, v in slot_info.items() if v or k in ["index", "id", "size", "operations"]
                }
                slots_info.append(slot_info)

        return {
            "format": "PSPF/2025",
            "version": f"0x{index.format_version:08x}",
            "launcher_size": index.launcher_size,
            "signature_valid": signature_valid,
            "slot_count": index.slot_count,
            "package": metadata.get("package", {}),
            "build": metadata.get("build", {}),
            "slots": slots_info,
        }


# 🌶️📦🔚
