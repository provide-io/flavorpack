#!/usr/bin/env python3
"""
PSPF Builder - Functional package builder with immutable patterns.

This module provides both pure functions and a fluent builder interface
for creating PSPF packages.
"""

import gzip
import io
import json
from pathlib import Path
import tarfile
import tempfile
import time
import zlib

import attrs
from pyvider.telemetry import logger

from flavor.exceptions import BuildError
from flavor.psp.format_2025.checksums import calculate_checksum
from flavor.psp.format_2025.constants import (
    ACCESS_AUTO,
    CACHE_NORMAL,
    CAPABILITY_MMAP,
    CAPABILITY_PAGE_ALIGNED,
    CAPABILITY_SIGNED,
    DEFAULT_EXECUTABLE_PERMS,
    DEFAULT_FILE_PERMS,
    DEFAULT_MAX_MEMORY,
    DEFAULT_MIN_MEMORY,
    ENCODING_GZIP,
    ENCODING_RAW,
    ENCODING_TAR,
    ENCODING_TGZ,
    HEADER_SIZE,
    LIFECYCLE_CACHE,
    LIFECYCLE_CONFIG,
    LIFECYCLE_DEV,
    LIFECYCLE_EAGER,
    LIFECYCLE_INIT,
    LIFECYCLE_LAZY,
    LIFECYCLE_PLATFORM,
    LIFECYCLE_RUNTIME,
    LIFECYCLE_SHUTDOWN,
    LIFECYCLE_STARTUP,
    LIFECYCLE_TEMPORARY,
    MAGIC_TRAILER_SIZE,
    MAGIC_WAND_EMOJI_BYTES,
    PACKAGE_EMOJI_BYTES,
    PAGE_SIZE,
    PURPOSE_CODE,
    PURPOSE_CONFIG,
    PURPOSE_DATA,
    PURPOSE_MEDIA,
    SLOT_ALIGNMENT,
    SLOT_DESCRIPTOR_SIZE,
)
from flavor.psp.format_2025.crypto import sign_data
from flavor.psp.format_2025.index import PSPFIndex
from flavor.psp.format_2025.keys import resolve_keys
from flavor.psp.format_2025.metadata.assembly import (
    assemble_metadata,
)
from flavor.psp.format_2025.slots import (
    SlotDescriptor,
    SlotMetadata,
)
from flavor.utils.alignment import align_offset, align_to_page
from flavor.psp.format_2025.spec import (
    BuildOptions,
    BuildResult,
    BuildSpec,
    KeyConfig,
    PreparedSlot,
)
from flavor.psp.format_2025.validation import validate_complete
from flavor.utils.archive import deterministic_filter
from flavor.utils.permissions import parse_permissions, set_file_permissions

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
    logger.info("🔍🏗️🚀 Validating build specification")
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
    logger.debug("✅🔍📋 Validation passed")

    # Resolve keys
    logger.info("🔑🔍🚀 Resolving signing keys")
    logger.trace("🔑🔍📋 Key configuration", has_keys=bool(spec.keys))
    try:
        private_key, public_key = resolve_keys(spec.keys)
    except Exception as e:
        return BuildResult(success=False, errors=[f"🔑 Key resolution failed: {e}"])

    # Prepare slots
    logger.info("📦🏗️🚀 Preparing slots", slot_count=len(spec.slots))
    logger.debug("🎰🔍📋 Slot details", slots=[s.id for s in spec.slots])
    try:
        prepared_slots = prepare_slots(spec.slots, spec.options)
        logger.debug("🎰✅📋 Slots prepared", prepared_count=len(prepared_slots))
    except Exception as e:
        logger.error("📦🏗️❌ Slot preparation failed", error=str(e))
        return BuildResult(success=False, errors=[f"📦 Slot preparation failed: {e}"])

    # Write package
    logger.info("✍️🏗️🚀 Writing package", output=str(output_path))
    logger.trace(
        "📦🔍📋 Package assembly details",
        slot_count=len(prepared_slots),
        has_signature=bool(private_key),
    )
    try:
        package_size = _write_package(
            spec, output_path, prepared_slots, private_key, public_key
        )
        logger.debug("✍️✅📋 Package written", size_bytes=package_size)
    except Exception as e:
        logger.error("✍️🏗️❌ Package writing failed", error=str(e))
        return BuildResult(success=False, errors=[f"❌ Package writing failed: {e}"])

    # Success!
    duration = time.time() - start_time
    logger.info(
        "✅🏗️🎉 Package built successfully",
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


def prepare_slots(
    slots: list[SlotMetadata], options: BuildOptions
) -> list[PreparedSlot]:
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

        # Determine encoding (no compression, just metadata)
        slot_data, encoding_type = _determine_encoding(data, slot.encoding, options)

        # Calculate checksums with prefixes
        checksum_str = calculate_checksum(slot_data, "sha256")
        checksum_adler32 = zlib.adler32(slot_data)

        # Store prefixed checksum in metadata
        slot.checksum = checksum_str

        prepared.append(
            PreparedSlot(
                metadata=slot,
                data=data,
                compressed_data=slot_data if slot_data != data else None,
                encoding_type=encoding_type,  # Now encoding type, not compression
                checksum=checksum_adler32,  # Binary descriptor uses raw Adler-32
            )
        )

        logger.trace(
            "🎰🔍📋 Slot prepared",
            name=slot.id,
            raw_size=len(data),
            compressed_size=len(slot_data),
            encoding=encoding_type,
            checksum=checksum_str[:8],
        )

    return prepared


def create_index(
    spec: BuildSpec, slots: list[PreparedSlot], public_key: bytes
) -> PSPFIndex:
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
        import os

        # Priority: 1. FLAVOR_WORKENV_BASE env var, 2. Current working directory
        base_dir = os.environ.get("FLAVOR_WORKENV_BASE", os.getcwd())
        slot_path = Path(str(slot_path).replace("{workenv}", base_dir))
        logger.debug(
            f"📍 Resolved slot path: {slot.source} -> {slot_path} (base: {base_dir})"
        )

    if not slot_path.exists():
        raise BuildError(f"Slot path does not exist: {slot_path}")

    if slot_path.is_dir():
        # Create tarball for directory deterministically
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as tar:
            # Add files in a sorted, deterministic order
            for path_item in sorted(slot_path.rglob("*")):
                arcname = path_item.relative_to(slot_path)
                tar.add(path_item, arcname=arcname, filter=deterministic_filter)
        buffer.seek(0)
        return buffer.read()
    else:
        return slot_path.read_bytes()


def _determine_encoding(
    data: bytes, encoding: str, options: BuildOptions
) -> tuple[bytes, int]:
    """Determine encoding constant for the data format.

    Note: This does NOT compress data - the orchestrator/packer handles that.
    We just map the encoding string to the appropriate constant.
    """
    encoding_lower = encoding.lower()

    # Map encoding strings to constants
    if encoding_lower in ("none", "raw", ""):
        return data, ENCODING_RAW
    elif encoding_lower == "tar":
        return data, ENCODING_TAR
    elif encoding_lower == "gzip":
        return data, ENCODING_GZIP
    elif encoding_lower in ("tgz", "tar.gz"):
        return data, ENCODING_TGZ
    # Future formats (not implemented yet):
    # elif encoding_lower == "zstd":
    #     return data, ENCODING_ZSTD
    # elif encoding_lower in ("tzst", "tar.zst"):
    #     return data, ENCODING_TZST
    # elif encoding_lower == "brotli":
    #     return data, ENCODING_BROTLI
    # elif encoding_lower in ("tbr", "tar.br"):
    #     return data, ENCODING_TBR
    # elif encoding_lower == "zip":
    #     return data, ENCODING_ZIP
    # elif encoding_lower == "7z":
    #     return data, ENCODING_7Z
    else:
        logger.warning(f"Unknown encoding '{encoding}', using ENCODING_RAW")
        return data, ENCODING_RAW


def _write_package(
    spec: BuildSpec,
    output_path: Path,
    slots: list[PreparedSlot],
    private_key: bytes,
    public_key: bytes,
) -> int:
    """
    Write the complete package file.

    Returns the total package size in bytes.
    """
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Get launcher binary
    if spec.options.launcher_bin:
        launcher_data = spec.options.launcher_bin.read_bytes()
    else:
        # Default to rust launcher
        from flavor.psp.format_2025.metadata.assembly import load_launcher_binary

        launcher_data = load_launcher_binary("rust")

    launcher_size = len(launcher_data)
    logger.trace(
        "🚀📏📋 Launcher loaded",
        size=launcher_size,
        has_binary=bool(spec.options.launcher_bin),
    )

    # Create launcher info for metadata
    from flavor.psp.format_2025.metadata.assembly import (
        calculate_checksum,
        extract_launcher_version,
    )

    launcher_info = {
        "data": launcher_data,
        "tool": "launcher",  # Will be detected at runtime
        "tool_version": extract_launcher_version(launcher_data),
        "checksum": calculate_checksum(launcher_data, "sha256"),
        "capabilities": ["mmap", "async", "sandbox"],  # Generic capabilities
    }

    # Create index
    index = create_index(spec, slots, public_key)
    index.launcher_size = launcher_size

    # Assemble complete metadata using the new assembly function
    metadata = assemble_metadata(spec, slots, launcher_info)
    metadata_json = json.dumps(metadata, indent=2).encode("utf-8")

    # Sign metadata
    signature = sign_data(metadata_json, private_key)
    padded_signature = signature + b"\x00" * (512 - 64)
    index.integrity_signature = padded_signature

    # Compress metadata
    metadata_compressed = gzip.compress(metadata_json, mtime=0)

    # Write package
    with output_path.open("wb") as f:
        # Write launcher
        f.write(launcher_data)

        # Start right after launcher (no index reservation - index goes in MagicTrailer)
        f.seek(launcher_size)

        # Write metadata
        metadata_offset = f.tell()
        logger.debug(f"Metadata offset: {metadata_offset}, size: {len(metadata_compressed)}")
        f.write(metadata_compressed)
        logger.debug(f"Position after metadata: {f.tell()}")

        index.metadata_offset = metadata_offset
        index.metadata_size = len(metadata_compressed)
        checksum = zlib.adler32(metadata_compressed)
        index.metadata_checksum = checksum.to_bytes(4, "little") + b"\x00" * 28

        # Write slot descriptors and data
        if slots:
            # Slot table position
            slot_table_offset = align_offset(f.tell(), SLOT_ALIGNMENT)
            index.slot_table_offset = slot_table_offset
            index.slot_table_size = len(slots) * SLOT_DESCRIPTOR_SIZE

            # Reserve space for slot table
            f.seek(slot_table_offset + index.slot_table_size)

            # Write slot data
            descriptors = []
            for i, slot in enumerate(slots):
                # Align if needed
                if spec.options.page_aligned and i > 0:
                    current = f.tell()
                    aligned = align_to_page(current)
                    if aligned > current:
                        f.write(b"\x00" * (aligned - current))

                slot_offset = f.tell()
                data_to_write = slot.get_data_to_write()
                f.write(data_to_write)

                # Create descriptor
                # Parse permissions from metadata or use default
                slot_permissions = parse_permissions(slot.metadata.permissions)

                descriptor = SlotDescriptor(
                    id=i,
                    name=slot.metadata.id,
                    offset=slot_offset,
                    size=len(data_to_write),
                    original_size=len(slot.data),
                    checksum=slot.checksum,
                    encoding=slot.encoding_type,  # Using encoding field now
                    purpose=_map_purpose(slot.metadata.purpose),
                    lifecycle=_map_lifecycle(slot.metadata.lifecycle),
                    permissions=slot_permissions,
                    alignment=PAGE_SIZE
                    if spec.options.page_aligned
                    else SLOT_ALIGNMENT,
                )
                descriptors.append(descriptor)

            # Write descriptor table
            end_of_slots = f.tell()
            f.seek(slot_table_offset)
            for descriptor in descriptors:
                f.write(descriptor.pack())
            f.seek(end_of_slots)

        # Update package size before writing MagicTrailer
        # (add 8200 for the trailer that will be written)
        current_pos = f.tell()
        logger.debug(f"Position before MagicTrailer: {current_pos}")
        index.package_size = current_pos + MAGIC_TRAILER_SIZE

        # Write MagicTrailer (8200 bytes: 📦 + index + 🪄)
        f.write(PACKAGE_EMOJI_BYTES)  # 4-byte package emoji
        index_data = index.pack()  # pack() calculates checksum internally
        logger.debug(f"Writing index with format_version: 0x{index.format_version:08x}")
        logger.debug(f"Index data first 16 bytes: {index_data[:16].hex()}")
        f.write(index_data)  # 8192-byte index
        f.write(MAGIC_WAND_EMOJI_BYTES)  # 4-byte magic wand emoji
        
        # Get actual file size after writing
        actual_size = f.tell()

    # Set the output file as executable (user only for security)
    set_file_permissions(output_path, DEFAULT_EXECUTABLE_PERMS)
    logger.trace(
        "🔧📝📋 Set output file as executable",
        path=str(output_path),
        mode=oct(output_path.stat().st_mode),
    )

    return actual_size


def _map_purpose(purpose: str) -> int:
    """Map purpose string to constant."""
    mapping = {
        "data": PURPOSE_DATA,
        "payload": PURPOSE_DATA,
        "code": PURPOSE_CODE,
        "runtime": PURPOSE_CODE,
        "config": PURPOSE_CONFIG,
        "tool": PURPOSE_CONFIG,
        "media": PURPOSE_MEDIA,
        "asset": PURPOSE_MEDIA,
        "library": PURPOSE_CODE,
        "binary": PURPOSE_CODE,
        "installer": PURPOSE_CONFIG,
    }
    return mapping.get(purpose, PURPOSE_DATA)


def _map_lifecycle(lifecycle: str) -> int:
    """Map lifecycle string to constant."""
    mapping = {
        "init": LIFECYCLE_INIT,
        "startup": LIFECYCLE_STARTUP,
        "runtime": LIFECYCLE_RUNTIME,
        "shutdown": LIFECYCLE_SHUTDOWN,
        "cache": LIFECYCLE_CACHE,
        "temporary": LIFECYCLE_TEMPORARY,
        "lazy": LIFECYCLE_LAZY,
        "eager": LIFECYCLE_EAGER,
        "dev": LIFECYCLE_DEV,
        "config": LIFECYCLE_CONFIG,
        "platform": LIFECYCLE_PLATFORM,
    }
    return mapping.get(lifecycle, LIFECYCLE_RUNTIME)


# =============================================================================
# Fluent Builder Interface
# =============================================================================


class PSPFBuilder:
    """
    Immutable fluent builder interface for PSPF packages.

    Provides a chainable API for constructing build specifications.
    """

    def __init__(self, spec: BuildSpec | None = None) -> None:
        """Initialize with optional starting specification."""
        self._spec = spec or BuildSpec()

    @classmethod
    def create(cls) -> "PSPFBuilder":
        """Create a new builder instance."""
        return cls()

    def metadata(self, **kwargs) -> "PSPFBuilder":
        """
        Set metadata fields.

        Merges provided kwargs with existing metadata.
        """
        new_spec = self._spec.with_metadata(**kwargs)
        return PSPFBuilder(new_spec)

    def add_slot(
        self,
        id: str,
        data: bytes | str | Path,
        purpose: str = "data",
        lifecycle: str = "runtime",
        encoding: str = "gzip",
        target: str | None = None,
        permissions: str | None = None,
    ) -> "PSPFBuilder":
        """
        Add a slot to the package.

        Args:
            id: Slot identifier
            data: Slot data (bytes, string, or path to file/directory)
            purpose: Slot purpose (data, code, config, media)
            lifecycle: Slot lifecycle (runtime, cached, temporary)
            encoding: Compression encoding (none, gzip)
            target: Target location relative to workenv (default: None)
            permissions: Unix permissions as octal string (e.g., "0755")
        """
        # Determine path and size
        if isinstance(data, bytes):
            # Write to temp file securely
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(data)
                temp_path = Path(temp_file.name)
            path = temp_path
            size = len(data)
        elif isinstance(data, str):
            # Write string to temp file securely
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, encoding="utf-8"
            ) as temp_file:
                temp_file.write(data)
                temp_path = Path(temp_file.name)
            path = temp_path
            size = len(data.encode("utf-8"))
        elif isinstance(data, Path):
            path = data
            size = path.stat().st_size if path.exists() else 0
        else:
            raise BuildError(f"Invalid data type: {type(data)}")

        # Create slot metadata
        slot = SlotMetadata(
            index=len(self._spec.slots),
            id=id,
            source=str(path) if path else "",
            target=target or id,
            size=size,
            checksum="",  # Will be calculated during build
            encoding=encoding,
            purpose=purpose,
            lifecycle=lifecycle,
            permissions=permissions,
        )

        new_spec = self._spec.with_slot(slot)
        return PSPFBuilder(new_spec)

    def with_keys(
        self,
        seed: str | None = None,
        private: bytes | None = None,
        public: bytes | None = None,
        path: Path | None = None,
    ) -> "PSPFBuilder":
        """
        Configure signing keys.

        Args:
            seed: Seed for deterministic key generation
            private: Explicit private key bytes
            public: Explicit public key bytes
            path: Path to load keys from
        """
        key_config = KeyConfig(
            private_key=private, public_key=public, key_seed=seed, key_path=path
        )
        new_spec = self._spec.with_keys(key_config)
        return PSPFBuilder(new_spec)

    def with_options(self, **kwargs) -> "PSPFBuilder":
        """
        Set build options.

        Supported options:
        - enable_mmap: Enable memory-mapped access
        - page_aligned: Align slots to page boundaries
        - strip_binaries: Strip debug symbols from binaries
        - compression: Compression type (none, gzip)
        - compression_level: Compression level (0-9)
        - launcher_bin: Path to launcher binary
        - reproducible: Enable reproducible builds
        """
        # Create new options with updates
        current_options = self._spec.options
        new_options = attrs.evolve(current_options, **kwargs)
        new_spec = self._spec.with_options(new_options)
        return PSPFBuilder(new_spec)

    def build(self, output_path: str | Path) -> BuildResult:
        """
        Build the package.

        Args:
            output_path: Path where package should be written

        Returns:
            BuildResult with success status and any errors
        """
        if isinstance(output_path, str):
            output_path = Path(output_path)

        return build_package(self._spec, output_path)
