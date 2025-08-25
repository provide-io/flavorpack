"""
PSPF 2025 Format Implementation

Progressive Secure Package Format (2025 Edition)
"""

from flavor.psp.format_2025.builder import PSPFBuilder, build_package
from flavor.psp.format_2025.constants import (
    EMOJI_MAGIC_SIZE,
    INDEX_SIZE,
    MAGIC_WAND_EMOJI,
    PSPF_MAGIC,
    PSPF_VERSION,
    SLOT_ALIGNMENT,
    SLOT_DESCRIPTOR_SIZE,
)
from flavor.psp.format_2025.crypto import generate_key_pair, sign_data, verify_signature
from flavor.psp.format_2025.executor import BundleExecutor
from flavor.psp.format_2025.index import PSPFIndex
from flavor.psp.format_2025.keys import create_key_config, resolve_keys
from flavor.psp.format_2025.launcher import PSPFLauncher
from flavor.psp.format_2025.reader import PSPFReader
from flavor.psp.format_2025.slots import SlotMetadata, align_offset
from flavor.psp.format_2025.spec import (
    BuildOptions,
    BuildResult,
    BuildSpec,
    KeyConfig,
    PreparedSlot,
)
from flavor.psp.format_2025.validation import validate_complete, validate_spec

__all__ = [
    "EMOJI_MAGIC_SIZE",
    "INDEX_SIZE",
    "MAGIC_WAND_EMOJI",
    # Constants
    "PSPF_MAGIC",
    "PSPF_VERSION",
    "SLOT_ALIGNMENT",
    "SLOT_DESCRIPTOR_SIZE",
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
