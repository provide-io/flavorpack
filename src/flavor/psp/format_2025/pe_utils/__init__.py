"""Windows PE Executable Utilities for PSPF Format Compatibility.

Provides utilities for manipulating Windows PE (Portable Executable) files
to ensure compatibility with PSPF format when data is appended after the executable.
"""

from flavor.psp.format_2025.pe_utils.dos_stub import expand_dos_stub
from flavor.psp.format_2025.pe_utils.launcher import (
    get_launcher_type,
    process_launcher_for_pspf,
)
from flavor.psp.format_2025.pe_utils.validation import (
    get_pe_header_offset,
    is_pe_executable,
    needs_dos_stub_expansion,
)

__all__ = [
    "expand_dos_stub",
    "get_launcher_type",
    "get_pe_header_offset",
    "is_pe_executable",
    "needs_dos_stub_expansion",
    "process_launcher_for_pspf",
]
