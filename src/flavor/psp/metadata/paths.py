"""
Path manipulation and resolution for metadata.

Generic path functions that work with metadata structures.
"""

import os
from pathlib import Path
from typing import Any

from flavor.psp.workenv.placeholders import substitute_placeholders


def validate_metadata_path(path: str) -> str:
    """
    Ensure a path in metadata starts with {workenv}.
    
    Args:
        path: The path to validate
        
    Returns:
        Path starting with {workenv}
    """
    if not path:
        return path
    
    # Special case for placeholders that aren't paths
    if path.startswith("{") and path.endswith("}") and "/" not in path:
        return path
    
    # Remove any leading slashes
    if path.startswith("/"):
        path = path.lstrip("/")
    
    # If path doesn't start with {workenv}, add it
    if not path.startswith("{workenv}"):
        if path == "." or path == "./":
            path = "{workenv}"
        elif path.startswith("./"):
            path = f"{{workenv}}/{path[2:]}"
        else:
            path = f"{{workenv}}/{path}"
    
    # Clean up any double slashes
    while "//" in path:
        path = path.replace("//", "/")
    
    # Ensure {workenv} doesn't end with a slash unless it's the whole path
    if path == "{workenv}/":
        path = "{workenv}"
    
    return path


def expand_workenv_path(path: str, workenv_dir: str | Path) -> str:
    """
    Expand a {workenv} path to an actual filesystem path.
    
    Args:
        path: Path containing {workenv} placeholder
        workenv_dir: Actual workenv directory path
        
    Returns:
        Expanded path
    """
    return substitute_placeholders(path, Path(workenv_dir))


def make_relative_to_workenv(absolute_path: str | Path, workenv_dir: str | Path) -> str:
    """
    Convert an absolute path to a {workenv}-relative path.
    
    Args:
        absolute_path: The absolute path to convert
        workenv_dir: The workenv directory path
        
    Returns:
        Path with {workenv} placeholder
    """
    # Normalize paths
    absolute_path = Path(absolute_path).resolve()
    workenv_dir = Path(workenv_dir).resolve()
    
    # Check if path is under workenv
    try:
        relpath = absolute_path.relative_to(workenv_dir)
        if str(relpath) == ".":
            return "{workenv}"
        return f"{{workenv}}/{relpath}"
    except ValueError:
        # Path is not under workenv - just return with {workenv} prefix
        return validate_metadata_path(str(absolute_path))


def validate_metadata_dict(metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively validate all paths in a metadata dictionary.
    
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
    
    result = {}
    
    for key, value in metadata.items():
        if key == "workenv" and isinstance(value, dict):
            # Workenv section - validate directory paths
            workenv_result = {}
            if "directories" in value:
                dirs = value["directories"]
                if isinstance(dirs, list):
                    validated_dirs = []
                    for dir_info in dirs:
                        if isinstance(dir_info, dict) and "path" in dir_info:
                            dir_copy = dir_info.copy()
                            dir_copy["path"] = validate_metadata_path(dir_info["path"])
                            validated_dirs.append(dir_copy)
                        else:
                            validated_dirs.append(dir_info)
                    workenv_result["directories"] = validated_dirs
                else:
                    workenv_result["directories"] = dirs
            
            # Copy other workenv fields
            for k, v in value.items():
                if k not in workenv_result:
                    workenv_result[k] = v
            
            result[key] = workenv_result
        elif key in PATH_KEYS and isinstance(value, str):
            # This is a path field - validate it
            result[key] = validate_metadata_path(value)
        elif isinstance(value, dict):
            # Recurse into nested dictionaries
            result[key] = validate_metadata_dict(value)
        elif isinstance(value, list):
            # Handle lists
            result[key] = validate_metadata_list(value, key in PATH_KEYS)
        else:
            # Keep as-is
            result[key] = value
    
    return result


def validate_metadata_list(items: list[Any], is_path_list: bool = False) -> list[Any]:
    """
    Validate items in a list.
    
    Args:
        items: The list to validate
        is_path_list: If True, treat string items as paths
        
    Returns:
        List with validated items
    """
    result = []
    
    for item in items:
        if isinstance(item, dict):
            result.append(validate_metadata_dict(item))
        elif isinstance(item, str) and is_path_list:
            result.append(validate_metadata_path(item))
        else:
            result.append(item)
    
    return result