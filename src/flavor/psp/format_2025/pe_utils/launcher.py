#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Launcher type detection and processing utilities.

Provides utilities for detecting launcher types and processing them for PSPF compatibility.
"""

from provide.foundation import logger

from .dos_stub import expand_dos_stub
from .validation import get_pe_header_offset, is_pe_executable, needs_dos_stub_expansion


def get_launcher_type(launcher_data: bytes) -> str:
    """
    Detect launcher type from PE characteristics.

    Go and Rust compilers produce PE files with different characteristics:
    - Go: Minimal DOS stub (PE offset 0x80 / 128 bytes)
    - Rust: Larger DOS stub (PE offset 0xE8 / 232 bytes or more)

    Args:
        launcher_data: Launcher binary data

    Returns:
        "go", "rust", or "unknown"
    """
    if not is_pe_executable(launcher_data):
        return "unknown"

    pe_offset = get_pe_header_offset(launcher_data)
    if pe_offset is None:
        return "unknown"

    # Go binaries have PE offset 0x80, Rust has 0xE8 or larger
    if pe_offset == 0x80:
        logger.debug("Detected Go launcher", pe_offset=f"0x{pe_offset:x}")
        return "go"
    elif pe_offset >= 0xE8:
        logger.debug("Detected Rust launcher", pe_offset=f"0x{pe_offset:x}")
        return "rust"
    else:
        logger.debug("Unknown launcher type", pe_offset=f"0x{pe_offset:x}")
        return "unknown"


def process_launcher_for_pspf(launcher_data: bytes) -> bytes:
    """
    Process launcher binary for PSPF embedding compatibility.

    This is the main entry point for PE manipulation. It uses a hybrid approach:
    - Go launchers: Use PE overlay (no modifications, PSPF appended after sections)
    - Rust launchers: Use DOS stub expansion (PSPF at fixed 0xF0 offset)

    Phase 29: Go binaries are fundamentally incompatible with DOS stub expansion
    due to their PE structure (15 sections, unusual section names, missing data
    directories). The PE overlay approach is the industry standard and preserves
    100% PE structure integrity.

    Args:
        launcher_data: Original launcher binary

    Returns:
        Processed launcher binary (expanded if Rust, unchanged if Go/Unix)
    """
    if not is_pe_executable(launcher_data):
        # Not a Windows PE executable, return unchanged (Unix binary)
        logger.trace("Launcher is not a PE executable, no processing needed")
        return launcher_data

    launcher_type = get_launcher_type(launcher_data)

    if launcher_type == "go":
        # Go launcher: Use PE overlay approach (zero modifications)
        # PSPF data will be appended after all PE sections
        logger.info("Using PE overlay approach for Go launcher (no PE modifications)")
        return launcher_data
    elif launcher_type == "rust":
        # Rust launcher: Use DOS stub expansion (PSPF at fixed 0xF0 offset)
        if needs_dos_stub_expansion(launcher_data):
            logger.info("Expanding DOS stub for Rust launcher (PSPF at 0xF0)")
            return expand_dos_stub(launcher_data)
        else:
            logger.trace("Rust launcher already has adequate DOS stub")
            return launcher_data
    else:
        # Unknown launcher type: Safe default is no modification (PE overlay)
        logger.info("Unknown launcher type, using PE overlay approach")
        return launcher_data
