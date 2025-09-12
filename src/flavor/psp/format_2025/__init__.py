"""
PSPF 2025 Format Implementation

Progressive Secure Package Format (2025 Edition)
"""

from flavor.psp.format_2025.builder import PSPFBuilder, build_package
from flavor.config.defaults import (
    DEFAULT_HEADER_SIZE,
    DEFAULT_MAGIC_TRAILER_SIZE,
    DEFAULT_SLOT_ALIGNMENT,
    DEFAULT_SLOT_DESCRIPTOR_SIZE,
    PSPF_VERSION,
    TRAILER_END_MAGIC,
    TRAILER_START_MAGIC,
)
from provide.foundation.crypto import generate_key_pair, sign_data, verify_signature
from flavor.psp.format_2025.executor import BundleExecutor
from flavor.psp.format_2025.index import PSPFIndex
from flavor.psp.format_2025.keys import create_key_config, resolve_keys
from flavor.psp.format_2025.launcher import PSPFLauncher
from flavor.psp.format_2025.reader import PSPFReader
from flavor.psp.format_2025.slots import SlotMetadata
from flavor.utils.alignment import align_offset
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
    "KeyConfig",
    "PSPFBuilder",
    # Core Classes
    "PSPFIndex",
    "PSPFLauncher",
    "PSPFReader",
    "PreparedSlot",
    "SlotMetadata",
    "align_offset",
    "build_package",
    "create_key_config",
    # Functions
    "generate_key_pair",
    "resolve_keys",
    "sign_data",
    "validate_complete",
    "validate_spec",
    "verify_signature",
]
