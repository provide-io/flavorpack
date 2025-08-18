"""
PSPF 2025 Format Implementation

Progressive Secure Package Format (2025 Edition)
"""

from flavor.psp.format_2025.constants import (
    PSPF_MAGIC,
    PSPF_VERSION,
    INDEX_SIZE,
    EMOJI_MAGIC_SIZE,
    SLOT_ALIGNMENT,
    SLOT_DESCRIPTOR_SIZE,
    MAGIC_WAND_EMOJI,
)
from flavor.psp.format_2025.index import PSPFIndex
from flavor.psp.format_2025.slots import SlotMetadata, align_offset
from flavor.psp.format_2025.crypto import generate_key_pair, sign_data, verify_signature
from flavor.psp.format_2025.builder import PSPFBuilder, build_package
from flavor.psp.format_2025.reader import PSPFReader
from flavor.psp.format_2025.launcher import PSPFLauncher
from flavor.psp.format_2025.executor import BundleExecutor
from flavor.psp.format_2025.spec import (
    BuildSpec,
    BuildResult,
    BuildOptions,
    KeyConfig,
    PreparedSlot,
)
from flavor.psp.format_2025.validation import validate_spec, validate_complete
from flavor.psp.format_2025.keys import resolve_keys, create_key_config

__all__ = [
    # Constants
    'PSPF_MAGIC',
    'PSPF_VERSION',
    'INDEX_SIZE',
    'EMOJI_MAGIC_SIZE',
    'SLOT_ALIGNMENT',
    'SLOT_DESCRIPTOR_SIZE',
    'MAGIC_WAND_EMOJI',
    
    # Core Classes
    'PSPFIndex',
    'SlotMetadata',
    'PSPFBuilder',
    'PSPFReader',
    'PSPFLauncher',
    'BundleExecutor',
    
    # Spec Classes
    'BuildSpec',
    'BuildResult',
    'BuildOptions',
    'KeyConfig',
    'PreparedSlot',
    
    # Functions
    'generate_key_pair',
    'sign_data',
    'verify_signature',
    'align_offset',
    'build_package',
    'validate_spec',
    'validate_complete',
    'resolve_keys',
    'create_key_config',
]