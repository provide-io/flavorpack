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
    MAGIC_WAND_EMOJI,
)
from flavor.psp.format_2025.index import PSPFIndex
from flavor.psp.format_2025.slots import SlotMetadata, align_offset
from flavor.psp.format_2025.crypto import ephemeral_key_pair, sign_data, verify_signature
from flavor.psp.format_2025.builder import PSPFBuilder
from flavor.psp.format_2025.reader import PSPFReader
from flavor.psp.format_2025.launcher import PSPFLauncher
from flavor.psp.format_2025.executor import BundleExecutor

__all__ = [
    # Constants
    'PSPF_MAGIC',
    'PSPF_VERSION',
    'INDEX_SIZE',
    'EMOJI_MAGIC_SIZE',
    'SLOT_ALIGNMENT',
    'MAGIC_WAND_EMOJI',
    
    # Classes
    'PSPFIndex',
    'SlotMetadata',
    'PSPFBuilder',
    'PSPFReader',
    'PSPFLauncher',
    'BundleExecutor',
    
    # Functions
    'ephemeral_key_pair',
    'sign_data',
    'verify_signature',
    'align_offset',
]