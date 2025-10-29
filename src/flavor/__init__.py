#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

"""
This package contains the core logic for building and verifying the
Progressive Secure Package Format (PSPF/2025).
"""

# Set Foundation's setup log level before any imports
# This MUST happen first to control Foundation's initialization logs
import os

if "FOUNDATION_SETUP_LOG_LEVEL" not in os.environ:
    # Default to ERROR to suppress Foundation's debug/trace initialization logs
    # unless explicitly set via FOUNDATION_LOG_LEVEL
    setup_level = os.environ.get("FOUNDATION_LOG_LEVEL", "ERROR")
    os.environ["FOUNDATION_SETUP_LOG_LEVEL"] = setup_level

from provide.foundation.utils import get_version

from flavor.exceptions import BuildError, VerificationError

__version__ = get_version("flavorpack", caller_file=__file__)
from flavor.package import (
    build_package_from_manifest,
    clean_cache,
    verify_package,
)

__all__ = [
    "BuildError",
    "VerificationError",
    "__version__",
    "build_package_from_manifest",
    "clean_cache",
    "verify_package",
]
# 🌶️📦🔚
