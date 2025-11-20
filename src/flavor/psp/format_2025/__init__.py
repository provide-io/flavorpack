#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PSPF 2025 Format Implementation

Progressive Secure Package Format (2025 Edition)"""

from provide.foundation.crypto import (
    Ed25519Signer,
    Ed25519Verifier,
    generate_ed25519_keypair,
)

from flavor.psp.format_2025.builder import build_package
from flavor.psp.format_2025.constants import (
    DEFAULT_HEADER_SIZE,
    DEFAULT_MAGIC_TRAILER_SIZE,
    DEFAULT_SLOT_ALIGNMENT,
    DEFAULT_SLOT_DESCRIPTOR_SIZE,
    PSPF_VERSION,
    TRAILER_END_MAGIC,
    TRAILER_START_MAGIC,
)
from flavor.psp.format_2025.executor import BundleExecutor
from flavor.psp.format_2025.index import PSPFIndex
from flavor.psp.format_2025.keys import create_key_config, resolve_keys
from flavor.psp.format_2025.launcher import PSPFLauncher
from flavor.psp.format_2025.pspf_builder import PSPFBuilder
from flavor.psp.format_2025.reader import PSPFReader
from flavor.psp.format_2025.slots import SlotMetadata
from flavor.psp.format_2025.spec import (
    BuildOptions,
    BuildResult,
    BuildSpec,
    KeyConfig,
    PreparedSlot,
)
from flavor.psp.format_2025.validation import validate_complete, validate_spec

__all__ = [
    # Constants
    "DEFAULT_HEADER_SIZE",
    "DEFAULT_MAGIC_TRAILER_SIZE",
    "DEFAULT_SLOT_ALIGNMENT",
    "DEFAULT_SLOT_DESCRIPTOR_SIZE",
    "PSPF_VERSION",
    "TRAILER_END_MAGIC",
    "TRAILER_START_MAGIC",
    "BuildOptions",
    "BuildResult",
    # Spec Classes
    "BuildSpec",
    "BundleExecutor",
    # Crypto Classes
    "Ed25519Signer",
    "Ed25519Verifier",
    "KeyConfig",
    "PSPFBuilder",
    # Core Classes
    "PSPFIndex",
    "PSPFLauncher",
    "PSPFReader",
    "PreparedSlot",
    "SlotMetadata",
    "build_package",
    "create_key_config",
    # Functions
    "generate_ed25519_keypair",
    "resolve_keys",
    "validate_complete",
    "validate_spec",
]

# 🌶️📦🔚
