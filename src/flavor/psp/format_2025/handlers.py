#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PSPF operation handlers bridging PSPF ops and Foundation archive tooling.

This module maps PSPF/2025 operation chains to provide.foundation.archive implementations,
ensuring secure, tested, and consistent archive operations across the ecosystem.
"""

from __future__ import annotations

from pathlib import Path

from provide.foundation import logger
from provide.foundation.archive import (
    DEFAULT_LIMITS,
    ArchiveLimits,
    ArchiveOperation as FoundationOp,
    Bzip2Compressor,
    GzipCompressor,
    TarArchive,
    XzCompressor,
    ZstdCompressor,
)
from provide.foundation.archive.base import ArchiveError
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


def _apply_single_operation(data: bytes, op: FoundationOp, compression_level: int) -> bytes:
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
        xz_compressor = XzCompressor(level=compression_level)
        result = xz_compressor.compress_bytes(data)
        logger.trace("🗜️ Applied XZ compression", output_size=len(result))
        return result
    if op == FoundationOp.ZSTD:
        try:
            zstd_compressor = ZstdCompressor(level=compression_level)
            result = zstd_compressor.compress_bytes(data)
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
        ValueError: If operations are invalid or compression_level out of range
        ArchiveError: If operation execution fails
    """
    if packed_ops == 0:
        return data

    if not (1 <= compression_level <= 9):
        raise ValueError(f"Compression level must be 1-9, got {compression_level}")

    try:
        # Unpack and map operations
        pspf_ops = unpack_operations(packed_ops)
        logger.debug(
            "🗜️ Applying PSPF operation chain",
            operations=[f"0x{op:02x}" for op in pspf_ops],
            data_size=len(data),
            compression_level=compression_level,
        )

        foundation_ops = map_operations(pspf_ops)

        # Skip TAR if present (handled during slot loading)
        if FoundationOp.TAR in foundation_ops:
            foundation_ops = [op for op in foundation_ops if op != FoundationOp.TAR]
            if not foundation_ops:
                return data

        # Apply compression operations
        result = data
        for op in foundation_ops:
            result = _apply_single_operation(result, op, compression_level)

        logger.debug(
            "✅ Operations applied successfully",
            input_size=len(data),
            output_size=len(result),
            compression_ratio=f"{len(result) / len(data):.2f}" if len(data) > 0 else "N/A",
        )

        return result

    except ValueError:
        raise
    except Exception as e:
        logger.error(
            "❌ Failed to apply operations",
            error=str(e),
            error_type=type(e).__name__,
            operations=f"0x{packed_ops:016x}",
        )
        raise ArchiveError(f"Operation application failed: {e}") from e


def reverse_operations(data: bytes, packed_ops: int) -> bytes:  # noqa: C901
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
        return data

    try:
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
                continue
            elif op == FoundationOp.GZIP:
                gzip_compressor = GzipCompressor(level=6)  # level doesn't matter for decompression
                result = gzip_compressor.decompress_bytes(result)
                logger.trace("🗜️ Reversed GZIP compression", output_size=len(result))
            elif op == FoundationOp.BZIP2:
                bzip2_compressor = Bzip2Compressor(level=9)
                result = bzip2_compressor.decompress_bytes(result)
                logger.trace("🗜️ Reversed BZIP2 compression", output_size=len(result))
            elif op == FoundationOp.XZ:
                xz_compressor = XzCompressor()
                result = xz_compressor.decompress_bytes(result)
                logger.trace("🗜️ Reversed XZ compression", output_size=len(result))
            elif op == FoundationOp.ZSTD:
                try:
                    zstd_compressor = ZstdCompressor()
                    result = zstd_compressor.decompress_bytes(result)
                    logger.trace("🗜️ Reversed ZSTD compression", output_size=len(result))
                except ImportError as e:
                    logger.error("❌ ZSTD library not available for decompression")
                    raise ArchiveError(
                        "ZSTD decompression required but zstandard library not installed. "
                        "Install with: pip install provide-foundation[compression]"
                    ) from e
            else:
                logger.warning(f"⚠️ Unsupported operation for reversal: {op}")

        logger.debug(
            "✅ Operations reversed successfully",
            input_size=len(data),
            output_size=len(result),
            expansion_ratio=f"{len(result) / len(data):.2f}" if len(data) > 0 else "N/A",
        )

        return result

    except ValueError:
        raise
    except ArchiveError:
        raise
    except Exception as e:
        logger.error(
            "❌ Failed to reverse operations",
            error=str(e),
            error_type=type(e).__name__,
            operations=f"0x{packed_ops:016x}",
        )
        raise ArchiveError(f"Operation reversal failed: {e}") from e


def create_tar_archive(source: Path, deterministic: bool = True) -> bytes:
    """Create TAR archive from directory using Foundation's TarArchive.

    Args:
        source: Source directory or file
        deterministic: Create reproducible archive

    Returns:
        TAR archive as bytes

    Raises:
        ArchiveError: If archive creation fails
        FileNotFoundError: If source does not exist
    """
    if not source.exists():
        raise FileNotFoundError(f"Source path does not exist: {source}")

    logger.debug(
        "📦 Creating TAR archive",
        source=str(source),
        deterministic=deterministic,
        is_dir=source.is_dir(),
    )

    try:
        tar_impl = TarArchive(deterministic=deterministic)

        # Foundation's TarArchive expects to write to a file
        # Use a BytesIO buffer to capture the output
        with temp_file(suffix=".tar", cleanup=True) as temp_path:
            tar_impl.create(source, temp_path)
            result = temp_path.read_bytes()

        return result

    except ArchiveError:
        raise
    except Exception as e:
        logger.error(
            "❌ Failed to create TAR archive",
            error=str(e),
            error_type=type(e).__name__,
            source=str(source),
        )
        raise ArchiveError(f"TAR creation failed: {e}") from e


def extract_archive(
    data: bytes,
    dest: Path,
    packed_ops: int,
    limits: ArchiveLimits | None = None,
) -> Path:
    """Extract archive data using Foundation's extractors with security limits.

    Args:
        data: Archive data (potentially compressed)
        dest: Destination directory
        packed_ops: Packed PSPF operations to determine format
        limits: Optional extraction limits (uses DEFAULT_LIMITS if None)

    Returns:
        Path to extracted content

    Raises:
        ArchiveError: If extraction fails or violates security limits
        ValueError: If operations are invalid
    """
    if limits is None:
        limits = DEFAULT_LIMITS

    logger.debug(
        "📂 Extracting archive",
        data_size=len(data),
        dest=str(dest),
        operations=f"0x{packed_ops:016x}",
        limits_enabled=limits.enabled,
    )

    try:
        # First, reverse compression operations
        decompressed = reverse_operations(data, packed_ops)

        # Determine if TAR extraction is needed
        pspf_ops = unpack_operations(packed_ops) if packed_ops != 0 else []
        needs_tar_extract = OP_TAR in pspf_ops

        if needs_tar_extract:
            # Extract TAR using Foundation with security limits
            tar_impl = TarArchive()

            # Write decompressed data to temp file, then extract with limits
            with temp_file(suffix=".tar", cleanup=True) as temp_path:
                temp_path.write_bytes(decompressed)
                tar_impl.extract(temp_path, dest, limits=limits)

            logger.debug(
                "✅ TAR extraction complete",
                dest=str(dest),
                file_count=len(list(dest.rglob("*"))),
            )
            return dest

        # Not an archive, just write the data
        output_file = dest / "data"
        dest.mkdir(parents=True, exist_ok=True)
        output_file.write_bytes(decompressed)

        return output_file

    except ArchiveError as e:
        logger.error(
            "❌ Archive extraction failed",
            error=str(e),
            dest=str(dest),
            data_size=len(data),
        )
        raise
    except ValueError as e:
        logger.error(
            "❌ Invalid operation chain",
            error=str(e),
            operations=f"0x{packed_ops:016x}",
        )
        raise
    except Exception as e:
        logger.error(
            "❌ Unexpected extraction error",
            error=str(e),
            error_type=type(e).__name__,
            dest=str(dest),
        )
        raise ArchiveError(f"Extraction failed: {e}") from e


__all__ = [
    "apply_operations",
    "create_tar_archive",
    "extract_archive",
    "map_operations",
    "reverse_operations",
]

# 🌶️📦🔚
