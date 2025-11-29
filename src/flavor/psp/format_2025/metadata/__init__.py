#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PSPF 2025 metadata assembly and creation.

Provides functions for assembling package metadata, creating build info,
launcher metadata, and verification data for PSPF packages.
"""

from .assembly import (
    assemble_metadata,
    create_build_metadata,
    create_launcher_metadata,
    create_verification_metadata,
    get_launcher_info,
)

__all__ = [
    "assemble_metadata",
    "create_build_metadata",
    "create_launcher_metadata",
    "create_verification_metadata",
    "get_launcher_info",
]

# 🌶️📦🔚
