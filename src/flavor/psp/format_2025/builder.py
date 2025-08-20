"""
PSPF Builder - Re-export from builder_core for backward compatibility.

The builder has been split into multiple modules for better maintainability:
- builder_core.py: Main build_package function and PSPFBuilder class
- builder_slots.py: Slot preparation logic
- builder_index.py: Index creation logic
- builder_writer.py: Package writing logic
"""

from flavor.psp.format_2025.builder_core import PSPFBuilder, build_package

__all__ = ["PSPFBuilder", "build_package"]