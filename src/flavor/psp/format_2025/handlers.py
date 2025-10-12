#!/usr/bin/env python3
"""
PSPF Operation Handlers - Bridge between PSPF operations and Foundation archive tools.

This module maps PSPF/2025 operation chains to provide.foundation.archive implementations,
ensuring secure, tested, and consistent archive operations across the ecosystem.
"""

from __future__ import annotations

from pathlib import Path

from provide.foundation import logger
from provide.foundation.archive import (
    ArchiveOperation as FoundationOp,
    Bzip2Compressor,
    GzipCompressor,
    TarArchive,
)
from provide.foundation.file import temp_file

from flavor.psp.format_2025.constants import (
    OP_BZIP2,
    OP_GZIP,
    OP_NONE,
    OP_TAR,
    OP_XZ,
    OP_ZSTD,
)
from flavor.psp.format_2025.operations import unpack_operations

# Operation code mapping: PSPF → Foundation
_OPERATION_MAP = {
    OP_TAR: FoundationOp.TAR,
    OP_GZIP: FoundationOp.GZIP,
    OP_BZIP2: FoundationOp.BZIP2,
    OP_XZ: FoundationOp.XZ,
    OP_ZSTD: FoundationOp.ZSTD,
}


def map_operations(pspf_ops: list[int]) -> list[FoundationOp]:
    """Map PSPF operation codes to Foundation operations.

    Args:
        pspf_ops: List of PSPF operation codes

    Returns:
        List of Foundation ArchiveOperation enum values

    Raises:
        ValueError: If operation code is unsupported
    """
    foundation_ops = []
    for op in pspf_ops:
        if op == OP_NONE:
            continue
        if op not in _OPERATION_MAP:
            raise ValueError(f"Unsupported PSPF operation: 0x{op:02x}")
        foundation_ops.append(_OPERATION_MAP[op])

    logger.debug(
        "🔄 Mapped PSPF operations to Foundation",
        pspf_ops=[f"0x{op:02x}" for op in pspf_ops],
        foundation_ops=[op.name for op in foundation_ops],
    )
    return foundation_ops


def _apply_single_operation(
    data: bytes, op: FoundationOp, compression_level: int
) -> bytes:
    """Apply a single compression operation.

    Args:
        data: Input data
        op: Foundation operation to apply
        compression_level: Compression level

    Returns:
        Compressed data
    """
    if op == FoundationOp.GZIP:
        gzip_compressor = GzipCompressor(level=compression_level)
        result = gzip_compressor.compress_bytes(data)
        logger.trace("🗜️ Applied GZIP compression", output_size=len(result))
        return result
    if op == FoundationOp.BZIP2:
        bzip2_compressor = Bzip2Compressor(level=9)  # bzip2 always uses level 9
        result = bzip2_compressor.compress_bytes(data)
        logger.trace("🗜️ Applied BZIP2 compression", output_size=len(result))
        return result
    if op == FoundationOp.XZ:
        import lzma

        result = lzma.compress(data, preset=6)
        logger.trace("🗜️ Applied XZ compression", output_size=len(result))
        return result
    if op == FoundationOp.ZSTD:
        try:
            import zstandard as zstd

            cctx = zstd.ZstdCompressor(level=3)
            result = cctx.compress(data)
            logger.trace("🗜️ Applied ZSTD compression", output_size=len(result))
            return result
        except ImportError:
            logger.warning("⚠️ ZSTD not available, skipping compression")
            return data

    logger.warning(f"⚠️ Unsupported operation for direct compression: {op}")
    return data


def apply_operations(
    data: bytes,
    packed_ops: int,
    compression_level: int = 6,
    deterministic: bool = True,
) -> bytes:
    """Apply PSPF operation chain using Foundation archive tools.

    Args:
        data: Raw data to process
        packed_ops: Packed PSPF operations as 64-bit integer
        compression_level: Compression level (1-9)
        deterministic: Create deterministic/reproducible output

    Returns:
        Processed data after applying operation chain

    Raises:
        ValueError: If operations are invalid
        ArchiveError: If operation execution fails
    """
    if packed_ops == 0:
        logger.trace("📦 No operations, returning raw data")
        return data

    # Unpack and map operations
    pspf_ops = unpack_operations(packed_ops)
    logger.debug(
        "🔧 Applying PSPF operation chain",
        operations=[f"0x{op:02x}" for op in pspf_ops],
        data_size=len(data),
    )

    foundation_ops = map_operations(pspf_ops)

    # Skip TAR if present (handled during slot loading)
    if FoundationOp.TAR in foundation_ops:
        logger.trace("📦 TAR operation detected - data should already be tar format")
        foundation_ops = [op for op in foundation_ops if op != FoundationOp.TAR]
        if not foundation_ops:
            return data

    # Apply compression operations
    result = data
    for op in foundation_ops:
        result = _apply_single_operation(result, op, compression_level)

    logger.debug(
        "✅ Operation chain applied",
        input_size=len(data),
        output_size=len(result),
        compression_ratio=f"{len(result) / len(data):.2f}" if len(data) > 0 else "N/A",
    )

    return result


def reverse_operations(data: bytes, packed_ops: int) -> bytes:
    """Reverse PSPF operation chain for extraction using Foundation tools.

    Args:
        data: Compressed/processed data
        packed_ops: Packed PSPF operations as 64-bit integer

    Returns:
        Decompressed/unprocessed data

    Raises:
        ValueError: If operations are invalid
        ArchiveError: If operation reversal fails
    """
    if packed_ops == 0:
        logger.trace("📦 No operations to reverse")
        return data

    # Unpack PSPF operations
    pspf_ops = unpack_operations(packed_ops)
    logger.debug(
        "🔄 Reversing PSPF operation chain",
        operations=[f"0x{op:02x}" for op in pspf_ops],
        data_size=len(data),
    )

    # Map to Foundation operations
    foundation_ops = map_operations(pspf_ops)

    # Reverse operations in reverse order
    result = data
    for op in reversed(foundation_ops):
        if op == FoundationOp.TAR:
            # TAR extraction is handled separately by extract_archive()
            logger.trace("📦 TAR operation (will be extracted separately)")
            continue
        elif op == FoundationOp.GZIP:
            gzip_compressor = GzipCompressor(
                level=6
            )  # level doesn't matter for decompression
            result = gzip_compressor.decompress_bytes(result)
            logger.trace("🗜️ Reversed GZIP compression", output_size=len(result))
        elif op == FoundationOp.BZIP2:
            bzip2_compressor = Bzip2Compressor(level=9)
            result = bzip2_compressor.decompress_bytes(result)
            logger.trace("🗜️ Reversed BZIP2 compression", output_size=len(result))
        elif op == FoundationOp.XZ:
            import lzma

            result = lzma.decompress(result)
            logger.trace("🗜️ Reversed XZ compression", output_size=len(result))
        elif op == FoundationOp.ZSTD:
            try:
                import zstandard as zstd

                dctx = zstd.ZstdDecompressor()
                result = dctx.decompress(result)
                logger.trace("🗜️ Reversed ZSTD compression", output_size=len(result))
            except ImportError:
                logger.warning("⚠️ ZSTD not available for decompression")
                return data
        else:
            logger.warning(f"⚠️ Unsupported operation for reversal: {op}")

    logger.debug(
        "✅ Reverse operations complete",
        input_size=len(data),
        output_size=len(result),
        expansion_ratio=f"{len(result) / len(data):.2f}" if len(data) > 0 else "N/A",
    )

    return result


def create_tar_archive(source: Path, deterministic: bool = True) -> bytes:
    """Create TAR archive from directory using Foundation's TarArchive.

    Args:
        source: Source directory or file
        deterministic: Create reproducible archive

    Returns:
        TAR archive as bytes

    Raises:
        ArchiveError: If archive creation fails
    """
    logger.debug(
        "📦 Creating TAR archive", source=str(source), deterministic=deterministic
    )

    tar_impl = TarArchive(deterministic=deterministic)

    # Foundation's TarArchive expects to write to a file
    # Use a BytesIO buffer to capture the output
    with temp_file(suffix=".tar", cleanup=True) as temp_path:
        tar_impl.create(source, temp_path)
        result = temp_path.read_bytes()

    logger.debug("✅ TAR archive created", size=len(result))
    return result


def extract_archive(data: bytes, dest: Path, packed_ops: int) -> Path:
    """Extract archive data using Foundation's extractors.

    Args:
        data: Archive data (potentially compressed)
        dest: Destination directory
        packed_ops: Packed PSPF operations to determine format

    Returns:
        Path to extracted content

    Raises:
        ArchiveError: If extraction fails
    """
    logger.debug(
        "📂 Extracting archive",
        data_size=len(data),
        dest=str(dest),
        operations=f"0x{packed_ops:016x}",
    )

    # First, reverse compression operations
    decompressed = reverse_operations(data, packed_ops)

    # Determine if TAR extraction is needed
    pspf_ops = unpack_operations(packed_ops) if packed_ops != 0 else []
    needs_tar_extract = OP_TAR in pspf_ops

    if needs_tar_extract:
        # Extract TAR using Foundation
        logger.debug("📦 Extracting TAR archive")
        tar_impl = TarArchive()

        # Write decompressed data to temp file, then extract
        with temp_file(suffix=".tar", cleanup=True) as temp_path:
            temp_path.write_bytes(decompressed)
            tar_impl.extract(temp_path, dest)

        logger.debug("✅ TAR extracted", dest=str(dest))
        return dest

    # Not an archive, just write the data
    output_file = dest / "data"
    dest.mkdir(parents=True, exist_ok=True)
    output_file.write_bytes(decompressed)

    logger.debug("✅ Data written", path=str(output_file))
    return output_file


__all__ = [
    "apply_operations",
    "create_tar_archive",
    "extract_archive",
    "map_operations",
    "reverse_operations",
]
