#!/usr/bin/env python3
"""
Operation handler that bridges PSPF/2025 operation chains with archive capabilities.
Uses provide.foundation.archive for actual implementation.
"""

import io
from pathlib import Path
from typing import BinaryIO

from provide.foundation.archive import capabilities
from provide.foundation.archive.base import BaseArchive
from provide.foundation.logger import logger

from flavor.psp.format_2025.operations import (
    OP_TAR, OP_GZIP, OP_BZIP2, OP_XZ, OP_ZSTD,
    OP_AES256_GCM, OP_CHACHA20_POLY1305,
    unpack_operations, operations_to_string
)
from flavor.utils.archive_utils import ArchiveUtils


class OperationHandler:
    """
    Handles execution of operation chains for PSPF/2025 slots.
    
    Maps operation chains to appropriate archive handlers and executes
    them in the correct order.
    """
    
    def __init__(self):
        """Initialize operation handler with available implementations."""
        self.archive_utils = ArchiveUtils(deterministic=True)
        self._handlers = self._init_handlers()
        
    def _init_handlers(self) -> dict[int, callable]:
        """Initialize operation handlers mapping."""
        return {
            OP_TAR: self._handle_tar,
            OP_GZIP: self._handle_gzip,
            OP_BZIP2: self._handle_bzip2,
            OP_XZ: self._handle_xz,
            OP_ZSTD: self._handle_zstd,
            OP_AES256_GCM: self._handle_aes256_gcm,
            OP_CHACHA20_POLY1305: self._handle_chacha20,
        }
    
    def process_chain(
        self,
        source: Path | BinaryIO,
        operations: int,
        output: Path | BinaryIO | None = None,
        reverse: bool = False
    ) -> Path | BinaryIO:
        """
        Process an operation chain on source data.
        
        Args:
            source: Source file path or binary stream
            operations: Packed operation chain (64-bit integer)
            output: Optional output path or stream
            reverse: If True, apply operations in reverse (for extraction)
            
        Returns:
            Processed data as Path or BinaryIO
        """
        ops = unpack_operations(operations)
        
        if reverse:
            ops = list(reversed(ops))
        
        logger.debug(f"🔗 Processing operation chain: {operations_to_string(operations)}")
        logger.debug(f"📊 Operations: {[hex(op) for op in ops]} (reverse={reverse})")
        
        current = source
        
        for op in ops:
            handler = self._handlers.get(op)
            if not handler:
                logger.warning(f"⚠️ No handler for operation 0x{op:02x}")
                continue
            
            if reverse:
                # For extraction, use reverse handler
                current = self._reverse_operation(op, current, output)
            else:
                # For creation, use forward handler
                current = handler(current, output)
        
        return current
    
    def _handle_tar(self, source: Path | BinaryIO, output: Path | BinaryIO | None) -> Path | BinaryIO:
        """Handle TAR bundling operation."""
        if isinstance(source, Path) and source.is_dir():
            # Create tar from directory
            if output is None:
                output = Path(tempfile.mktemp(suffix=".tar"))
            
            import tarfile
            with tarfile.open(output, "w") as tar:
                tar.add(source, arcname=".")
            
            logger.debug(f"📦 Created TAR archive: {output}")
            return output
        
        return source
    
    def _handle_gzip(self, source: Path | BinaryIO, output: Path | BinaryIO | None) -> Path | BinaryIO:
        """Handle GZIP compression operation."""
        import gzip
        
        if isinstance(source, Path):
            if output is None:
                output = source.with_suffix(source.suffix + ".gz")
            
            with open(source, 'rb') as f_in:
                with gzip.open(output, 'wb', compresslevel=6) as f_out:
                    f_out.write(f_in.read())
            
            logger.debug(f"🗜️ Compressed with GZIP: {output}")
            return output
        elif isinstance(source, BinaryIO):
            # Compress stream
            compressed = io.BytesIO()
            with gzip.GzipFile(fileobj=compressed, mode='wb', compresslevel=6) as gz:
                gz.write(source.read())
            compressed.seek(0)
            return compressed
        
        return source
    
    def _handle_bzip2(self, source: Path | BinaryIO, output: Path | BinaryIO | None) -> Path | BinaryIO:
        """Handle BZIP2 compression operation."""
        import bz2
        
        if isinstance(source, Path):
            if output is None:
                output = source.with_suffix(source.suffix + ".bz2")
            
            with open(source, 'rb') as f_in:
                with bz2.open(output, 'wb', compresslevel=9) as f_out:
                    f_out.write(f_in.read())
            
            logger.debug(f"🗜️ Compressed with BZIP2: {output}")
            return output
        
        return source
    
    def _handle_xz(self, source: Path | BinaryIO, output: Path | BinaryIO | None) -> Path | BinaryIO:
        """Handle XZ/LZMA compression operation."""
        import lzma
        
        if isinstance(source, Path):
            if output is None:
                output = source.with_suffix(source.suffix + ".xz")
            
            with open(source, 'rb') as f_in:
                with lzma.open(output, 'wb', preset=6) as f_out:
                    f_out.write(f_in.read())
            
            logger.debug(f"🗜️ Compressed with XZ: {output}")
            return output
        
        return source
    
    def _handle_zstd(self, source: Path | BinaryIO, output: Path | BinaryIO | None) -> Path | BinaryIO:
        """Handle Zstandard compression operation."""
        try:
            import zstandard as zstd
        except ImportError:
            logger.warning("⚠️ zstandard not installed, skipping ZSTD operation")
            return source
        
        if isinstance(source, Path):
            if output is None:
                output = source.with_suffix(source.suffix + ".zst")
            
            cctx = zstd.ZstdCompressor(level=3)
            with open(source, 'rb') as f_in:
                with open(output, 'wb') as f_out:
                    f_out.write(cctx.compress(f_in.read()))
            
            logger.debug(f"🗜️ Compressed with ZSTD: {output}")
            return output
        
        return source
    
    def _handle_aes256_gcm(self, source: Path | BinaryIO, output: Path | BinaryIO | None) -> Path | BinaryIO:
        """Handle AES-256-GCM encryption operation."""
        logger.warning("⚠️ AES-256-GCM encryption not yet implemented")
        return source
    
    def _handle_chacha20(self, source: Path | BinaryIO, output: Path | BinaryIO | None) -> Path | BinaryIO:
        """Handle ChaCha20-Poly1305 encryption operation."""
        logger.warning("⚠️ ChaCha20-Poly1305 encryption not yet implemented")
        return source
    
    def _reverse_operation(self, op: int, source: Path | BinaryIO, output: Path | BinaryIO | None) -> Path | BinaryIO:
        """
        Reverse an operation (for extraction).
        
        Args:
            op: Operation to reverse
            source: Source data
            output: Optional output location
            
        Returns:
            Processed data
        """
        if op == OP_TAR:
            # Extract TAR
            import tarfile
            import tempfile
            
            if output is None:
                output = Path(tempfile.mkdtemp())
            
            with tarfile.open(source, "r") as tar:
                tar.extractall(output)
            
            logger.debug(f"📦 Extracted TAR to: {output}")
            return output
            
        elif op == OP_GZIP:
            # Decompress GZIP
            import gzip
            
            if isinstance(source, Path):
                if output is None:
                    output = source.with_suffix("")  # Remove .gz
                
                with gzip.open(source, 'rb') as f_in:
                    with open(output, 'wb') as f_out:
                        f_out.write(f_in.read())
                
                logger.debug(f"🗜️ Decompressed GZIP: {output}")
                return output
                
        elif op == OP_BZIP2:
            # Decompress BZIP2
            import bz2
            
            if isinstance(source, Path):
                if output is None:
                    output = source.with_suffix("")  # Remove .bz2
                
                with bz2.open(source, 'rb') as f_in:
                    with open(output, 'wb') as f_out:
                        f_out.write(f_in.read())
                
                logger.debug(f"🗜️ Decompressed BZIP2: {output}")
                return output
        
        return source
    
    def validate_operations(self, operations: int) -> tuple[bool, str]:
        """
        Validate that an operation chain is valid and supported.
        
        Args:
            operations: Packed operation chain
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        ops = unpack_operations(operations)
        
        if len(ops) == 0:
            return True, "No operations (raw data)"
        
        if len(ops) > 8:
            return False, f"Too many operations: {len(ops)} (max 8)"
        
        # Check for unsupported operations
        unsupported = []
        for op in ops:
            if op not in self._handlers:
                unsupported.append(f"0x{op:02x}")
        
        if unsupported:
            return False, f"Unsupported operations: {', '.join(unsupported)}"
        
        # Check for logical issues
        # (e.g., multiple compressions without intermediate steps)
        compress_ops = {OP_GZIP, OP_BZIP2, OP_XZ, OP_ZSTD}
        compress_count = sum(1 for op in ops if op in compress_ops)
        
        if compress_count > 1:
            logger.warning(f"⚠️ Multiple compression operations in chain: {compress_count}")
        
        return True, "Valid operation chain"


import tempfile  # Add at top of file