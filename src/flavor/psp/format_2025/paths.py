#!/usr/bin/env python3
"""
Path validation and normalization for PSPF metadata.

Ensures all paths in metadata use the {workenv} placeholder for portability.
This makes it clear to developers that paths are relative to the work environment.
"""

import os
from typing import Any, Dict, List, Union


def validate_metadata_path(path: str) -> str:
    """
    Ensure a path in metadata starts with {workenv}.
    
    This function normalizes paths to always use the {workenv} placeholder,
    making it clear that paths are relative to the work environment directory.
    
    Args:
        path: The path to validate
        
    Returns:
        Path starting with {workenv}
        
    Examples:
        >>> validate_metadata_path("/usr/bin/python")
        "{workenv}/bin/python"
        >>> validate_metadata_path("bin/python")
        "{workenv}/bin/python"
        >>> validate_metadata_path("{workenv}/bin/python")
        "{workenv}/bin/python"
    """
    if not path:
        return path
    
    # Special case for placeholders that aren't paths
    if path.startswith("{") and path.endswith("}") and "/" not in path:
        # This is a placeholder like "{version}" or "{package_name}"
        return path
    
    # Remove any leading slashes (absolute paths are not allowed)
    if path.startswith("/"):
        # Try to extract the relative part if it looks like a common pattern
        if "/workenv/" in path:
            # Extract everything after /workenv/
            idx = path.index("/workenv/") + len("/workenv/")
            path = path[idx:]
        else:
            # Just remove the leading slash
            path = path.lstrip("/")
    
    # If path doesn't start with {workenv}, add it
    if not path.startswith("{workenv}"):
        # Handle some special cases
        if path.startswith("workenv/"):
            # Replace literal "workenv/" with "{workenv}/"
            path = "{workenv}/" + path[8:]
        elif path == "." or path == "./":
            # Current directory is workenv root
            path = "{workenv}"
        elif path.startswith("./"):
            # Relative to workenv root
            path = "{workenv}/" + path[2:]
        else:
            # Standard case - prepend {workenv}/
            path = f"{{workenv}}/{path}"
    
    # Clean up any double slashes
    while "//" in path:
        path = path.replace("//", "/")
    
    # Ensure {workenv} doesn't end with a slash unless it's the whole path
    if path == "{workenv}/":
        path = "{workenv}"
    
    return path


def validate_metadata_dict(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively validate all paths in a metadata dictionary.
    
    This function walks through the metadata structure and ensures all
    path-like values use the {workenv} placeholder.
    
    Args:
        metadata: The metadata dictionary to validate
        
    Returns:
        Metadata with all paths validated
    """
    # Keys that typically contain file paths
    PATH_KEYS = {
        "command", "check_file", "path", "extract_to", 
        "source", "destination", "executable", "script"
    }
    
    # Keys that contain path patterns or templates
    PATTERN_KEYS = {"pattern", "enumerate"}
    
    result = {}
    
    for key, value in metadata.items():
        if key in PATH_KEYS and isinstance(value, str):
            # This is a path field - validate it
            result[key] = validate_metadata_path(value)
        elif key in PATTERN_KEYS and isinstance(value, dict) and "path" in value:
            # Special case for enumerate patterns
            result[key] = {
                **value,
                "path": validate_metadata_path(value["path"])
            }
        elif isinstance(value, dict):
            # Recurse into nested dictionaries
            result[key] = validate_metadata_dict(value)
        elif isinstance(value, list):
            # Handle lists (may contain dicts or strings)
            result[key] = validate_metadata_list(value, key in PATH_KEYS)
        else:
            # Keep as-is
            result[key] = value
    
    return result


def validate_metadata_list(items: List[Any], is_path_list: bool = False) -> List[Any]:
    """
    Validate items in a list, handling both dict and string items.
    
    Args:
        items: The list to validate
        is_path_list: If True, treat string items as paths
        
    Returns:
        List with validated items
    """
    result = []
    
    for item in items:
        if isinstance(item, dict):
            # Recurse into dictionaries
            result.append(validate_metadata_dict(item))
        elif isinstance(item, str) and is_path_list:
            # This is a path string
            result.append(validate_metadata_path(item))
        else:
            # Keep as-is
            result.append(item)
    
    return result


def expand_workenv_path(path: str, workenv_dir: str) -> str:
    """
    Expand a {workenv} path to an actual filesystem path.
    
    This is used at runtime to convert metadata paths to real paths.
    
    Args:
        path: Path containing {workenv} placeholder
        workenv_dir: Actual workenv directory path
        
    Returns:
        Expanded path
        
    Examples:
        >>> expand_workenv_path("{workenv}/bin/python", "/tmp/pspf/work123")
        "/tmp/pspf/work123/bin/python"
    """
    if "{workenv}" in path:
        return path.replace("{workenv}", workenv_dir)
    return path


def make_relative_to_workenv(absolute_path: str, workenv_dir: str) -> str:
    """
    Convert an absolute path to a {workenv}-relative path.
    
    This is useful when capturing paths during build time.
    
    Args:
        absolute_path: The absolute path to convert
        workenv_dir: The workenv directory path
        
    Returns:
        Path with {workenv} placeholder
        
    Examples:
        >>> make_relative_to_workenv("/tmp/build/bin/python", "/tmp/build")
        "{workenv}/bin/python"
    """
    # Normalize paths
    absolute_path = os.path.normpath(absolute_path)
    workenv_dir = os.path.normpath(workenv_dir)
    
    # Check if path is under workenv
    if absolute_path.startswith(workenv_dir):
        # Get relative path
        relpath = os.path.relpath(absolute_path, workenv_dir)
        if relpath == ".":
            return "{workenv}"
        return f"{{workenv}}/{relpath}"
    
    # Path is not under workenv - just return with {workenv} prefix
    # This shouldn't normally happen but handle gracefully
    return validate_metadata_path(absolute_path)