"""Memory and file alignment utilities.

DEPRECATED: This module is a compatibility shim. Import directly from:
    from provide.foundation.file import (
        align_offset,
        align_to_page,
        is_aligned,
        calculate_padding,
        PAGE_SIZE_4K,
        PAGE_SIZE_16K,
        DEFAULT_ALIGNMENT,
    )

Note: Flavorpack uses DEFAULT_SLOT_ALIGNMENT and DEFAULT_PAGE_SIZE constants
for PSPF-specific needs, but the underlying alignment functions are now from foundation.
"""

from provide.foundation.file import (
    align_offset as _align_offset,
    align_to_page as _align_to_page,
    calculate_padding as _calculate_padding,
    is_aligned as _is_aligned,
)

from flavor.config.defaults import DEFAULT_PAGE_SIZE, DEFAULT_SLOT_ALIGNMENT


def align_offset(offset: int, alignment: int = DEFAULT_SLOT_ALIGNMENT) -> int:
    """Align offset to specified boundary.

    Args:
        offset: The offset to align
        alignment: Alignment boundary (must be power of 2)

    Returns:
        Aligned offset
    """
    return _align_offset(offset, alignment)


def align_to_page(offset: int) -> int:
    """Align offset to page boundary for optimal mmap performance.

    Args:
        offset: The offset to align

    Returns:
        Page-aligned offset
    """
    return _align_to_page(offset, page_size=DEFAULT_PAGE_SIZE)


def is_aligned(offset: int, alignment: int = DEFAULT_SLOT_ALIGNMENT) -> bool:
    """Check if offset is aligned to boundary.

    Args:
        offset: The offset to check
        alignment: Alignment boundary

    Returns:
        True if aligned
    """
    return _is_aligned(offset, alignment)


def calculate_padding(
    current_offset: int, alignment: int = DEFAULT_SLOT_ALIGNMENT
) -> int:
    """Calculate padding needed to align to boundary.

    Args:
        current_offset: Current offset
        alignment: Desired alignment

    Returns:
        Number of padding bytes needed
    """
    return _calculate_padding(current_offset, alignment)


__all__ = [
    "align_offset",
    "align_to_page",
    "calculate_padding",
    "is_aligned",
]
