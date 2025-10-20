# flavor/packaging/__init__.py
#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# flavor/packaging/__init__.py
#
"""
This package contains the core logic for packaging and
verification of Progressive Secure Provider Format (Flavor) packages.
"""

# Public API for the packaging module
from flavor.packaging.keys import generate_key_pair
from flavor.packaging.orchestrator import PackagingOrchestrator

__all__ = [
    "PackagingOrchestrator",
    "generate_key_pair",
]
# 🗂️ 🖱️ 🔨
# 🌶️📦📦🪄
