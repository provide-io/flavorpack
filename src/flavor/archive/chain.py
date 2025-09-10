"""
Archive chain processing for PSPF/2025.

Provides ArchiveChain data structure and ChainProcessor execution engine
for composable operation chains without heavy dependencies.
"""

import io
import tempfile
from pathlib import Path
from typing import BinaryIO

from provide.foundation.logger import logger

from flavor.archive.operations import (
    Operation,
    pack_operations,
    unpack_operations,
    validate_operation_chain,
    format_operation_chain,
    get_operation_name,
    get_operation_category,
)


class ArchiveChain:
    """
    Represents a sequence of archive operations.
    
    Provides validation, optimization, and serialization for operation chains.
    """
    
    def __init__(self, operations: list[int] | int | None = None):
        """
        Initialize archive chain.
        
        Args:
            operations: List of operation IDs or packed 64-bit integer
        """
        if operations is None:
            self._operations = []
        elif isinstance(operations, int):
            self._operations = unpack_operations(operations)
        elif isinstance(operations, list):
            self._operations = operations.copy()
        else:
            raise TypeError(f"operations must be list[int], int, or None, got {type(operations)}")
        
        # Validate chain on creation
        is_valid, error = validate_operation_chain(self._operations)
        if not is_valid:
            raise ValueError(f"Invalid operation chain: {error}")
    
    @property
    def operations(self) -> list[int]:
        """Get operations list (read-only)."""
        return self._operations.copy()
    
    @property 
    def packed(self) -> int:
        """Get packed 64-bit representation."""
        return pack_operations(self._operations)
    
    @property
    def length(self) -> int:
        """Get number of operations in chain."""
        return len(self._operations)
    
    @property
    def is_empty(self) -> bool:
        """Check if chain has no operations."""
        return len(self._operations) == 0
    
    def add_operation(self, operation: int) -> 'ArchiveChain':
        """
        Add operation to end of chain (returns new chain).
        
        Args:
            operation: Operation ID to add
            
        Returns:
            New ArchiveChain with operation added
        """
        new_ops = self._operations + [operation]
        return ArchiveChain(new_ops)
    
    def remove_operation(self, index: int) -> 'ArchiveChain':
        """
        Remove operation at index (returns new chain).
        
        Args:
            index: Index of operation to remove
            
        Returns:
            New ArchiveChain with operation removed
        """
        new_ops = self._operations.copy()
        del new_ops[index]
        return ArchiveChain(new_ops)
    
    def reverse(self) -> 'ArchiveChain':
        """Get reversed chain for extraction."""
        return ArchiveChain(list(reversed(self._operations)))
    
    def optimize(self) -> 'ArchiveChain':
        """
        Remove redundant operations and optimize chain.
        
        Returns:
            Optimized ArchiveChain
        """
        if not self._operations:
            return ArchiveChain([])
        
        # Remove consecutive duplicate operations
        optimized = [self._operations[0]]
        for op in self._operations[1:]:
            if op != optimized[-1]:
                optimized.append(op)
        
        return ArchiveChain(optimized)
    
    def get_categories(self) -> list[str]:
        """Get operation categories in chain."""
        return [get_operation_category(op) for op in self._operations]
    
    def has_category(self, category: str) -> bool:
        """Check if chain contains operations of given category."""
        return category in self.get_categories()
    
    def __str__(self) -> str:
        """Human-readable chain representation."""
        return format_operation_chain(self._operations)
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"ArchiveChain({self._operations})"
    
    def __eq__(self, other) -> bool:
        """Compare chains for equality."""
        if not isinstance(other, ArchiveChain):
            return False
        return self._operations == other._operations
    
    def __len__(self) -> int:
        """Get chain length."""
        return len(self._operations)


class ChainProcessor:
    """
    Executes archive operation chains using registered handlers.
    
    Coordinates between operation chains and actual archive implementations.
    """
    
    def __init__(self):
        """Initialize chain processor with handler registry."""
        from flavor.archive.operation_handler import OperationHandler
        self._handler = OperationHandler()
    
    def process(
        self,
        source: Path | BinaryIO,
        chain: ArchiveChain,
        output: Path | BinaryIO | None = None,
        reverse: bool = False
    ) -> Path | BinaryIO:
        """
        Process data through operation chain.
        
        Args:
            source: Source file path or binary stream
            chain: ArchiveChain to execute
            output: Optional output path or stream
            reverse: If True, apply operations in reverse (for extraction)
            
        Returns:
            Processed data as Path or BinaryIO
        """
        if chain.is_empty:
            logger.debug("🔗 Empty chain, returning source unchanged")
            return source
        
        processing_chain = chain.reverse() if reverse else chain
        
        logger.debug(f"🔗 Processing chain: {processing_chain}")
        logger.debug(f"📊 Operations: {[hex(op) for op in processing_chain.operations]} (reverse={reverse})")
        
        current = source
        
        for i, op in enumerate(processing_chain.operations):
            op_name = get_operation_name(op)
            logger.debug(f"🔧 Step {i+1}/{len(processing_chain)}: {op_name} (0x{op:02x})")
            
            # For the last operation, use the final output destination
            is_last = (i == len(processing_chain) - 1)
            step_output = output if is_last else None
            
            try:
                if reverse:
                    current = self._handler.reverse_operation(op, current, step_output)
                else:
                    current = self._handler.apply_operation(op, current, step_output)
                
                logger.debug(f"✅ Step {i+1} completed: {type(current).__name__}")
                
            except Exception as e:
                logger.error(f"❌ Step {i+1} failed: {e}")
                raise
        
        logger.debug(f"✅ Chain processing complete: {len(processing_chain)} operations")
        return current
    
    def validate_chain(self, chain: ArchiveChain) -> tuple[bool, str]:
        """
        Validate that a chain is executable.
        
        Args:
            chain: ArchiveChain to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if chain.is_empty:
            return True, "Empty chain (pass-through)"
        
        # Check basic chain validity
        is_valid, error = validate_operation_chain(chain.operations)
        if not is_valid:
            return False, error
        
        # Check that all operations have handlers
        unsupported = []
        for op in chain.operations:
            if not self._handler.supports_operation(op):
                op_name = get_operation_name(op)
                unsupported.append(f"{op_name} (0x{op:02x})")
        
        if unsupported:
            return False, f"Unsupported operations: {', '.join(unsupported)}"
        
        return True, "Valid chain"
    
    def get_supported_operations(self) -> set[int]:
        """Get set of supported operation IDs."""
        return self._handler.get_supported_operations()