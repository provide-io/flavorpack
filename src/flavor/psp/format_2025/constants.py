# flavor/psp/format_2025/constants.py
#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""PSPF/2025 Format Constants

All constants defined here match the authoritative specification.
These are the canonical values for the PSPF/2025 v0 format.
"""

# =================================
# Format Version and Magic
# =================================
from __future__ import annotations

PSPF_VERSION = 0x20250001  # PSPF/2025 v1 format identifier
FORMAT_VERSION_STRING = "2025.0.0"  # String version for JSON metadata

# Magic bytes for package trailer
TRAILER_START_MAGIC = bytes([0xF0, 0x9F, 0x93, 0xA6])  # 📦 emoji
# 🌶️📦📄🪄
