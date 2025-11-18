#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""FlavorPack core package exports and helper utilities."""

from __future__ import annotations

# Foundation's setup log level is now configured via FlavorConfig
# See flavor/config.py for FLAVOR_SETUP_LOG_LEVEL environment variable
from provide.foundation.utils import get_version

from flavor.exceptions import BuildError, VerificationError
from flavor.package import (
    build_package_from_manifest,
    clean_cache,
    verify_package,
)

__version__ = get_version("flavorpack", caller_file=__file__)

__all__ = [
    "BuildError",
    "VerificationError",
    "__version__",
    "build_package_from_manifest",
    "clean_cache",
    "verify_package",
]

# 🌶️📦🔚
