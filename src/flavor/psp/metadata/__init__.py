"""
Metadata handling for PSP packages.

This module provides:
- Protocol definitions for metadata interfaces
- Attrs models for structured metadata
- Path validation and manipulation
- Type definitions for external APIs
"""

from flavor.psp.metadata.models import (
    DirectorySpec,
    WorkenvSpec,
    RuntimeEnvOps,
    RuntimeSpec,
    ExecutionSpec,
    PackageInfo,
    PSPFMetadata,
)
from flavor.psp.metadata.paths import (
    validate_metadata_path,
    expand_workenv_path,
    make_relative_to_workenv,
    validate_metadata_dict,
    validate_metadata_list,
)
from flavor.psp.metadata.protocols import (
    MetadataValidator,
    PathResolver,
    EnvironmentProcessor,
    MetadataFormat,
)
from flavor.psp.metadata.types import (
    DirectoryDict,
    WorkenvDict,
    RuntimeDict,
    ExecutionDict,
    PackageDict,
    PSPF2025MetadataDict,
    MetadataDict,
)
from flavor.psp.metadata.validators import ValidationError

__all__ = [
    # Models
    "DirectorySpec",
    "WorkenvSpec",
    "RuntimeEnvOps",
    "RuntimeSpec",
    "ExecutionSpec",
    "PackageInfo",
    "PSPFMetadata",
    # Path functions
    "validate_metadata_path",
    "expand_workenv_path",
    "make_relative_to_workenv",
    "validate_metadata_dict",
    "validate_metadata_list",
    # Protocols
    "MetadataValidator",
    "PathResolver",
    "EnvironmentProcessor",
    "MetadataFormat",
    # Types
    "DirectoryDict",
    "WorkenvDict",
    "RuntimeDict",
    "ExecutionDict",
    "PackageDict",
    "PSPF2025MetadataDict",
    "MetadataDict",
    # Exceptions
    "ValidationError",
]