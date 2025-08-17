#!/usr/bin/env python3
"""
PSPF Builder - Functional package builder with immutable patterns.

This module provides both pure functions and a fluent builder interface
for creating PSPF packages.
"""

import gzip
import hashlib
import io
import json
import struct
import tarfile
import tempfile
import time
import zlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union

import attrs
from pyvider.telemetry import logger

from flavor.exceptions import BuildError
from flavor.utils import get_platform_string
from flavor.psp.format_2025.constants import (
    EMOJI_MAGIC_SIZE, HEADER_SIZE, MAGIC_WAND_EMOJI, PSPF_MAGIC,
    SLOT_DESCRIPTOR_SIZE, PAGE_SIZE, SLOT_ALIGNMENT,
    COMPRESSION_NONE, COMPRESSION_GZIP,
    PURPOSE_DATA, PURPOSE_CODE, PURPOSE_CONFIG, PURPOSE_MEDIA,
    LIFECYCLE_PERMANENT, LIFECYCLE_CACHED, LIFECYCLE_TEMPORARY,
    ACCESS_AUTO, CACHE_NORMAL,
    CAPABILITY_MMAP, CAPABILITY_SIGNED, CAPABILITY_PAGE_ALIGNED,
    DEFAULT_MAX_MEMORY, DEFAULT_MIN_MEMORY
)
from flavor.psp.format_2025.crypto import sign_data
from flavor.psp.format_2025.index import PSPFIndex
from flavor.psp.format_2025.slots import SlotDescriptor, SlotMetadata, align_offset, align_to_page
from flavor.psp.format_2025.spec import (
    BuildSpec, BuildResult, BuildOptions, KeyConfig, PreparedSlot
)
from flavor.psp.format_2025.validation import validate_complete
from flavor.psp.format_2025.keys import resolve_keys


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
    logger.info("🔍 Validating build specification...")
    errors = validate_complete(spec)
    if errors:
        logger.error(f"❌ Validation failed with {len(errors)} errors")
        for error in errors:
            logger.error(f"  {error}")
        return BuildResult(success=False, errors=errors)
    
    # Resolve keys
    logger.info("🔑 Resolving signing keys...")
    try:
        private_key, public_key = resolve_keys(spec.keys)
    except Exception as e:
        return BuildResult(success=False, errors=[f"🔑 Key resolution failed: {e}"])
    
    # Prepare slots
    logger.info(f"📦 Preparing {len(spec.slots)} slots...")
    try:
        prepared_slots = prepare_slots(spec.slots, spec.options)
    except Exception as e:
        return BuildResult(success=False, errors=[f"📦 Slot preparation failed: {e}"])
    
    # Write package
    logger.info(f"✍️ Writing package to {output_path}...")
    try:
        package_size = _write_package(
            spec, output_path, prepared_slots, private_key, public_key
        )
    except Exception as e:
        return BuildResult(success=False, errors=[f"❌ Package writing failed: {e}"])
    
    # Success!
    duration = time.time() - start_time
    logger.info(f"✅ Package built successfully in {duration:.2f}s ({package_size / 1024 / 1024:.1f} MB)")
    
    return BuildResult(
        success=True,
        package_path=output_path,
        duration_seconds=duration,
        package_size_bytes=package_size,
        metadata={
            "slot_count": len(prepared_slots),
            "launcher_type": spec.options.launcher_type,
            "compression": spec.options.compression
        }
    )


def prepare_slots(
    slots: List[SlotMetadata],
    options: BuildOptions
) -> List[PreparedSlot]:
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
        
        # Apply compression if needed
        compressed_data, compression_type = _compress_data(
            data, slot.encoding, options
        )
        
        # Calculate checksum
        checksum = zlib.adler32(compressed_data)
        
        prepared.append(
            PreparedSlot(
                metadata=slot,
                data=data,
                compressed_data=compressed_data if compressed_data != data else None,
                compression_type=compression_type,
                checksum=checksum
            )
        )
        
        logger.debug(
            f"   📍 Slot '{slot.name}': "
            f"{len(data)} bytes → {len(compressed_data)} bytes "
            f"(compression: {compression_type})"
        )
    
    return prepared


def create_index(
    spec: BuildSpec,
    slots: List[PreparedSlot],
    public_key: bytes
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
    if not slot.path:
        # Empty slot
        return b""
    
    if not slot.path.exists():
        raise BuildError(f"Slot path does not exist: {slot.path}")
    
    if slot.path.is_dir():
        # Create tarball for directory
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as tar:
            tar.add(slot.path, arcname=".")
        buffer.seek(0)
        return buffer.read()
    else:
        return slot.path.read_bytes()


def _compress_data(
    data: bytes,
    encoding: str,
    options: BuildOptions
) -> Tuple[bytes, int]:
    """Compress data according to encoding and options."""
    if encoding == "none" or options.compression == "none":
        return data, COMPRESSION_NONE
    
    if encoding == "gzip" or options.compression == "gzip":
        compressed = gzip.compress(data, compresslevel=options.compression_level)
        # Only use compression if it actually saves space
        if len(compressed) < len(data):
            return compressed, COMPRESSION_GZIP
    
    # TODO: Support zstd and brotli
    
    return data, COMPRESSION_NONE


def _get_launcher(launcher_type: str) -> bytes:
    """Get launcher binary for the specified type."""
    platform_str = get_platform_string()
    
    # Map launcher types to binary names
    launcher_map = {
        "rust": "flavor-rs-launcher",
        "go": "flavor-go-launcher",
        "python": "flavor-rs-launcher",  # Python uses Rust launcher
        "node": "flavor-rs-launcher",    # Node uses Rust launcher
    }
    
    launcher_name = launcher_map.get(launcher_type, "flavor-rs-launcher")
    
    # Search paths
    search_paths = [
        Path.cwd() / "workenv" / "flavors" / platform_str / launcher_name,
        Path.cwd() / "helpers" / "bin" / launcher_name,
        Path.home() / ".cache" / "flavor" / "bin" / launcher_name,
        Path.cwd() / launcher_name,
    ]
    
    for path in search_paths:
        if path.exists():
            logger.debug(f"🚀 Loading {launcher_type} launcher from {path}")
            return path.read_bytes()
    
    raise FileNotFoundError(
        f"Could not find {launcher_name} binary. "
        f"Build it first with 'flavor helpers build'"
    )


def _write_package(
    spec: BuildSpec,
    output_path: Path,
    slots: List[PreparedSlot],
    private_key: bytes,
    public_key: bytes
) -> int:
    """
    Write the complete package file.
    
    Returns the total package size in bytes.
    """
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Get launcher
    launcher_data = _get_launcher(spec.options.launcher_type)
    launcher_size = len(launcher_data)
    
    # Create index
    index = create_index(spec, slots, public_key)
    index.launcher_size = launcher_size
    
    # Create metadata JSON
    metadata = {
        "format": "PSPF/2025",
        "version": "1.0.0",
        **spec.metadata,
        "slots": [slot.metadata.to_dict() for slot in slots]
    }
    metadata_json = json.dumps(metadata, indent=2).encode('utf-8')
    
    # Sign metadata
    signature = sign_data(metadata_json, private_key)
    padded_signature = signature + b'\x00' * (512 - 64)
    index.integrity_signature = padded_signature
    
    # Compress metadata
    metadata_compressed = gzip.compress(metadata_json)
    
    # Write package
    with open(output_path, "wb") as f:
        # Write launcher
        f.write(launcher_data)
        
        # Reserve space for index
        index_offset = launcher_size
        f.seek(index_offset + HEADER_SIZE)
        
        # Write metadata
        metadata_offset = f.tell()
        f.write(metadata_compressed)
        
        index.metadata_offset = metadata_offset
        index.metadata_size = len(metadata_compressed)
        checksum = zlib.adler32(metadata_compressed)
        index.metadata_checksum = checksum.to_bytes(4, 'little') + b'\x00' * 28
        
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
                        f.write(b'\x00' * (aligned - current))
                
                slot_offset = f.tell()
                data_to_write = slot.get_data_to_write()
                f.write(data_to_write)
                
                # Create descriptor
                descriptor = SlotDescriptor(
                    id=i,
                    name=slot.metadata.name,
                    offset=slot_offset,
                    size=len(data_to_write),
                    original_size=len(slot.data),
                    checksum=slot.checksum,
                    compression=slot.compression_type,
                    purpose=_map_purpose(slot.metadata.purpose),
                    lifecycle=_map_lifecycle(slot.metadata.lifecycle),
                    permissions=0o644,
                    alignment=PAGE_SIZE if spec.options.page_aligned else SLOT_ALIGNMENT
                )
                descriptors.append(descriptor)
            
            # Write descriptor table
            end_of_slots = f.tell()
            f.seek(slot_table_offset)
            for descriptor in descriptors:
                f.write(descriptor.pack())
            f.seek(end_of_slots)
        
        # Write trailing magic
        f.write('📦🪄'.encode('utf-8'))
        
        # Update package size
        index.package_size = f.tell()
        
        # Calculate index checksum
        index_data = index.pack()
        checksum_data = bytearray(index_data)
        checksum_data[12:16] = b'\x00\x00\x00\x00'
        index.index_checksum = zlib.adler32(checksum_data)
        
        # Write final index
        f.seek(index_offset)
        f.write(index.pack())
    
    return index.package_size


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
        "permanent": LIFECYCLE_PERMANENT,
        "persistent": LIFECYCLE_PERMANENT,
        "runtime": LIFECYCLE_PERMANENT,
        "cached": LIFECYCLE_CACHED,
        "cache": LIFECYCLE_CACHED,
        "volatile": LIFECYCLE_CACHED,
        "temporary": LIFECYCLE_TEMPORARY,
        "temp": LIFECYCLE_TEMPORARY,
        "install": LIFECYCLE_TEMPORARY,
        "init": LIFECYCLE_TEMPORARY,
        "startup": LIFECYCLE_CACHED,
        "shutdown": LIFECYCLE_TEMPORARY,
        "lazy": LIFECYCLE_CACHED,
        "eager": LIFECYCLE_PERMANENT,
        "dev": LIFECYCLE_TEMPORARY,
        "config": LIFECYCLE_PERMANENT,
        "platform": LIFECYCLE_CACHED,
    }
    return mapping.get(lifecycle, LIFECYCLE_CACHED)


# =============================================================================
# Fluent Builder Interface
# =============================================================================

class PSPFBuilder:
    """
    Immutable fluent builder interface for PSPF packages.
    
    Provides a chainable API for constructing build specifications.
    """
    
    def __init__(self, spec: Optional[BuildSpec] = None):
        """Initialize with optional starting specification."""
        self._spec = spec or BuildSpec()
    
    @classmethod
    def create(cls) -> 'PSPFBuilder':
        """Create a new builder instance."""
        return cls()
    
    def metadata(self, **kwargs) -> 'PSPFBuilder':
        """
        Set metadata fields.
        
        Merges provided kwargs with existing metadata.
        """
        new_spec = self._spec.with_metadata(**kwargs)
        return PSPFBuilder(new_spec)
    
    def add_slot(
        self,
        name: str,
        data: Union[bytes, str, Path],
        purpose: str = "data",
        lifecycle: str = "runtime",
        encoding: str = "gzip"
    ) -> 'PSPFBuilder':
        """
        Add a slot to the package.
        
        Args:
            name: Slot name
            data: Slot data (bytes, string, or path to file/directory)
            purpose: Slot purpose (data, code, config, media)
            lifecycle: Slot lifecycle (runtime, cached, temporary)
            encoding: Compression encoding (none, gzip)
        """
        # Determine path and size
        if isinstance(data, bytes):
            # Write to temp file
            temp_path = Path(tempfile.mktemp())
            temp_path.write_bytes(data)
            path = temp_path
            size = len(data)
        elif isinstance(data, str):
            # Write string to temp file
            temp_path = Path(tempfile.mktemp())
            temp_path.write_text(data)
            path = temp_path
            size = len(data.encode('utf-8'))
        elif isinstance(data, Path):
            path = data
            size = path.stat().st_size if path.exists() else 0
        else:
            raise ValueError(f"Invalid data type: {type(data)}")
        
        # Create slot metadata
        slot = SlotMetadata(
            index=len(self._spec.slots),
            name=name,
            size=size,
            checksum="",  # Will be calculated during build
            encoding=encoding,
            purpose=purpose,
            lifecycle=lifecycle,
            path=path
        )
        
        new_spec = self._spec.with_slot(slot)
        return PSPFBuilder(new_spec)
    
    def with_keys(
        self,
        seed: Optional[str] = None,
        private: Optional[bytes] = None,
        public: Optional[bytes] = None,
        path: Optional[Path] = None
    ) -> 'PSPFBuilder':
        """
        Configure signing keys.
        
        Args:
            seed: Seed for deterministic key generation
            private: Explicit private key bytes
            public: Explicit public key bytes
            path: Path to load keys from
        """
        key_config = KeyConfig(
            private_key=private,
            public_key=public,
            key_seed=seed,
            key_path=path
        )
        new_spec = self._spec.with_keys(key_config)
        return PSPFBuilder(new_spec)
    
    def with_options(self, **kwargs) -> 'PSPFBuilder':
        """
        Set build options.
        
        Supported options:
        - enable_mmap: Enable memory-mapped access
        - page_aligned: Align slots to page boundaries
        - strip_binaries: Strip debug symbols from binaries
        - compression: Compression type (none, gzip)
        - compression_level: Compression level (0-9)
        - launcher_type: Launcher type (rust, go)
        - reproducible: Enable reproducible builds
        """
        # Create new options with updates
        current_options = self._spec.options
        new_options = attrs.evolve(current_options, **kwargs)
        new_spec = self._spec.with_options(new_options)
        return PSPFBuilder(new_spec)
    
    def build(self, output_path: Union[str, Path]) -> BuildResult:
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