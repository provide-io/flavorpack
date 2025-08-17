#!/usr/bin/env python3
# src/flavor/psp/format_2025/builder.py
# PSPF 2025 Bundle Builder - Enhanced format with 512-byte headers

import gzip
import io
import json
import struct
import tarfile
import tempfile
import zlib
from pathlib import Path
from typing import BinaryIO, List, Dict, Any, Optional, Tuple

from pyvider.telemetry import logger

from flavor.utils import get_platform_string
from flavor.psp.format_2025.constants import (
    EMOJI_MAGIC_SIZE, HEADER_SIZE, MAGIC_WAND_EMOJI, PSPF_MAGIC,
    SLOT_DESCRIPTOR_SIZE, PAGE_SIZE, SLOT_ALIGNMENT,
    COMPRESSION_NONE, COMPRESSION_GZIP, COMPRESSION_ZSTD, COMPRESSION_BROTLI,
    PURPOSE_DATA, PURPOSE_CODE, PURPOSE_CONFIG, PURPOSE_MEDIA,
    LIFECYCLE_PERMANENT, LIFECYCLE_CACHED, LIFECYCLE_TEMPORARY,
    ACCESS_AUTO, CACHE_NORMAL, METADATA_JSON,
    CAPABILITY_MMAP, CAPABILITY_SIGNED, CAPABILITY_PAGE_ALIGNED,
    DEFAULT_MAX_MEMORY, DEFAULT_MIN_MEMORY
)
from flavor.psp.format_2025.crypto import generate_key_pair, sign_data
from flavor.psp.format_2025.index import PSPFIndex
from flavor.psp.format_2025.slots import SlotDescriptor, SlotMetadata, align_offset, align_to_page


class PSPFBuilder:
    """Build PSPF bundles with enhanced format."""

    def __init__(self, enable_mmap: bool = True, page_aligned: bool = True):
        """Initialize builder.
        
        Args:
            enable_mmap: Enable memory-mapped access optimizations
            page_aligned: Align slots to page boundaries for optimal mmap
        """
        self.temp_dir = Path(tempfile.mkdtemp())
        self.enable_mmap = enable_mmap
        self.page_aligned = page_aligned

    def build(
        self,
        output_path: Path,
        metadata: Optional[Dict[str, Any]] = None,
        slots: Optional[List[SlotMetadata]] = None,
        launcher_type: str = "rust",
        manifest_path: Optional[Path] = None,
    ) -> None:
        """Build a PSPF bundle with enhanced format.
        
        Args:
            output_path: Output path for bundle
            metadata: Bundle metadata dictionary
            slots: List of slot metadata
            launcher_type: Type of launcher (rust/go)
            manifest_path: Path to manifest file
        """
        logger.info(f"🔨 Building PSPF/2025 bundle: {output_path}")

        # Load from manifest if provided
        if manifest_path:
            metadata, slots = self._load_manifest(manifest_path)

        # Ensure metadata has slots array if not provided
        if metadata and "slots" not in metadata and slots:
            metadata["slots"] = [slot.to_dict() for slot in slots]

        # Generate keys for signing
        private_key, public_key = generate_key_pair()

        # Get launcher
        launcher_data = self._get_launcher(launcher_type)
        launcher_size = len(launcher_data)

        # Create enhanced index with 512-byte header
        index = PSPFIndex()
        index.launcher_size = launcher_size
        # Store public key for signature verification
        index.public_key = public_key
        
        # Set capabilities
        capabilities = 0
        if self.enable_mmap:
            capabilities |= CAPABILITY_MMAP
        if self.page_aligned:
            capabilities |= CAPABILITY_PAGE_ALIGNED
        capabilities |= CAPABILITY_SIGNED  # We always sign
        index.capabilities = capabilities
        
        # Set access hints
        index.access_mode = ACCESS_AUTO
        index.cache_strategy = CACHE_NORMAL
        index.max_memory = DEFAULT_MAX_MEMORY
        index.min_memory = DEFAULT_MIN_MEMORY
        
        # Metadata is always gzipped JSON in PSPF/2025

        # Write bundle
        with open(output_path, "wb") as f:
            # Write launcher
            f.write(launcher_data)

            # Reserve space for index/header (512 bytes)
            index_offset = launcher_size
            f.seek(index_offset + HEADER_SIZE)

            # Create and sign metadata
            metadata_offset = f.tell()
            metadata_json, signature = self._create_metadata(metadata, private_key, public_key)
            
            # Store signature in index (Ed25519 signatures are 64 bytes)
            # Pad signature to 512 bytes
            padded_signature = signature + b'\x00' * (512 - 64)
            index.integrity_signature = padded_signature
            
            # Compress metadata (always gzip in PSPF/2025)
            metadata_data = gzip.compress(metadata_json)
            
            f.write(metadata_data)
            
            index.metadata_offset = metadata_offset
            index.metadata_size = len(metadata_data)
            # Store Adler32 checksum as 32-byte field (padded)
            checksum = zlib.adler32(metadata_data)
            index.metadata_checksum = checksum.to_bytes(4, 'little') + b'\x00' * 28

            # Prepare slot descriptors
            descriptors = []
            if slots:
                index.slot_count = len(slots)
                
                # Calculate and set slot table position (right after metadata)
                slot_table_offset = align_offset(f.tell(), SLOT_ALIGNMENT)
                index.slot_table_offset = slot_table_offset
                index.slot_table_size = len(slots) * SLOT_DESCRIPTOR_SIZE
                
                # Reserve space for slot table
                f.seek(slot_table_offset + index.slot_table_size)
                
                # Align to boundary for first slot data
                data_start = align_offset(f.tell(), SLOT_ALIGNMENT)
                f.seek(data_start)
                
                # Write slot data and build descriptors
                for i, slot in enumerate(slots):
                    # Align slot offset if needed
                    if self.page_aligned and i > 0:
                        current = f.tell()
                        aligned = align_to_page(current)
                        if aligned > current:
                            f.write(b'\x00' * (aligned - current))
                    
                    slot_offset = f.tell()
                    
                    # Get and compress slot data
                    slot_data = self._get_slot_data(slot)
                    original_size = len(slot_data)
                    
                    compressed_data, compression_type = self._compress_data(
                        slot_data, slot.encoding
                    )
                    
                    f.write(compressed_data)
                    
                    # Create descriptor
                    descriptor = SlotDescriptor(
                        id=i,
                        name=slot.name,
                        offset=slot_offset,
                        size=len(compressed_data),
                        original_size=original_size,
                        checksum=zlib.adler32(compressed_data),
                        compression=compression_type,
                        purpose=self._get_purpose_value(slot.purpose),
                        lifecycle=self._get_lifecycle_value(slot.lifecycle),
                        permissions=0o644,  # Default permissions
                        alignment=PAGE_SIZE if self.page_aligned else SLOT_ALIGNMENT
                    )
                    
                    descriptors.append(descriptor)
                    
                    logger.trace(
                        f"📍 Slot {i} ({slot.name}): "
                        f"offset={slot_offset}, size={len(compressed_data)}, "
                        f"original={original_size}, compression={compression_type}"
                    )
                
                # Now go back and write the descriptor table
                end_of_slots = f.tell()
                f.seek(slot_table_offset)
                for descriptor in descriptors:
                    f.write(descriptor.pack())
                
                # Return to end of data
                f.seek(end_of_slots)
            
            # Now we're at the correct position (end of all data)
            
            # Write trailing magic with package and wand emojis
            trailing_magic = '📦🪄'
            f.write(trailing_magic.encode('utf-8'))
            
            # Update package size to include trailing magic
            index.package_size = f.tell()

            # Calculate and write index with checksum
            index_data = index.pack()
            
            # Calculate checksum with checksum field zeroed
            checksum_data = bytearray(index_data)
            checksum_data[12:16] = b'\x00\x00\x00\x00'  # Checksum is at offset 12
            index.index_checksum = zlib.adler32(checksum_data)
            
            # Write final index with checksum
            f.seek(index_offset)
            f.write(index.pack())
            
        logger.info(
            f"✅ Built PSPF/2025 bundle: {output_path} "
            f"({index.package_size} bytes, {len(descriptors)} slots)"
        )

    def _get_launcher(self, launcher_type: str) -> bytes:
        """Get launcher binary."""
        platform_str = get_platform_string()
        
        # Map launcher types to actual binary names
        if launcher_type in ["rust", "python", "node", "unknown"]:
            launcher_suffix = "rs"
        else:
            launcher_suffix = launcher_type
        
        # Try to find launcher in workenv
        workenv_dir = Path.cwd() / "workenv" / "flavors" / platform_str
        launcher_name = f"flavor-{launcher_suffix}-launcher"
        launcher_path = workenv_dir / launcher_name
        
        if launcher_path.exists():
            logger.debug(f"🚀 Loading {launcher_type} launcher from {launcher_path}")
            return launcher_path.read_bytes()
        
        # Fallback: try to find in various common locations
        search_paths = [
            Path.cwd() / launcher_name,
            Path(__file__).parent.parent.parent / "go/cmd/pspf-launcher" / launcher_name,
            Path(__file__).parent.parent.parent / f"rust/flavor/target/release/{launcher_name}",
        ]
        
        for path in search_paths:
            if path.exists():
                logger.debug(f"🚀 Loading {launcher_type} launcher from {path}")
                return path.read_bytes()
        
        # If no launcher found, raise error
        raise FileNotFoundError(
            f"Could not find {launcher_name} binary. "
            f"Build it first with 'flavor package'"
        )

    def _create_metadata(
        self, metadata: dict, private_key: bytes, public_key: bytes
    ) -> Tuple[bytes, bytes]:
        """Create metadata JSON and sign it.
        
        Returns:
            tuple: (json_data, signature)
        """
        if metadata is None:
            metadata = {}
        
        # Add format version
        metadata["format"] = "PSPF/2025"
        metadata["version"] = "1.0.0"
        
        # Convert to JSON
        json_data = json.dumps(metadata, indent=2).encode('utf-8')
        
        # Sign the metadata
        signature = sign_data(json_data, private_key)
        
        # Return JSON and signature separately
        return json_data, signature

    def _get_slot_data(self, slot: SlotMetadata) -> bytes:
        """Get raw slot data."""
        if not slot.path or not slot.path.exists():
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

    def _compress_data(self, data: bytes, encoding: str) -> Tuple[bytes, int]:
        """Compress data with specified encoding.
        
        Returns:
            Tuple of (compressed_data, compression_type)
        """
        if encoding == "gzip":
            return gzip.compress(data), COMPRESSION_GZIP
        elif encoding == "zstd":
            # Future: implement zstd
            logger.warning("ZSTD not yet supported, using gzip")
            return gzip.compress(data), COMPRESSION_GZIP
        elif encoding == "brotli":
            # Future: implement brotli
            logger.warning("Brotli not yet supported, using gzip")
            return gzip.compress(data), COMPRESSION_GZIP
        else:
            return data, COMPRESSION_NONE

    def _get_purpose_value(self, purpose: str) -> int:
        """Convert purpose string to integer value."""
        purpose_map = {
            "data": PURPOSE_DATA,
            "payload": PURPOSE_DATA,  # Legacy
            "code": PURPOSE_CODE,
            "runtime": PURPOSE_CODE,  # Legacy
            "config": PURPOSE_CONFIG,
            "tool": PURPOSE_CONFIG,  # Legacy
            "media": PURPOSE_MEDIA,
        }
        return purpose_map.get(purpose, PURPOSE_DATA)

    def _get_lifecycle_value(self, lifecycle: str) -> int:
        """Convert lifecycle string to integer value."""
        lifecycle_map = {
            "permanent": LIFECYCLE_PERMANENT,
            "persistent": LIFECYCLE_PERMANENT,  # Legacy
            "cached": LIFECYCLE_CACHED,
            "volatile": LIFECYCLE_CACHED,  # Legacy
            "temporary": LIFECYCLE_TEMPORARY,
            "install": LIFECYCLE_TEMPORARY,  # Legacy
        }
        return lifecycle_map.get(lifecycle, LIFECYCLE_CACHED)

    def _load_manifest(self, manifest_path: Path) -> Tuple[dict, List[SlotMetadata]]:
        """Load manifest file."""
        import tomllib

        with open(manifest_path, "rb") as f:
            manifest = tomllib.load(f)

        # Create metadata
        metadata = {
            "format": "PSPF/2025",
            "package": {
                "name": manifest.get("name", "unknown"),
                "version": manifest.get("version", "0.0.0"),
                "description": manifest.get("description", ""),
            },
            "build": {
                "timestamp": manifest.get("timestamp", ""),
                "builder": manifest.get("builder", "flavor"),
            }
        }

        # Create slots
        slots = []
        for i, slot_data in enumerate(manifest.get("slots", [])):
            slot_path = Path(slot_data["path"])
            if slot_path.exists():
                slots.append(
                    SlotMetadata(
                        index=i,
                        name=slot_data.get("name", slot_path.stem),
                        size=slot_path.stat().st_size,
                        checksum="",  # Will be calculated
                        encoding=slot_data.get("encoding", "gzip"),
                        purpose=slot_data.get("purpose", "data"),
                        lifecycle=slot_data.get("lifecycle", "cached"),
                        path=slot_path,
                        extract_to=slot_data.get("extract_to"),
                    )
                )

        return metadata, slots


# Convenience function
def build_bundle(
    output_path: Path,
    slots: List[SlotMetadata],
    metadata: Optional[Dict[str, Any]] = None,
    enable_mmap: bool = True,
    page_aligned: bool = True,
) -> None:
    """Build a PSPF bundle.
    
    Args:
        output_path: Output path for bundle
        slots: List of slot metadata
        metadata: Optional metadata dictionary
        enable_mmap: Enable memory-mapped optimizations
        page_aligned: Align slots to page boundaries
    """
    builder = PSPFBuilder(enable_mmap=enable_mmap, page_aligned=page_aligned)
    builder.build(output_path, metadata=metadata, slots=slots)

# 📦🔨🏗️🪄