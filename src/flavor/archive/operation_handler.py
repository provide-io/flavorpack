#!/usr/bin/env python3
"""
Operation handler that uses provide.foundation.archive for implementation.
Maps PSPF/2025 operation chains to foundation archive capabilities.
"""

from pathlib import Path
from typing import BinaryIO

from provide.foundation.archive import Bzip2Compressor, GzipCompressor, TarArchive
from provide.foundation.file import temp_file
from provide.foundation.logger import logger

from flavor.archive.operations import Operation


class OperationHandler:
    """
    Handles individual archive operations using provide.foundation implementations.

    Maps operation IDs to appropriate foundation archive handlers.
    """

    def __init__(self) -> None:
        """Initialize operation handler with foundation-based handlers."""
        self._handlers = self._init_handlers()
        self._reverse_handlers = self._init_reverse_handlers()

    def _init_handlers(self) -> dict[int, callable]:
        """Initialize operation handlers mapping to foundation tools."""
        return {
            Operation.BUNDLE_TAR: self._handle_tar,
            Operation.COMPRESS_GZIP: self._handle_gzip,
            Operation.COMPRESS_BZIP2: self._handle_bzip2,
            Operation.COMPRESS_XZ: self._handle_xz,
            Operation.COMPRESS_ZSTD: self._handle_zstd,
            Operation.ENCRYPT_AES256: self._handle_aes256_gcm,
            Operation.ENCRYPT_CHACHA20: self._handle_chacha20,
        }

    def _init_reverse_handlers(self) -> dict[int, callable]:
        """Initialize reverse operation handlers mapping."""
        return {
            Operation.BUNDLE_TAR: self._reverse_tar,
            Operation.COMPRESS_GZIP: self._reverse_gzip,
            Operation.COMPRESS_BZIP2: self._reverse_bzip2,
            Operation.COMPRESS_XZ: self._reverse_xz,
            Operation.COMPRESS_ZSTD: self._reverse_zstd,
            Operation.ENCRYPT_AES256: self._reverse_aes256_gcm,
            Operation.ENCRYPT_CHACHA20: self._reverse_chacha20,
        }

    def apply_operation(
        self,
        operation: int,
        source: Path | BinaryIO,
        output: Path | BinaryIO | None = None,
    ) -> Path | BinaryIO:
        """
        Apply a single operation to source data.

        Args:
            operation: Operation ID to apply
            source: Source file path or binary stream
            output: Optional output path or stream

        Returns:
            Processed data as Path or BinaryIO
        """
        handler = self._handlers.get(operation)
        if not handler:
            logger.warning(f"⚠️ No handler for operation 0x{operation:02x}")
            return source

        return handler(source, output)

    def reverse_operation(
        self,
        operation: int,
        source: Path | BinaryIO,
        output: Path | BinaryIO | None = None,
    ) -> Path | BinaryIO:
        """
        Reverse a single operation (for extraction).

        Args:
            operation: Operation ID to reverse
            source: Source data
            output: Optional output location

        Returns:
            Processed data
        """
        return self._reverse_operation(operation, source, output)

    def supports_operation(self, operation: int) -> bool:
        """
        Check if operation is supported by this handler.

        Args:
            operation: Operation ID to check

        Returns:
            True if operation is supported
        """
        return operation in self._handlers

    def get_supported_operations(self) -> set[int]:
        """
        Get set of all supported operation IDs.

        Returns:
            Set of supported operation IDs
        """
        return set(self._handlers.keys())

    def _handle_tar(
        self, source: Path | BinaryIO, output: Path | BinaryIO | None
    ) -> Path | BinaryIO:
        """Handle TAR bundling using foundation TarArchive."""
        if isinstance(source, Path) and source.is_dir():
            if output is None:
                # Use secure temp file instead of mktemp
                with temp_file(suffix=".tar", cleanup=False) as temp_path:
                    output = temp_path

            tar_archive = TarArchive()
            tar_archive.create_from_directory(source, output)

            logger.debug(f"📦 Created TAR archive using foundation: {output}")
            return output

        return source

    def _handle_gzip(
        self, source: Path | BinaryIO, output: Path | BinaryIO | None
    ) -> Path | BinaryIO:
        """Handle GZIP compression using foundation GzipCompressor."""
        if isinstance(source, Path):
            if output is None:
                output = source.with_suffix(source.suffix + ".gz")

            compressor = GzipCompressor()
            compressor.compress_file(source, output)

            logger.debug(f"🗜️ Compressed with GZIP using foundation: {output}")
            return output

        # For streams, use foundation stream API
        elif hasattr(source, "read"):
            import io

            if output is None:
                output = io.BytesIO()

            compressor = GzipCompressor()
            compressor.compress(source, output)
            output.seek(0)

            logger.debug("🗜️ Compressed stream with GZIP using foundation")
            return output

        return source

    def _handle_bzip2(
        self, source: Path | BinaryIO, output: Path | BinaryIO | None
    ) -> Path | BinaryIO:
        """Handle BZIP2 compression using foundation Bzip2Compressor."""
        if isinstance(source, Path):
            if output is None:
                output = source.with_suffix(source.suffix + ".bz2")

            try:
                compressor = Bzip2Compressor()
                compressor.compress_file(source, output)

                logger.debug(f"🗜️ Compressed with BZIP2 using foundation: {output}")
                return output
            except (ImportError, AttributeError):
                # Fall back to direct implementation if foundation doesn't have it
                import bz2

                with (
                    source.open("rb") as f_in,
                    bz2.open(output, "wb", compresslevel=9) as f_out,
                ):
                    f_out.write(f_in.read())

                logger.debug(f"🗜️ Compressed with BZIP2 (fallback): {output}")
                return output

        # For streams, use foundation stream API if available
        elif hasattr(source, "read"):
            import io

            try:
                if output is None:
                    output = io.BytesIO()

                compressor = Bzip2Compressor()
                compressor.compress(source, output)
                output.seek(0)

                logger.debug("🗜️ Compressed stream with BZIP2 using foundation")
                return output
            except (ImportError, AttributeError):
                # Fall back to manual implementation
                import bz2

                if output is None:
                    output = io.BytesIO()

                compressed_data = bz2.compress(source.read(), compresslevel=9)
                output.write(compressed_data)
                output.seek(0)

                logger.debug("🗜️ Compressed stream with BZIP2 (fallback)")
                return output

        return source

    def _handle_xz(
        self, source: Path | BinaryIO, output: Path | BinaryIO | None
    ) -> Path | BinaryIO:
        """Handle XZ/LZMA compression (stdlib fallback)."""
        import lzma

        if isinstance(source, Path):
            if output is None:
                output = source.with_suffix(source.suffix + ".xz")

            with source.open("rb") as f_in, lzma.open(output, "wb", preset=6) as f_out:
                f_out.write(f_in.read())

            logger.debug(f"🗜️ Compressed with XZ (stdlib): {output}")
            return output

        return source

    def _handle_zstd(
        self, source: Path | BinaryIO, output: Path | BinaryIO | None
    ) -> Path | BinaryIO:
        """Handle Zstandard compression (optional)."""
        try:
            import zstandard as zstd
        except ImportError:
            logger.warning("⚠️ zstandard not installed, skipping ZSTD operation")
            return source

        if isinstance(source, Path):
            if output is None:
                output = source.with_suffix(source.suffix + ".zst")

            cctx = zstd.ZstdCompressor(level=3)
            with source.open("rb") as f_in, output.open("wb") as f_out:
                f_out.write(cctx.compress(f_in.read()))

            logger.debug(f"🗜️ Compressed with ZSTD: {output}")
            return output

        return source

    def _handle_aes256_gcm(
        self, source: Path | BinaryIO, output: Path | BinaryIO | None
    ) -> Path | BinaryIO:
        """Handle AES-256-GCM encryption (not implemented)."""
        logger.warning("⚠️ AES-256-GCM encryption not yet implemented")
        return source

    def _handle_chacha20(
        self, source: Path | BinaryIO, output: Path | BinaryIO | None
    ) -> Path | BinaryIO:
        """Handle ChaCha20-Poly1305 encryption (not implemented)."""
        logger.warning("⚠️ ChaCha20-Poly1305 encryption not yet implemented")
        return source

    def _reverse_operation(
        self, op: int, source: Path | BinaryIO, output: Path | BinaryIO | None
    ) -> Path | BinaryIO:
        """
        Reverse an operation (for extraction).

        Args:
            op: Operation to reverse
            source: Source data
            output: Optional output location

        Returns:
            Processed data
        """
        handler = self._reverse_handlers.get(op)
        if handler:
            return handler(source, output)

        logger.warning(f"⚠️ No reverse handler for operation 0x{op:02x}")
        return source

    def _reverse_tar(
        self, source: Path | BinaryIO, output: Path | BinaryIO | None
    ) -> Path | BinaryIO:
        """Reverse TAR operation (extract)."""
        if output is None:
            import tempfile

            output = Path(tempfile.mkdtemp())

        tar_archive = TarArchive()
        tar_archive.extract_to_directory(source, output)

        logger.debug(f"📦 Extracted TAR using foundation: {output}")
        return output

    def _reverse_gzip(
        self, source: Path | BinaryIO, output: Path | BinaryIO | None
    ) -> Path | BinaryIO:
        """Reverse GZIP operation (decompress)."""
        if isinstance(source, Path):
            if output is None:
                output = source.with_suffix("")  # Remove .gz

            compressor = GzipCompressor()
            compressor.decompress_file(source, output)

            logger.debug(f"🗜️ Decompressed GZIP using foundation: {output}")
            return output

        elif hasattr(source, "read"):
            import io

            if output is None:
                output = io.BytesIO()

            compressor = GzipCompressor()
            compressor.decompress(source, output)
            output.seek(0)

            logger.debug("🗜️ Decompressed GZIP stream using foundation")
            return output

        return source

    def _reverse_bzip2(
        self, source: Path | BinaryIO, output: Path | BinaryIO | None
    ) -> Path | BinaryIO:
        """Reverse BZIP2 operation (decompress)."""
        if isinstance(source, Path):
            if output is None:
                output = source.with_suffix("")  # Remove .bz2

            try:
                compressor = Bzip2Compressor()
                compressor.decompress_file(source, output)

                logger.debug(f"🗜️ Decompressed BZIP2 using foundation: {output}")
                return output
            except (ImportError, AttributeError):
                import bz2

                with bz2.open(source, "rb") as f_in, output.open("wb") as f_out:
                    f_out.write(f_in.read())

                logger.debug(f"🗜️ Decompressed BZIP2 (fallback): {output}")
                return output

        elif hasattr(source, "read"):
            import io

            try:
                if output is None:
                    output = io.BytesIO()

                compressor = Bzip2Compressor()
                compressor.decompress(source, output)
                output.seek(0)

                logger.debug("🗜️ Decompressed BZIP2 stream using foundation")
                return output
            except (ImportError, AttributeError):
                import bz2

                if output is None:
                    output = io.BytesIO()

                decompressed_data = bz2.decompress(source.read())
                output.write(decompressed_data)
                output.seek(0)

                logger.debug("🗜️ Decompressed BZIP2 stream (fallback)")
                return output

        return source

    def _reverse_xz(
        self, source: Path | BinaryIO, output: Path | BinaryIO | None
    ) -> Path | BinaryIO:
        """Reverse XZ operation (decompress)."""
        import lzma

        if isinstance(source, Path):
            if output is None:
                output = source.with_suffix("")  # Remove .xz

            with lzma.open(source, "rb") as f_in, output.open("wb") as f_out:
                f_out.write(f_in.read())

            logger.debug(f"🗜️ Decompressed XZ (stdlib): {output}")
            return output

        return source

    def _reverse_zstd(
        self, source: Path | BinaryIO, output: Path | BinaryIO | None
    ) -> Path | BinaryIO:
        """Reverse ZSTD operation (decompress)."""
        try:
            import zstandard as zstd
        except ImportError:
            logger.warning("⚠️ zstandard not installed, skipping ZSTD reversal")
            return source

        if isinstance(source, Path):
            if output is None:
                output = source.with_suffix("")  # Remove .zst

            dctx = zstd.ZstdDecompressor()
            with source.open("rb") as f_in, output.open("wb") as f_out:
                f_out.write(dctx.decompress(f_in.read()))

            logger.debug(f"🗜️ Decompressed ZSTD: {output}")
            return output

        return source

    def _reverse_aes256_gcm(
        self, source: Path | BinaryIO, output: Path | BinaryIO | None
    ) -> Path | BinaryIO:
        """Reverse AES-256-GCM operation (decrypt) - not implemented."""
        logger.warning("⚠️ AES-256-GCM decryption not yet implemented")
        return source

    def _reverse_chacha20(
        self, source: Path | BinaryIO, output: Path | BinaryIO | None
    ) -> Path | BinaryIO:
        """Reverse ChaCha20-Poly1305 operation (decrypt) - not implemented."""
        logger.warning("⚠️ ChaCha20-Poly1305 decryption not yet implemented")
        return source

    def validate_operations(self, operations: int) -> tuple[bool, str]:
        """
        Validate operations - deprecated, use ChainProcessor instead.

        Args:
            operations: Packed operation chain

        Returns:
            Tuple of (is_valid, error_message)
        """
        logger.warning("⚠️ OperationHandler.validate_operations() is deprecated")
        return True, "Deprecated method - use ChainProcessor instead"
