"""
Archive operation chain system for PSPF/2025.

Provides composable archive operations without heavy dependencies.
Works with or without protobuf installed.
"""

from __future__ import annotations


from flavor.archive.chain import ArchiveChain, ChainProcessor
from flavor.archive.operations import (
    Operation,
    get_operation_capabilities,
    get_operation_name,
    pack_operations,
    unpack_operations,
)

__all__ = [
    "ArchiveChain",
    "ChainProcessor",
    "Operation",
    "get_operation_capabilities",
    "get_operation_name",
    "pack_operations",
    "unpack_operations",
]

__version__ = "2025.1.0"
