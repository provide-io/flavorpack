"""
Protocol definitions for metadata handling.

These protocols define the interfaces that different metadata implementations
must follow, enabling duck typing and runtime type checking.
"""

from typing import Protocol, Any, runtime_checkable


@runtime_checkable
class MetadataValidator(Protocol):
    """Protocol for metadata validators."""
    
    def validate(self) -> None:
        """Validate the metadata structure.
        
        Raises:
            ValidationError: If validation fails
        """
        ...
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        ...


@runtime_checkable
class PathResolver(Protocol):
    """Protocol for path resolution strategies."""
    
    def resolve(self, path: str, context: dict[str, str]) -> str:
        """Resolve placeholders in a path.
        
        Args:
            path: Path with potential placeholders
            context: Context dictionary with replacement values
            
        Returns:
            Resolved path string
        """
        ...
    
    def validate(self, path: str) -> bool:
        """Check if a path is valid for this resolver.
        
        Args:
            path: Path to validate
            
        Returns:
            True if valid
        """
        ...


@runtime_checkable
class EnvironmentProcessor(Protocol):
    """Protocol for environment variable processors."""
    
    def process(self, env: dict[str, str]) -> dict[str, str]:
        """Process environment variables.
        
        Args:
            env: Input environment dictionary
            
        Returns:
            Processed environment dictionary
        """
        ...


@runtime_checkable
class MetadataFormat(Protocol):
    """Protocol for metadata format handlers."""
    
    format_version: str
    
    def parse(self, data: dict[str, Any]) -> MetadataValidator:
        """Parse raw data into validated metadata.
        
        Args:
            data: Raw metadata dictionary
            
        Returns:
            Validated metadata object
        """
        ...
    
    def serialize(self, metadata: MetadataValidator) -> dict[str, Any]:
        """Serialize metadata to dictionary.
        
        Args:
            metadata: Metadata object
            
        Returns:
            Dictionary representation
        """
        ...