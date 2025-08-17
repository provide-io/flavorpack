"""
Validator functions for metadata fields.

These validators are used with attrs to ensure data integrity
and compliance with specifications.
"""

from pathlib import Path
from typing import Any


class ValidationError(ValueError):
    """Validation error with field information."""
    
    def __init__(self, field: str, value: Any, reason: str):
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"Invalid {field}: {reason}")


def validate_workenv_path(instance, attribute, value: str) -> None:
    """Validate that a path starts with {workenv}.
    
    Args:
        instance: The attrs instance
        attribute: The attribute being validated
        value: The path value
        
    Raises:
        ValidationError: If path doesn't start with {workenv}
    """
    if not value.startswith("{workenv}"):
        raise ValidationError(
            field=attribute.name,
            value=value,
            reason=f"must start with {{workenv}}"
        )


def validate_mode(instance, attribute, value: int) -> None:
    """Validate a Unix file mode.
    
    Args:
        instance: The attrs instance
        attribute: The attribute being validated
        value: The mode value
        
    Raises:
        ValidationError: If mode is invalid
    """
    if not isinstance(value, int):
        raise ValidationError(
            field=attribute.name,
            value=value,
            reason="must be an integer"
        )
    
    if not 0 <= value <= 0o777:
        raise ValidationError(
            field=attribute.name,
            value=oct(value),
            reason="must be between 0000 and 0777"
        )


def validate_format_version(instance, attribute, value: str) -> None:
    """Validate a format version string.
    
    Args:
        instance: The attrs instance
        attribute: The attribute being validated
        value: The format version
        
    Raises:
        ValidationError: If format is unsupported
    """
    supported_formats = ["PSPF/2025"]
    if value not in supported_formats:
        raise ValidationError(
            field=attribute.name,
            value=value,
            reason=f"unsupported format, must be one of {supported_formats}"
        )


def validate_env_operations(instance, attribute, value: dict) -> None:
    """Validate runtime environment operations.
    
    Args:
        instance: The attrs instance
        attribute: The attribute being validated
        value: The env operations dict
        
    Raises:
        ValidationError: If operations are invalid
    """
    valid_ops = {"unset", "pass", "map", "set"}
    
    for op in value:
        if op not in valid_ops:
            raise ValidationError(
                field=f"{attribute.name}.{op}",
                value=op,
                reason=f"unknown operation, must be one of {valid_ops}"
            )
    
    # Validate operation types
    list_ops = {"unset", "pass"}
    dict_ops = {"map", "set"}
    
    for op in list_ops:
        if op in value and not isinstance(value[op], list):
            raise ValidationError(
                field=f"{attribute.name}.{op}",
                value=type(value[op]).__name__,
                reason="must be a list"
            )
    
    for op in dict_ops:
        if op in value and not isinstance(value[op], dict):
            raise ValidationError(
                field=f"{attribute.name}.{op}",
                value=type(value[op]).__name__,
                reason="must be a dict"
            )


def validate_placeholder(value: str) -> bool:
    """Check if a string contains valid placeholders.
    
    Args:
        value: String to check
        
    Returns:
        True if all placeholders are valid
    """
    valid_placeholders = {
        "{workenv}", "{os}", "{arch}", "{platform}",
        "{package_name}", "{version}"
    }
    
    # Find all placeholders in the string
    import re
    placeholders = re.findall(r'\{[^}]+\}', value)
    
    # Check each placeholder
    for placeholder in placeholders:
        if placeholder not in valid_placeholders:
            # Could be a nested path like {workenv}/{os}
            # which is valid if components are valid
            parts = placeholder.strip("{}").split("/")
            for part in parts:
                if f"{{{part}}}" not in valid_placeholders:
                    return False
    
    return True