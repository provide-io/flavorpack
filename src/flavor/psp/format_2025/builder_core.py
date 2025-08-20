#!/usr/bin/env python3
"""
PSPF Builder Core - Main builder functionality and fluent interface.

Provides the core build_package function and PSPFBuilder fluent interface
for creating PSPF packages.
"""

from pathlib import Path
import tempfile

import attrs
from pyvider.telemetry import logger

from flavor.exceptions import BuildError
from flavor.psp.format_2025.builder_index import create_index
from flavor.psp.format_2025.builder_slots import prepare_slots
from flavor.psp.format_2025.builder_writer import write_package
from flavor.psp.format_2025.constants import INDEX_SIZE, SLOT_DESCRIPTOR_SIZE
from flavor.psp.format_2025.crypto import sign_data
from flavor.psp.format_2025.keys import resolve_keys
from flavor.psp.format_2025.metadata.assembly import assemble_metadata
from flavor.psp.format_2025.slots import SlotMetadata
from flavor.psp.format_2025.spec import (
    BuildOptions,
    BuildResult,
    BuildSpec,
    KeyConfig,
)
from flavor.psp.format_2025.validation import validate_spec


def build_package(spec: BuildSpec, output_path: Path) -> BuildResult:
    """
    Build a PSPF package from specification.
    
    This is the main entry point for package building. It orchestrates:
    1. Specification validation
    2. Key resolution
    3. Launcher selection
    4. Slot preparation
    5. Metadata assembly
    6. Index creation
    7. Package writing
    
    Args:
        spec: Build specification
        output_path: Where to write the package
        
    Returns:
        BuildResult with success status and any errors
    """
    logger.info("🏗️ Building PSPF package")
    
    # Validate specification
    validation_errors = validate_spec(spec)
    if validation_errors:
        return BuildResult(success=False, errors=validation_errors)
    
    try:
        # Resolve keys
        private_key, public_key = resolve_keys(spec.keys)
        
        # Get launcher
        launcher_path = spec.options.launcher_bin
        if isinstance(launcher_path, str):
            launcher_path = Path(launcher_path)
        
        # If no launcher specified, use mocked/default launcher data
        if not launcher_path:
            # For tests, we'll use the mocked launcher data from metadata.assembly
            from flavor.psp.format_2025.metadata.assembly import load_launcher_binary
            launcher_data = load_launcher_binary("rust")  # This will be mocked in tests
            
            # Write to temp file for consistency
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".launcher", delete=False) as f:
                f.write(launcher_data)
                launcher_path = Path(f.name)
            launcher_size = len(launcher_data)
        else:
            if not launcher_path.exists():
                raise BuildError(f"Launcher not found: {launcher_path}")
            launcher_size = launcher_path.stat().st_size
        
        logger.debug(f"🚀 Using launcher: {launcher_path} ({launcher_size} bytes)")
        
        # Prepare slots first to get their data
        # We'll calculate proper offsets after we know metadata size
        # Use a large temporary offset for now
        temp_offset = launcher_size + INDEX_SIZE + 10000  # Temporary offset
        prepared_slots = prepare_slots(spec.slots, temp_offset, spec.options)
        
        # Get launcher info for metadata
        from flavor.psp.format_2025.metadata.assembly import get_launcher_info
        launcher_info = get_launcher_info("rust")  # Get info for metadata
        
        # Now assemble metadata with prepared slots (extract PreparedSlot from wrapper)
        metadata = assemble_metadata(
            spec=spec,
            slots=[s.prepared_slot for s in prepared_slots],
            launcher_info=launcher_info,
        )
        
        # Create metadata archive to get actual size
        import io
        import json
        import tarfile
        import time
        
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
            json_data = json.dumps(metadata, indent=2, sort_keys=True).encode("utf-8")
            json_info = tarfile.TarInfo(name="psp.json")
            json_info.size = len(json_data)
            json_info.mtime = 0 if spec.options.reproducible else int(time.time())
            tar.addfile(json_info, io.BytesIO(json_data))
        
        metadata_size = len(tar_buffer.getvalue())
        
        # Now recalculate actual offsets for slots
        slot_table_offset = launcher_size + INDEX_SIZE + metadata_size
        current_offset = slot_table_offset + (len(spec.slots) * SLOT_DESCRIPTOR_SIZE)
        
        # Update slot descriptors with correct offsets
        for slot in prepared_slots:
            offset_diff = current_offset - slot.descriptor.offset
            slot.descriptor.offset = current_offset
            current_offset += slot.descriptor.size
        
        # Sign metadata if we have a private key
        signature = None
        if private_key:
            # Create signature of metadata
            signature_data = json.dumps(metadata, sort_keys=True).encode("utf-8")
            signature = sign_data(signature_data, private_key)
            logger.debug(f"🔏 Created signature ({len(signature)} bytes)")
        
        # Create index
        index = create_index(
            launcher_size=launcher_size,
            slots=prepared_slots,
            metadata_size=metadata_size,
            signature=signature,
            options=spec.options,
        )
        
        # Write package
        result = write_package(
            output_path=output_path,
            launcher_path=launcher_path,
            index=index,
            metadata=metadata,
            slots=prepared_slots,
            signature=signature,
            options=spec.options,
        )
        
        if result.success:
            logger.info(f"✅ Package built successfully: {output_path}")
        
        return result
        
    except Exception as e:
        import traceback
        error_msg = str(e) if str(e) else f"{type(e).__name__}: {traceback.format_exc()}"
        logger.error(f"❌ Build failed: {error_msg}")
        return BuildResult(success=False, errors=[error_msg])


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
        name: str,
        data: bytes | str | Path,
        purpose: str = "data",
        lifecycle: str = "runtime",
        encoding: str = "gzip",
        extract_to: str | None = None,
    ) -> "PSPFBuilder":
        """
        Add a slot to the package.
        
        Args:
            name: Slot name
            data: Slot data (bytes, string, or path to file/directory)
            purpose: Slot purpose (data, code, config, media)
            lifecycle: Slot lifecycle (runtime, cached, temporary)
            encoding: Compression encoding (none, gzip)
            extract_to: Extract location relative to workenv (default: None)
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
            with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as temp_file:
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
            name=name,
            size=size,
            checksum="",  # Will be calculated during build
            encoding=encoding,
            purpose=purpose,
            lifecycle=lifecycle,
            extract_to=extract_to,
            path=path,
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