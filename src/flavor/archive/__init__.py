"""
Archive operation chain system for PSPF/2025.

Provides composable archive operations without heavy dependencies.
Works with or without protobuf installed.
"""

from flavor.archive.operations import (
    Operation,
    pack_operations,
    unpack_operations,
    get_operation_name,
    get_operation_capabilities,
)
from flavor.archive.chain import ArchiveChain, ChainProcessor

__all__ = [
    "Operation",
    "ArchiveChain",
    "ChainProcessor",
    "pack_operations",
    "unpack_operations",
    "get_operation_name",
    "get_operation_capabilities",
]

__version__ = "2025.1.0"