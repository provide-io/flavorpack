"""Memory and file alignment utilities."""

from flavor.psp.format_2025.constants import PAGE_SIZE, SLOT_ALIGNMENT


def align_offset(offset: int, alignment: int = SLOT_ALIGNMENT) -> int:
    """Align offset to specified boundary.
    
    Args:
        offset: The offset to align
        alignment: Alignment boundary (must be power of 2)
        
    Returns:
        Aligned offset
    """
    return (offset + alignment - 1) & ~(alignment - 1)


def align_to_page(offset: int) -> int:
    """Align offset to page boundary for optimal mmap performance.
    
    Args:
        offset: The offset to align
        
    Returns:
        Page-aligned offset
    """
    return align_offset(offset, PAGE_SIZE)


def is_aligned(offset: int, alignment: int = SLOT_ALIGNMENT) -> bool:
    """Check if offset is aligned to boundary.
    
    Args:
        offset: The offset to check
        alignment: Alignment boundary
        
    Returns:
        True if aligned
    """
    return (offset & (alignment - 1)) == 0


def calculate_padding(current_offset: int, alignment: int = SLOT_ALIGNMENT) -> int:
    """Calculate padding needed to align to boundary.
    
    Args:
        current_offset: Current offset
        alignment: Desired alignment
        
    Returns:
        Number of padding bytes needed
    """
    aligned = align_offset(current_offset, alignment)
    return aligned - current_offset