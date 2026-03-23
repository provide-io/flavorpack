#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""PSPF Builder - Functional package builder with immutable patterns.

This module provides both pure functions and a fluent builder interface
for creating PSPF packages."""

import os
from pathlib import Path
import time

from provide.foundation import logger
from provide.foundation.crypto import format_checksum as calculate_checksum

from flavor.config.defaults import (
    ACCESS_AUTO,
    CACHE_NORMAL,
    CAPABILITY_MMAP,
    CAPABILITY_PAGE_ALIGNED,
    CAPABILITY_SIGNED,
)
from flavor.exceptions import BuildError
from flavor.psp.format_2025 import handlers
from flavor.psp.format_2025.constants import (
    DEFAULT_MAX_MEMORY,
    DEFAULT_MIN_MEMORY,
)
from flavor.psp.format_2025.index import PSPFIndex
from flavor.psp.format_2025.keys import resolve_keys
from flavor.psp.format_2025.slots import (
    SlotMetadata,
)
from flavor.psp.format_2025.spec import (
    BuildOptions,
    BuildResult,
    BuildSpec,
    PreparedSlot,
)
from flavor.psp.format_2025.validation import validate_complete
from flavor.psp.format_2025.writer import write_package

# =============================================================================
# Pure Functions
# =============================================================================


def build_package(spec: BuildSpec, output_path: Path) -> BuildResult:
    """
    Pure function to build a PSPF package.

    This is the main entry point for building packages functionally.
    All side effects are contained within this function.

    Args:
        spec: Complete build specification
        output_path: Path where package should be written

    Returns:
        BuildResult with success status and any errors/warnings
    """
    start_time = time.time()

    # Validate specification
    logger.debug(
        "📋🔍📋 Build spec details",
        slot_count=len(spec.slots),
        has_metadata=bool(spec.metadata),
        has_keys=bool(spec.keys),
    )
    errors = validate_complete(spec)
    if errors:
        logger.error("❌🔍🚨 Validation failed", error_count=len(errors))
        for error in errors:
            logger.error("  ❌📋📋 Validation error", error=error)
        return BuildResult(success=False, errors=errors)

    # Resolve keys
    logger.info("🔑🔍🚀 Resolving signing keys")
    logger.trace("🔑🔍📋 Key configuration", has_keys=bool(spec.keys))
    try:
        private_key, public_key = resolve_keys(spec.keys)
    except Exception as e:
        return BuildResult(success=False, errors=[f"🔑 Key resolution failed: {e}"])

    # Prepare slots
    logger.debug("🎰🔍📋 Slot details", slots=[s.id for s in spec.slots])
    try:
        prepared_slots = prepare_slots(spec.slots, spec.options)
    except Exception as e:
        logger.error(f"Failed to prepare slots: {e}")
        raise

    # Write package
    logger.trace(
        "🔧 PSPF package configuration",
        slot_count=len(prepared_slots),
        has_signature=bool(private_key),
    )
    try:
        # Create index
        index = create_index(spec, prepared_slots, public_key)

        # Write package using writer module
        package_size = write_package(spec, output_path, prepared_slots, index, private_key, public_key)
    except Exception as e:
        return BuildResult(success=False, errors=[f"❌ Package writing failed: {e}"])

    # Success!
    duration = time.time() - start_time
    logger.info(
        "✅ Package built successfully",
        duration_seconds=duration,
        size_mb=package_size / 1024 / 1024,
        path=str(output_path),
    )

    return BuildResult(
        success=True,
        package_path=output_path,
        duration_seconds=duration,
        package_size_bytes=package_size,
        metadata={
            "slot_count": len(prepared_slots),
            "compression": spec.options.compression,
        },
    )


def prepare_slots(slots: list[SlotMetadata], options: BuildOptions) -> list[PreparedSlot]:
    """
    Prepare slots for packaging.

    Loads data, applies compression, calculates checksums.

    Args:
        slots: List of slot metadata
        options: Build options controlling compression

    Returns:
        List of prepared slots ready for writing
    """
    prepared = []

    for slot in slots:
        # Load data
        data = _load_slot_data(slot)

        # Get packed operations
        from flavor.psp.format_2025.operations import (
            string_to_operations,
            unpack_operations,
        )

        packed_ops = string_to_operations(slot.operations)
        # Debug: Log what operations we're creating
        unpacked_ops = unpack_operations(packed_ops)
        logger.debug(
            "🔄 Processing slot operations",
            slot_id=slot.id,
            operations_string=slot.operations,
            packed_operations=f"{packed_ops:#018x}",
            unpacked_operations=unpacked_ops,
        )

        # Apply operations to compress/transform data
        logger.trace(
            "🗜️ Applying operations to slot data",
            slot_id=slot.id,
            input_size=len(data),
            operations=unpacked_ops,
        )
        processed_data = _apply_operations(data, packed_ops, options)
        logger.debug(
            "🗜️ Slot compression complete",
            slot_id=slot.id,
            input_size=len(data),
            output_size=len(processed_data) if processed_data != data else len(data),
            compression_ratio=f"{len(processed_data) / len(data):.2f}"
            if processed_data != data and len(data) > 0
            else "1.00",
            operations_applied=len(unpacked_ops),
        )

        # Calculate checksums on the final data that will be written (compressed data)
        # This matches what Rust/Go builders do - checksum the actual slot content
        data_to_checksum = processed_data if processed_data != data else data
        logger.trace(
            "🔍 Computing checksums for slot",
            slot_id=slot.id,
            checksum_data_size=len(data_to_checksum),
            checksum_type="sha256",
        )
        checksum_str = calculate_checksum(data_to_checksum, "sha256")
        # Compute SHA-256 truncated to 8 bytes for binary descriptor
        import hashlib

        hash_bytes = hashlib.sha256(data_to_checksum).digest()[:8]
        checksum_uint64 = int.from_bytes(hash_bytes, byteorder="little")

        logger.debug(
            "🔍 Slot checksum calculation complete",
            slot_id=slot.id,
            checksum_uint64=f"{checksum_uint64:016x}",
            sha256_prefix=checksum_str[:16],
            data_size=len(data_to_checksum),
            processed_data=processed_data is not data,
        )

        # Store prefixed checksum in metadata
        slot.checksum = checksum_str

        prepared.append(
            PreparedSlot(
                metadata=slot,
                data=data,
                compressed_data=processed_data if processed_data != data else None,
                operations=packed_ops,  # Operations packed as integer
                checksum=checksum_uint64,  # Binary descriptor uses SHA-256 (first 8 bytes)
            )
        )

        logger.trace(
            "🎰🔍📋 Slot prepared",
            name=slot.id,
            raw_size=len(data),
            compressed_size=len(processed_data),
            operations=packed_ops,
            operations_hex=f"{packed_ops:#018x}",
            operations_unpacked=unpacked_ops,
            checksum=checksum_str[:8],
        )

    return prepared


def create_index(spec: BuildSpec, slots: list[PreparedSlot], public_key: bytes) -> PSPFIndex:
    """
    Create PSPF index structure.

    Args:
        spec: Build specification with metadata
        slots: Prepared slots with offsets
        public_key: Public key for verification

    Returns:
        Populated PSPFIndex instance
    """
    index = PSPFIndex()

    # Store public key
    index.public_key = public_key

    # Set capabilities based on options
    capabilities = 0
    if spec.options.enable_mmap:
        capabilities |= CAPABILITY_MMAP
    if spec.options.page_aligned:
        capabilities |= CAPABILITY_PAGE_ALIGNED
    capabilities |= CAPABILITY_SIGNED  # Always sign
    index.capabilities = capabilities

    # Set access hints
    index.access_mode = ACCESS_AUTO
    index.cache_strategy = CACHE_NORMAL
    index.max_memory = DEFAULT_MAX_MEMORY
    index.min_memory = DEFAULT_MIN_MEMORY

    # Slot information
    index.slot_count = len(slots)

    return index


# =============================================================================
# Helper Functions (Private)
# =============================================================================


def _load_slot_data(slot: SlotMetadata) -> bytes:
    """Load raw data for a slot."""
    if not slot.source:
        # Empty slot
        return b""

    # Resolve {workenv} if present in source path
    slot_path = Path(slot.source) if slot.source else Path()
    if "{workenv}" in str(slot_path):
        # Priority: 1. FLAVOR_WORKENV_BASE env var, 2. Current working directory
        base_dir = os.environ.get("FLAVOR_WORKENV_BASE", str(Path.cwd()))
        slot_path = Path(str(slot_path).replace("{workenv}", base_dir))
        logger.debug(f"📍 Resolved slot path: {slot.source} -> {slot_path} (base: {base_dir})")

    if not slot_path.exists():
        raise BuildError(f"Slot path does not exist: {slot_path}")

    if slot_path.is_dir():
        # Create tarball for directory using Foundation's TarArchive
        return handlers.create_tar_archive(slot_path, deterministic=True)
    else:
        return slot_path.read_bytes()


def _apply_operations(data: bytes, packed_ops: int, options: BuildOptions) -> bytes:
    """Apply v0 operation chain to data using Foundation handlers.

    Args:
        data: Raw data to process
        packed_ops: Packed v0 operations as 64-bit integer
        options: Build options

    Returns:
        Processed data after applying v0 operations
    """
    # Check if data is already compressed (common issue with pre-compressed files)
    # GZIP magic bytes: 1f 8b 08
    if len(data) >= 3 and data[0:3] == b"\x1f\x8b\x08":
        logger.trace("⚠️ Data appears to be already gzipped, returning as-is to avoid double compression")
        return data

    # Use Foundation handlers to apply operations
    return handlers.apply_operations(
        data=data,
        packed_ops=packed_ops,
        compression_level=options.compression_level,
        deterministic=options.reproducible,
    )


# Package writing is now handled by the writer module


# PSPFBuilder class and mapping functions moved to separate modules

# 🌶️📦🔚
