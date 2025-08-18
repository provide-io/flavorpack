"""
PSPF/2025 format-specific metadata handling.
"""

from typing import Any

from flavor.psp.metadata.models import PSPFMetadata
from flavor.psp.metadata.validators import ValidationError


class PSPF2025Format:
    """Handler for PSPF/2025 metadata format."""
    
    format_version = "PSPF/2025"
    
    def parse(self, data: dict[str, Any]) -> PSPFMetadata:
        """Parse raw data into validated PSPF/2025 metadata.
        
        Args:
            data: Raw metadata dictionary
            
        Returns:
            Validated PSPFMetadata object
            
        Raises:
            ValidationError: If data doesn't conform to PSPF/2025
        """
        # Check format version
        if data.get("format") != self.format_version:
            raise ValidationError(
                field="format",
                value=data.get("format"),
                reason=f"must be {self.format_version}"
            )
        
        # Parse using the model's from_dict method
        metadata = PSPFMetadata.from_dict(data)
        
        # Validate the parsed metadata
        metadata.validate()
        
        return metadata
    
    def serialize(self, metadata: PSPFMetadata) -> dict[str, Any]:
        """Serialize metadata to dictionary.
        
        Args:
            metadata: PSPFMetadata object
            
        Returns:
            Dictionary representation
        """
        return metadata.to_dict()


# Convenience function
def validate_metadata(data: dict[str, Any]) -> bool:
    """Validate PSPF/2025 metadata.
    
    Args:
        data: Metadata dictionary
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If validation fails
    """
    format_handler = PSPF2025Format()
    metadata = format_handler.parse(data)
    metadata.validate()
    return True