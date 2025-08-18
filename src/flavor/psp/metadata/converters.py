"""
Converter functions for metadata field transformation.

These converters are used with attrs to automatically transform
input values into the correct types and formats.
"""

from pathlib import Path
from typing import Any


def ensure_workenv_prefix(path: str | Path) -> str:
    """Ensure a path starts with {workenv} placeholder.
    
    Args:
        path: Input path
        
    Returns:
        Path with {workenv} prefix
    """
    path_str = str(path)
    
    # Already has workenv prefix
    if path_str.startswith("{workenv}"):
        return path_str
    
    # Special case for placeholders
    if path_str.startswith("{") and path_str.endswith("}") and "/" not in path_str:
        return path_str
    
    # Remove leading slashes and add workenv prefix
    path_str = path_str.lstrip("/")
    
    # Handle special cases
    if path_str in (".", ""):
        return "{workenv}"
    elif path_str.startswith("./"):
        return f"{{workenv}}/{path_str[2:]}"
    else:
        return f"{{workenv}}/{path_str}"


def parse_octal_mode(mode: str | int) -> int:
    """Parse an octal mode string or int into an integer.
    
    Args:
        mode: Mode as string (e.g., "0755", "755", "0o755") or int
        
    Returns:
        Mode as integer
        
    Raises:
        ValidationError: If mode is invalid
    """
    from flavor.psp.metadata.validators import ValidationError
    
    if isinstance(mode, int):
        if not 0 <= mode <= 0o777:
            raise ValidationError(
                field="mode",
                value=mode,
                reason="must be between 0000 and 0777"
            )
        return mode
    
    mode_str = str(mode).strip()
    
    # Handle different formats
    if mode_str.startswith("0o"):
        mode_str = mode_str[2:]
    elif mode_str.startswith("0x"):
        raise ValidationError(
            field="mode",
            value=mode,
            reason="hexadecimal mode not supported"
        )
    
    try:
        # Parse as octal
        mode_int = int(mode_str, 8)
        if not 0 <= mode_int <= 0o777:
            raise ValidationError(
                field="mode",
                value=mode,
                reason="must be between 0000 and 0777"
            )
        return mode_int
    except ValueError as e:
        raise ValidationError(
            field="mode",
            value=mode,
            reason="invalid octal format"
        ) from e


def normalize_path_list(paths: list[str | Path] | None) -> list[str]:
    """Normalize a list of paths.
    
    Args:
        paths: List of paths or None
        
    Returns:
        List of normalized path strings
    """
    if paths is None:
        return []
    return [ensure_workenv_prefix(p) for p in paths]


def normalize_env_dict(env: dict[str, Any] | None) -> dict[str, str]:
    """Normalize an environment dictionary.
    
    Args:
        env: Environment dictionary or None
        
    Returns:
        Normalized environment dictionary
    """
    if env is None:
        return {}
    return {str(k): str(v) for k, v in env.items()}


def to_list(value: str | list[str] | None) -> list[str]:
    """Convert a value to a list of strings.
    
    Args:
        value: String, list, or None
        
    Returns:
        List of strings
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def to_path(value: str | Path | None) -> Path | None:
    """Convert a value to a Path object.
    
    Args:
        value: String path, Path object, or None
        
    Returns:
        Path object or None
    """
    if value is None:
        return None
    return Path(value)