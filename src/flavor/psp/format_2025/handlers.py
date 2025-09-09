#!/usr/bin/env python3
"""
Operation handlers for PSPF/2025 using provide.foundation archive capabilities.

Maps PSPF operations to provide.foundation archive implementations.
"""

from io import BytesIO
import gzip
import bz2
import lzma
from pathlib import Path
from typing import BinaryIO

from provide.foundation.archive import GzipCompressor, TarArchive
from enum import IntFlag

class ArchiveCapability(IntFlag):
    """Archive capability flags."""
    BUNDLE = 1
    COMPRESS = 2
    ENCRYPT = 4

from flavor.psp.format_2025.operations import (
    OP_TAR, OP_GZIP, OP_BZIP2, OP_XZ, OP_ZSTD,
    OP_AES256_GCM, OP_CHACHA20_POLY1305,
    unpack_operations
)


class OperationHandler:
    """
    Handles operation chains for PSPF slots.
    
    Maps PSPF operations to provide.foundation capabilities and implementations.
    """
    
    def __init__(self):
        """Initialize operation handler with registered handlers."""
        self.handlers = {
            # Bundle operations
            OP_TAR: self._handle_tar,
            
            # Compression operations
            OP_GZIP: self._handle_gzip,
            OP_BZIP2: self._handle_bzip2,
            OP_XZ: self._handle_xz,
            
            # TODO: Add more handlers as needed
            # OP_ZSTD: self._handle_zstd,
            # OP_AES256_GCM: self._handle_aes256_gcm,
        }
        
        # Map operations to capabilities
        self.capability_map = {
            OP_TAR: ArchiveCapability.BUNDLE,
            OP_GZIP: ArchiveCapability.COMPRESS,
            OP_BZIP2: ArchiveCapability.COMPRESS,
            OP_XZ: ArchiveCapability.COMPRESS,
            OP_ZSTD: ArchiveCapability.COMPRESS,
            OP_AES256_GCM: ArchiveCapability.ENCRYPT,
            OP_CHACHA20_POLY1305: ArchiveCapability.ENCRYPT,
        }
    
    def process_chain(self, data: bytes, operations: int, reverse: bool = False) -> bytes:
        """
        Process data through an operation chain.
        
        Args:
            data: Input data
            operations: Packed 64-bit operation chain
            reverse: If True, apply operations in reverse (for extraction)
            
        Returns:
            Processed data
        """
        ops = unpack_operations(operations)
        
        if reverse:
            ops = list(reversed(ops))
        
        result = data
        for op in ops:
            if reverse:
                result = self._reverse_operation(result, op)
            else:
                result = self._apply_operation(result, op)
        
        return result
    
    def _apply_operation(self, data: bytes, operation: int) -> bytes:
        """Apply a single operation to data."""
        handler = self.handlers.get(operation)
        if not handler:
            # Unknown operation, pass through
            return data
        
        return handler(data, compress=True)
    
    def _reverse_operation(self, data: bytes, operation: int) -> bytes:
        """Apply the reverse of an operation (for extraction)."""
        handler = self.handlers.get(operation)
        if not handler:
            # Unknown operation, pass through
            return data
        
        return handler(data, compress=False)
    
    def _handle_tar(self, data: bytes, compress: bool = True) -> bytes:
        """Handle TAR bundling/extraction."""
        if compress:
            # For bundling, we need actual files - this is a simplified version
            # In practice, the builder would use TarArchive directly
            import tarfile
            import tempfile
            
            output = BytesIO()
            with tarfile.open(fileobj=output, mode='w') as tar:
                # This is a placeholder - real implementation needs file paths
                info = tarfile.TarInfo(name="data")
                info.size = len(data)
                tar.addfile(info, BytesIO(data))
            
            return output.getvalue()
        else:
            # Extract TAR
            import tarfile
            
            input_stream = BytesIO(data)
            with tarfile.open(fileobj=input_stream, mode='r') as tar:
                # For simplicity, extract first member
                members = tar.getmembers()
                if members:
                    file_data = tar.extractfile(members[0])
                    if file_data:
                        return file_data.read()
            
            return data
    
    def _handle_gzip(self, data: bytes, compress: bool = True) -> bytes:
        """Handle GZIP compression/decompression."""
        if compress:
            return gzip.compress(data)
        else:
            return gzip.decompress(data)
    
    def _handle_bzip2(self, data: bytes, compress: bool = True) -> bytes:
        """Handle BZIP2 compression/decompression."""
        if compress:
            return bz2.compress(data)
        else:
            return bz2.decompress(data)
    
    def _handle_xz(self, data: bytes, compress: bool = True) -> bytes:
        """Handle XZ/LZMA compression/decompression."""
        if compress:
            return lzma.compress(data, format=lzma.FORMAT_XZ)
        else:
            return lzma.decompress(data)
    
    def validate_operations(self, operations: int) -> tuple[bool, str]:
        """
        Validate that an operation chain is supported.
        
        Args:
            operations: Packed operation chain
            
        Returns:
            (is_valid, message)
        """
        ops = unpack_operations(operations)
        
        if not ops:
            return True, "No operations (RAW)"
        
        # Check each operation is supported
        for op in ops:
            if op not in self.handlers:
                from flavor.psp.format_2025.operations import operations_to_string
                op_name = operations_to_string(op)
                return False, f"Unsupported operation: {op_name}"
        
        # Check capability compatibility
        capabilities = []
        for op in ops:
            if op in self.capability_map:
                capabilities.append(self.capability_map[op])
        
        # Basic validation: no duplicate core operations
        seen = set()
        for cap in capabilities:
            if cap in seen and cap in (ArchiveCapability.BUNDLE, ArchiveCapability.COMPRESS):
                return False, "Duplicate operation type in chain"
            seen.add(cap)
        
        return True, "Valid operation chain"
    
    def get_required_capabilities(self, operations: int) -> ArchiveCapability:
        """
        Get the capabilities required for an operation chain.
        
        Args:
            operations: Packed operation chain
            
        Returns:
            Combined capability flags
        """
        ops = unpack_operations(operations)
        
        capabilities = ArchiveCapability(0)
        for op in ops:
            if op in self.capability_map:
                capabilities |= self.capability_map[op]
        
        return capabilities