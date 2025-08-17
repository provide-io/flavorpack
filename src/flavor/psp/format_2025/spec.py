#!/usr/bin/env python3
"""
PSPF Build Specification - Immutable data structures for package building.

This module defines the core data structures used throughout the PSPF builder
system, emphasizing immutability and functional programming patterns.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import attrs
from attrs import define, field, validators

from flavor.psp.format_2025.slots import SlotMetadata


@define(frozen=True)
class KeyConfig:
    """
    Immutable key configuration for package signing.
    
    Supports multiple key sources with clear priority:
    1. Explicit keys (highest priority)
    2. Deterministic from seed
    3. Load from filesystem path
    4. Generate ephemeral (default)
    """
    
    private_key: Optional[bytes] = field(default=None)
    public_key: Optional[bytes] = field(default=None)
    key_seed: Optional[str] = field(default=None)
    key_path: Optional[Path] = field(default=None)
    
    def has_explicit_keys(self) -> bool:
        """Check if explicit keys are provided."""
        return self.private_key is not None and self.public_key is not None
    
    def has_seed(self) -> bool:
        """Check if deterministic seed is provided."""
        return self.key_seed is not None
    
    def has_path(self) -> bool:
        """Check if key path is provided."""
        return self.key_path is not None


@define(frozen=True)
class BuildOptions:
    """
    Immutable build options controlling package generation.
    
    These options affect how the package is built but not what goes into it.
    """
    
    # Memory mapping support
    enable_mmap: bool = field(default=True)
    page_aligned: bool = field(default=True)
    
    # Binary optimization
    strip_binaries: bool = field(default=False)
    
    # Compression settings
    compression: str = field(
        default="gzip",
        validator=validators.in_(["none", "gzip", "zstd", "brotli"])
    )
    compression_level: int = field(default=6, validator=validators.instance_of(int))
    
    # Launcher selection
    launcher_type: str = field(
        default="rust",
        validator=validators.in_(["rust", "go", "python", "node"])
    )
    
    # Build behavior
    reproducible: bool = field(default=False)
    verbose: bool = field(default=False)
    
    def with_compression(self, compression: str, level: Optional[int] = None) -> 'BuildOptions':
        """Return new BuildOptions with updated compression settings."""
        updates = {"compression": compression}
        if level is not None:
            updates["compression_level"] = level
        return attrs.evolve(self, **updates)
    
    def with_launcher(self, launcher_type: str) -> 'BuildOptions':
        """Return new BuildOptions with updated launcher type."""
        return attrs.evolve(self, launcher_type=launcher_type)


@define(frozen=True)
class BuildSpec:
    """
    Immutable build specification containing all information needed to build a package.
    
    This is the central data structure that flows through the build process.
    """
    
    # Package metadata (name, version, description, etc.)
    metadata: Dict[str, Any] = field(factory=dict)
    
    # Slots to include in the package
    slots: List[SlotMetadata] = field(factory=list)
    
    # Key configuration for signing
    keys: KeyConfig = field(factory=KeyConfig)
    
    # Build options
    options: BuildOptions = field(factory=BuildOptions)
    
    def with_metadata(self, **kwargs) -> 'BuildSpec':
        """
        Return new BuildSpec with updated metadata.
        
        Merges provided kwargs with existing metadata.
        """
        new_metadata = {**self.metadata, **kwargs}
        return attrs.evolve(self, metadata=new_metadata)
    
    def with_slot(self, slot: SlotMetadata) -> 'BuildSpec':
        """
        Return new BuildSpec with additional slot.
        
        Appends the slot to the existing list.
        """
        new_slots = [*self.slots, slot]
        return attrs.evolve(self, slots=new_slots)
    
    def with_slots(self, *slots: SlotMetadata) -> 'BuildSpec':
        """
        Return new BuildSpec with multiple additional slots.
        
        Appends all provided slots to the existing list.
        """
        new_slots = [*self.slots, *slots]
        return attrs.evolve(self, slots=new_slots)
    
    def replace_slots(self, slots: List[SlotMetadata]) -> 'BuildSpec':
        """
        Return new BuildSpec with replaced slot list.
        
        Completely replaces the existing slots.
        """
        return attrs.evolve(self, slots=slots)
    
    def with_keys(self, keys: KeyConfig) -> 'BuildSpec':
        """Return new BuildSpec with updated key configuration."""
        return attrs.evolve(self, keys=keys)
    
    def with_options(self, options: BuildOptions) -> 'BuildSpec':
        """Return new BuildSpec with updated build options."""
        return attrs.evolve(self, options=options)
    
    def has_required_metadata(self) -> bool:
        """Check if required metadata fields are present."""
        if not self.metadata:
            return False
        
        # Check for package name (various possible locations)
        has_name = (
            "name" in self.metadata or
            ("package" in self.metadata and "name" in self.metadata["package"])
        )
        
        return has_name


@define(frozen=True)
class BuildResult:
    """
    Immutable result from a build operation.
    
    Contains success status, errors, warnings, and metadata about the build.
    """
    
    success: bool = field(validator=validators.instance_of(bool))
    package_path: Optional[Path] = field(default=None)
    errors: List[str] = field(factory=list)
    warnings: List[str] = field(factory=list)
    metadata: Dict[str, Any] = field(factory=dict)
    
    # Timing information
    duration_seconds: Optional[float] = field(default=None)
    
    # Size information
    package_size_bytes: Optional[int] = field(default=None)
    
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0
    
    def add_error(self, error: str) -> 'BuildResult':
        """Return new BuildResult with additional error."""
        new_errors = [*self.errors, error]
        return attrs.evolve(self, errors=new_errors, success=False)
    
    def add_warning(self, warning: str) -> 'BuildResult':
        """Return new BuildResult with additional warning."""
        new_warnings = [*self.warnings, warning]
        return attrs.evolve(self, warnings=new_warnings)
    
    def with_metadata(self, **kwargs) -> 'BuildResult':
        """Return new BuildResult with updated metadata."""
        new_metadata = {**self.metadata, **kwargs}
        return attrs.evolve(self, metadata=new_metadata)


@define(frozen=True)
class PreparedSlot:
    """
    Immutable representation of a slot that has been prepared for packaging.
    
    Contains the processed data and metadata needed to write the slot.
    """
    
    metadata: SlotMetadata = field(validator=validators.instance_of(SlotMetadata))
    data: bytes = field(validator=validators.instance_of(bytes))
    compressed_data: Optional[bytes] = field(default=None)
    compression_type: int = field(default=0)
    checksum: int = field(default=0)
    offset: Optional[int] = field(default=None)
    
    def with_compression(self, compressed_data: bytes, compression_type: int) -> 'PreparedSlot':
        """Return new PreparedSlot with compression applied."""
        return attrs.evolve(
            self,
            compressed_data=compressed_data,
            compression_type=compression_type
        )
    
    def with_offset(self, offset: int) -> 'PreparedSlot':
        """Return new PreparedSlot with offset set."""
        return attrs.evolve(self, offset=offset)
    
    def get_data_to_write(self) -> bytes:
        """Get the actual data to write (compressed if available)."""
        return self.compressed_data if self.compressed_data else self.data
    
    def get_size(self) -> int:
        """Get the size of data to write."""
        return len(self.get_data_to_write())